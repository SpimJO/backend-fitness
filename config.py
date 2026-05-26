# backend/config.py
import os
from datetime import timedelta
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


def resolve_database_url() -> str:
    """
    Database resolution order:
      1. DATABASE_URL (Render PostgreSQL — auto-injected)
      2. POSTGRES_* variables (local Docker / pgAdmin)
      3. DB_* MySQL variables (optional XAMPP fallback)
    """
    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url

    pg_host = os.environ.get("POSTGRES_HOST", "").strip()
    if pg_host or os.environ.get("DB_ENGINE", "").lower() == "postgresql":
        pg_user = os.environ.get("POSTGRES_USER", "fitquest")
        pg_pass = os.environ.get("POSTGRES_PASSWORD", "fitquest")
        pg_host = pg_host or "127.0.0.1"
        pg_port = os.environ.get("POSTGRES_PORT", "5432")
        pg_db = os.environ.get("POSTGRES_DB", "fitquest")
        pg_pass_esc = quote_plus(pg_pass)
        return (
            f"postgresql+psycopg2://{pg_user}:{pg_pass_esc}"
            f"@{pg_host}:{pg_port}/{pg_db}"
        )

    db_host = os.environ.get("DB_HOST", "127.0.0.1")
    db_port = os.environ.get("DB_PORT", "3306")
    db_name = os.environ.get("DB_NAME", "fitquest")
    db_user = os.environ.get("DB_USER", "root")
    db_pass = os.environ.get("DB_PASS", "")
    db_pass_esc = quote_plus(db_pass)
    return (
        f"mysql+pymysql://{db_user}:{db_pass_esc}"
        f"@{db_host}:{db_port}/{db_name}?charset=utf8mb4"
    )


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-jwt-secret-change-me")

    SQLALCHEMY_DATABASE_URI = resolve_database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    JWT_TOKEN_LOCATION = ["headers"]
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=7)

    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

    @staticmethod
    def database_label() -> str:
        uri = Config.SQLALCHEMY_DATABASE_URI or ""
        if uri.startswith("postgresql"):
            return "postgresql"
        if uri.startswith("mysql"):
            return "mysql"
        return "unknown"
