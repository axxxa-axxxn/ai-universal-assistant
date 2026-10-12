
import os

from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv

# Load environment variables from backend/.env
load_dotenv()

db = SQLAlchemy()
jwt = JWTManager()


def create_app():
    app = Flask(__name__)

    # Application configuration
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")
    app.config["JWT_SECRET_KEY"] = os.getenv(
        "JWT_SECRET_KEY",
        "dev-jwt-secret"
    )

    # Gemini configuration
    app.config["GEMINI_API_KEY"] = os.getenv("GEMINI_API_KEY")
    app.config["AI_MODEL"] = os.getenv(
        "AI_MODEL",
        "gemini-3.8-flash"
    )

    # Database configuration
    database_url = os.getenv(
        "DATABASE_URL",
        "sqlite:///assistant.db"
    )

    # Use psycopg2 for PostgreSQL connections
    if database_url.startswith("postgres://"):
        database_url = database_url.replace(
            "postgres://",
            "postgresql+psycopg2://",
            1
        )
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace(
            "postgresql://",
            "postgresql+psycopg2://",
            1
        )

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Upload configuration
    app.config["MAX_CONTENT_LENGTH"] = int(
        os.getenv("MAX_CONTENT_LENGTH", 52428800)
    )

    base_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..")
    )

    app.config["UPLOAD_FOLDER"] = os.path.join(
        base_dir,
        "uploads"
    )

    os.makedirs(
        app.config["UPLOAD_FOLDER"],
        exist_ok=True
    )

    # CORS configuration
    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": os.getenv(
                    "FRONTEND_URL",
                    "http://localhost:5173"
                )
            }
        },
        supports_credentials=True
    )

    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)

    # Import models and routes
    from .models import (
        User,
        Conversation,
        Message,
        Document,
        DocumentChunk,
    )

    from .routes import api

    # Register API routes
    app.register_blueprint(api)

    # Create database tables
    with app.app_context():
        db.create_all()

    return app