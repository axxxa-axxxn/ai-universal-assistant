
import os

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity,
)
from werkzeug.utils import secure_filename
from sqlalchemy import text

from . import db
from .models import User, Conversation, Message, Document
from .services import save_document, retrieve, web_search, generate_answer

api = Blueprint("api", __name__, url_prefix="/api")


def current_user():
    return User.query.get(int(get_jwt_identity()))


@api.get("/health")
def health():
    return jsonify({
        "success": True,
        "service": "AI Universal Assistant",
    }), 200


@api.get("/db-health")
def db_health():
    """Check whether the configured database is reachable."""
    try:
        db.session.execute(text("SELECT 1"))
        return jsonify({
            "success": True,
            "database": "connected",
        }), 200
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Database health check failed")
        return jsonify({
            "success": False,
            "database": "disconnected",
            "message": "Database connection failed. Check server logs.",
        }), 503
    finally:
        db.session.remove()


@api.post("/auth/register")
def register():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not name or not email or len(password) < 6:
        return jsonify({
            "success": False,
            "message": (
                "Name, email and a password of at least "
                "6 characters are required."
            ),
        }), 400

    if User.query.filter_by(email=email).first():
        return jsonify({
            "success": False,
            "message": "An account with this email already exists.",
        }), 409

    user = User(name=name, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    token = create_access_token(identity=str(user.id))

    return jsonify({
        "success": True,
        "token": token,
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
        },
    }), 201


@api.post("/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        return jsonify({
            "success": False,
            "message": "Invalid email or password.",
        }), 401

    token = create_access_token(identity=str(user.id))

    return jsonify({
        "success": True,
        "token": token,
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
        },
    }), 200


@api.get("/auth/me")
@jwt_required()
def me():
    user = current_user()

    if not user:
        return jsonify({
            "success": False,
            "message": "User not found.",
        }), 404

    return jsonify({
        "success": True,
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
        },
    }), 200


@api.get("/conversations")
@jwt_required()
def conversations():
    user = current_user()

    if not user:
        return jsonify({
            "success": False,
            "message": "User not found.",
        }), 404

    rows = (
        Conversation.query
        .filter_by(user_id=user.id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )

    return jsonify({
        "success": True,
        "conversations": [
            {"id": item.id, "title": item.title}
            for item in rows
        ],
    }), 200


@api.post("/conversations")
@jwt_required()
def create_conversation():
    user = current_user()

    if not user:
        return jsonify({
            "success": False,
            "message": "User not found.",
        }), 404

    conversation = Conversation(
        user_id=user.id,
        title="New conversation",
    )
    db.session.add(conversation)
    db.session.commit()

    return jsonify({
        "success": True,
        "conversation": {
            "id": conversation.id,
            "title": conversation.title,
        },
    }), 201


@api.get("/conversations/<int:conversation_id>")
@jwt_required()
def get_conversation(conversation_id):
    user = current_user()

    if not user:
        return jsonify({
            "success": False,
            "message": "User not found.",
        }), 404

    conversation = Conversation.query.filter_by(
        id=conversation_id,
        user_id=user.id,
    ).first()

    if not conversation:
        return jsonify({
            "success": False,
            "message": "Conversation not found.",
        }), 404

    return jsonify({
        "success": True,
        "conversation": {
            "id": conversation.id,
            "title": conversation.title,
            "messages": [
                {
                    "id": message.id,
                    "role": message.role,
                    "content": message.content,
                }
                for message in conversation.messages
            ],
        },
    }), 200


@api.post("/chat")
@jwt_required()
def chat():
    user = current_user()

    if not user:
        return jsonify({
            "success": False,
            "message": "User not found.",
        }), 404

    data = request.form if request.form else (
        request.get_json(silent=True) or {}
    )

    question = (data.get("message") or "").strip()
    conversation_id = data.get("conversation_id")
    use_web = str(data.get("use_web", "false")).lower() == "true"

    if not question:
        return jsonify({
            "success": False,
            "message": "Message is required.",
        }), 400

    if conversation_id:
        try:
            conversation_id = int(conversation_id)
        except (TypeError, ValueError):
            return jsonify({
                "success": False,
                "message": "Invalid conversation ID.",
            }), 400

        conversation = Conversation.query.filter_by(
            id=conversation_id,
            user_id=user.id,
        ).first()
    else:
        conversation = None

    if not conversation:
        conversation = Conversation(
            user_id=user.id,
            title=question[:60],
        )
        db.session.add(conversation)
        db.session.flush()

    old_messages = (
        Message.query
        .filter_by(conversation_id=conversation.id)
        .order_by(Message.created_at.asc())
        .all()
    )

    db.session.add(Message(
        conversation_id=conversation.id,
        role="user",
        content=question,
    ))

    chunks = retrieve(user.id, question)
    context = [chunk.content for chunk in chunks]
    web_results = web_search(question) if use_web else []

    image_path = None
    image = request.files.get("image")

    if image and image.filename:
        ext = os.path.splitext(image.filename)[1].lower()

        if ext not in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
            db.session.rollback()
            return jsonify({
                "success": False,
                "message": "Unsupported image format.",
            }), 400

        safe_filename = secure_filename(image.filename)

        if not safe_filename:
            db.session.rollback()
            return jsonify({
                "success": False,
                "message": "Invalid image filename.",
            }), 400

        upload_folder = current_app.config["UPLOAD_FOLDER"]
        os.makedirs(upload_folder, exist_ok=True)

        image_path = os.path.join(
            upload_folder,
            "chat_" + safe_filename,
        )
        image.save(image_path)

    try:
        answer = generate_answer(
            question,
            context,
            old_messages,
            image_path,
            web_results,
        )

        db.session.add(Message(
            conversation_id=conversation.id,
            role="assistant",
            content=answer,
        ))

        from datetime import datetime, timezone
        conversation.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        return jsonify({
            "success": True,
            "conversation_id": conversation.id,
            "answer": answer,
            "sources": [
                {
                    "document": chunk.document.original_name,
                    "chunk": chunk.chunk_index,
                }
                for chunk in chunks
            ],
            "web_results": web_results,
        }), 200

    except Exception:
        db.session.rollback()
        current_app.logger.exception("Chat request failed")

        return jsonify({
            "success": False,
            "message": "Unable to process the chat request.",
        }), 500

    finally:
        if image_path and os.path.exists(image_path):
            try:
                os.remove(image_path)
            except OSError:
                current_app.logger.warning(
                    "Could not remove temporary uploaded image."
                )


@api.post("/files")
@jwt_required()
def upload_file():
    user = current_user()

    if not user:
        return jsonify({
            "success": False,
            "message": "User not found.",
        }), 404

    uploaded_file = request.files.get("file")

    if not uploaded_file or not uploaded_file.filename:
        return jsonify({
            "success": False,
            "message": "Select a file.",
        }), 400

    try:
        document, count = save_document(user.id, uploaded_file)

        return jsonify({
            "success": True,
            "document": {
                "id": document.id,
                "name": document.original_name,
                "chunks": count,
            },
        }), 201

    except Exception:
        db.session.rollback()
        current_app.logger.exception("Document upload failed")

        return jsonify({
            "success": False,
            "message": "Unable to upload the document. Check server logs.",
        }), 400


@api.get("/files")
@jwt_required()
def files():
    user = current_user()

    if not user:
        return jsonify({
            "success": False,
            "message": "User not found.",
        }), 404

    rows = (
        Document.query
        .filter_by(user_id=user.id)
        .order_by(Document.created_at.desc())
        .all()
    )

    return jsonify({
        "success": True,
        "files": [
            {
                "id": document.id,
                "name": document.original_name,
                "type": document.file_type,
            }
            for document in rows
        ],
    }), 200