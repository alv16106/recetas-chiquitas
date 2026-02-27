import os

basedir = os.path.abspath(os.path.dirname(__file__))


def _database_uri():
    """
    Returns database URI.
    - ENVIRONMENT=develop → SQLite
    - DATABASE_URL set → Use it directly (Neon, etc.)
    - Else SQLite fallback
    """
    env = (os.environ.get("ENVIRONMENT") or "").lower()
    if env in ("develop", "development"):
        return "sqlite:///" + os.path.join(basedir, "instance", "recetas.db")

    return os.environ.get("DATABASE_URL") or "sqlite:///" + os.path.join(
        basedir, "instance", "recetas.db"
    )


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-key-change-in-production"
    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(basedir, "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload

    # S3 image storage (optional; when set, recipe images go to S3)
    S3_BUCKET = os.environ.get("S3_BUCKET")
    S3_REGION = os.environ.get("S3_REGION", "auto")
    S3_PREFIX = (os.environ.get("S3_PREFIX") or "recipes").strip().rstrip("/")
