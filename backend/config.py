import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _database_url():
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        return "sqlite:///" + os.path.join(BASE_DIR, "resolvehq.db")
    # Supabase / Heroku style URLs start with postgres:// which SQLAlchemy no longer accepts
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url


class Config:
    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}

    SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-only-change-me")
    JWT_SECRET_KEY = SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=int(os.getenv("JWT_EXPIRES_DAYS", "7")))

    # Comma-separated list of allowed frontend origins
    CORS_ORIGINS = [o.strip() for o in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:8000,http://127.0.0.1:8000,http://localhost:5500,http://127.0.0.1:5500",
    ).split(",") if o.strip()]

    # Attachments
    MAX_FILES_PER_TICKET = 5
    MAX_FILE_BYTES = 5 * 1024 * 1024          # 5 MB per image
    MAX_CONTENT_LENGTH = 30 * 1024 * 1024     # whole request cap
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.join(BASE_DIR, "uploads"))

    # Supabase Storage (used when both are set; otherwise files go to UPLOAD_DIR)
    SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
    SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
    SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "ticket-attachments")
    SIGNED_URL_SECONDS = int(os.getenv("SIGNED_URL_SECONDS", "3600"))

    # First company agent, created on startup if no agent exists yet
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
    ADMIN_NAME = os.getenv("ADMIN_NAME", "Support Admin")

    SEED_DEMO = os.getenv("SEED_DEMO", "false").lower() == "true"
