import os
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from . import db
from .models import User, Conversation, Message, Document
from .services import save_document, retrieve, web_search, generate_answer

api = Blueprint("api", __name__, url_prefix="/api")

def current_user():
    return User.query.get(int(get_jwt_identity()))

@api.get("/health")
def health():
    return jsonify({"success": True, "service": "AI Universal Assistant"})

@api.post("/auth/register")
def register():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not name or not email or len(password) < 6:
        return jsonify({"success": False, "message": "Name, email and a password of at least 6 characters are required."}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"success": False, "message": "An account with this email already exists."}), 409

    user = User(name=name, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    token = create_access_token(identity=str(user.id))
    return jsonify({"success": True, "token": token, "user": {"id": user.id, "name": user.name, "email": user.email}}), 201

@api.post("/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"success": False, "message": "Invalid email or password."}), 401
    token = create_access_token(identity=str(user.id))
    return jsonify({"success": True, "token": token, "user": {"id": user.id, "name": user.name, "email": user.email}})

@api.get("/auth/me")
@jwt_required()
def me():
    u = current_user()
    return jsonify({"success": True, "user": {"id": u.id, "name": u.name, "email": u.email}})

@api.get("/conversations")
@jwt_required()
def conversations():
    u = current_user()
    rows = Conversation.query.filter_by(user_id=u.id).order_by(Conversation.updated_at.desc()).all()
    return jsonify({"success": True, "conversations": [{"id": x.id, "title": x.title} for x in rows]})

@api.post("/conversations")
@jwt_required()
def create_conversation():
    u = current_user()
    c = Conversation(user_id=u.id, title="New conversation")
    db.session.add(c)
    db.session.commit()
    return jsonify({"success": True, "conversation": {"id": c.id, "title": c.title}}), 201

@api.get("/conversations/<int:conversation_id>")
@jwt_required()
def get_conversation(conversation_id):
    u = current_user()
    c = Conversation.query.filter_by(id=conversation_id, user_id=u.id).first()
    if not c:
        return jsonify({"success": False, "message": "Conversation not found."}), 404
    return jsonify({"success": True, "conversation": {
        "id": c.id, "title": c.title,
        "messages": [{"id": m.id, "role": m.role, "content": m.content} for m in c.messages]
    }})

@api.post("/chat")
@jwt_required()
def chat():
    u = current_user()
    data = request.form if request.form else (request.get_json(silent=True) or {})
    question = (data.get("message") or "").strip()
    conversation_id = data.get("conversation_id")
    use_web = str(data.get("use_web", "false")).lower() == "true"
    if not question:
        return jsonify({"success": False, "message": "Message is required."}), 400

    if conversation_id:
        c = Conversation.query.filter_by(id=int(conversation_id), user_id=u.id).first()
    else:
        c = None
    if not c:
        c = Conversation(user_id=u.id, title=question[:60])
        db.session.add(c)
        db.session.flush()

    old_messages = Message.query.filter_by(conversation_id=c.id).order_by(Message.created_at.asc()).all()
    db.session.add(Message(conversation_id=c.id, role="user", content=question))

    chunks = retrieve(u.id, question)
    context = [x.content for x in chunks]
    web_results = web_search(question) if use_web else []

    image_path = None
    image = request.files.get("image")
    if image and image.filename:
        ext = os.path.splitext(image.filename)[1].lower()
        if ext not in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
            return jsonify({"success": False, "message": "Unsupported image format."}), 400
        safe = secure_filename(image.filename)
        image_path = os.path.join(current_app.config["UPLOAD_FOLDER"], "chat_" + safe)
        image.save(image_path)

    answer = generate_answer(question, context, old_messages, image_path, web_results)
    db.session.add(Message(conversation_id=c.id, role="assistant", content=answer))
    c.updated_at = __import__("datetime").datetime.utcnow()
    db.session.commit()

    if image_path and os.path.exists(image_path):
        os.remove(image_path)

    return jsonify({
        "success": True,
        "conversation_id": c.id,
        "answer": answer,
        "sources": [{"document": x.document.original_name, "chunk": x.chunk_index} for x in chunks],
        "web_results": web_results
    })

@api.post("/files")
@jwt_required()
def upload_file():
    u = current_user()
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"success": False, "message": "Select a file."}), 400
    try:
        doc, count = save_document(u.id, f)
        return jsonify({"success": True, "document": {"id": doc.id, "name": doc.original_name, "chunks": count}}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 400

@api.get("/files")
@jwt_required()
def files():
    u = current_user()
    rows = Document.query.filter_by(user_id=u.id).order_by(Document.created_at.desc()).all()
    return jsonify({"success": True, "files": [{"id": x.id, "name": x.original_name, "type": x.file_type} for x in rows]})
