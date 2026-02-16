import os

basedir = os.path.abspath(os.path.dirname(__file__))


def _rds_iam_creator():
    """Create a psycopg2 connection using RDS IAM auth token."""
    import boto3
    import psycopg2

    host = os.environ["RDS_HOST"]
    port = int(os.environ.get("RDS_PORT", 5432))
    database = os.environ.get("RDS_DATABASE", "postgres")
    user = os.environ["RDS_USER"]
    region = os.environ.get("RDS_REGION", "eu-west-2")
    sslrootcert = os.environ.get("RDS_SSLROOTCERT", "/app/certs/eu-west-2-bundle.pem")

    token = boto3.client("rds", region_name=region).generate_db_auth_token(
        DBHostname=host,
        Port=port,
        DBUsername=user,
        Region=region,
    )
    return psycopg2.connect(
        host=host,
        port=port,
        database=database,
        user=user,
        password=token,
        sslmode="verify-full",
        sslrootcert=sslrootcert,
    )


def _database_config():
    """
    Returns (uri, engine_options).
    - ENVIRONMENT=develop → SQLite
    - RDS_IAM + RDS_HOST set → RDS with IAM auth
    - Else DATABASE_URL or SQLite fallback
    """
    env = (os.environ.get("ENVIRONMENT") or "").lower()
    if env in ("develop", "development"):
        uri = "sqlite:///" + os.path.join(basedir, "instance", "recetas.db")
        return uri, {}

    if os.environ.get("RDS_IAM") and os.environ.get("RDS_HOST"):
        uri = "postgresql+psycopg2://"
        return uri, {"creator": _rds_iam_creator}

    uri = os.environ.get("DATABASE_URL") or "sqlite:///" + os.path.join(
        basedir, "instance", "recetas.db"
    )
    return uri, {}


_db_uri, _db_engine_options = _database_config()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-key-change-in-production"
    SQLALCHEMY_DATABASE_URI = _db_uri
    SQLALCHEMY_ENGINE_OPTIONS = _db_engine_options
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(basedir, "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload

    # S3 image storage (optional; when set, recipe images go to S3)
    S3_BUCKET = os.environ.get("S3_BUCKET")
    S3_REGION = os.environ.get("S3_REGION", "eu-west-2")
    S3_PREFIX = (os.environ.get("S3_PREFIX") or "recipes").strip().rstrip("/")
