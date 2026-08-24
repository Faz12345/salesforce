import os


class Config:
    """Application configuration, loaded from environment variables."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY") or SECRET_KEY or "local-development-only-change-me"
    JWT_ACCESS_MINUTES = int(os.environ.get("JWT_ACCESS_MINUTES", "30"))
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
    EXPOSE_RESET_TOKEN = os.environ.get("EXPOSE_RESET_TOKEN", "false").lower() == "true"
    SMTP_HOST = os.environ.get("SMTP_HOST", "")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "true").lower() == "true"
    SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    MAIL_FROM = os.environ.get("MAIL_FROM", "")
    APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:5000")
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

    # MongoDB connection string, e.g. from MongoDB Atlas free tier:
    # mongodb+srv://<user>:<password>@cluster0.mongodb.net/support_crm
    MONGO_URI = os.environ.get("MONGO_URI", "")
    MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "")

    # Set to "true" to run against an in-memory mongomock instance instead
    # of a real MongoDB server. Useful for local development/testing when
    # you don't have a Mongo server handy. Never use this in production.
    USE_MONGOMOCK = os.environ.get("USE_MONGOMOCK", "false").lower() == "true"
