import os

from flask import Flask

from app.config import Config

db = None  # populated by init_db(), holds the Mongo database handle

# Project root (one level up from this app/ package) - templates/ and
# static/ live there, not inside app/, so Flask needs explicit paths.
_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def init_db(app):
    """Connect to MongoDB (or mongomock for local dev) and attach the
    database handle to the module-level `db` variable, plus create the
    indexes we rely on."""
    global db

    if app.config["USE_MONGOMOCK"]:
        import mongomock

        client = mongomock.MongoClient()
    else:
        from pymongo import MongoClient

        client = MongoClient(app.config["MONGO_URI"])

    db = client[app.config["MONGO_DB_NAME"]]

    # Indexes: fast lookup by ticket_id, fast filtering by status.
    # Search-as-you-type uses case-insensitive regex OR queries across
    # name/email/subject/description/ticket_id (see app/models/ticket.py) -
    # a $text index was considered but regex gives simpler, more
    # predictable substring matching for a UI search box, and behaves
    # identically on real MongoDB and mongomock.
    db.tickets.create_index("ticket_id", unique=True)
    db.tickets.create_index("status")
    db.tickets.create_index("created_at")
    db.notes.create_index("ticket_id")
    db.users.create_index("email", unique=True)
    db.users.create_index("user_id", unique=True)
    db.password_reset_tokens.create_index("token_hash", unique=True)
    db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)

    # Optional first-admin bootstrap for a fresh deployment.
    if app.config["ADMIN_EMAIL"] and app.config["ADMIN_PASSWORD"]:
        from app.models import user as user_model

        if not user_model.find_auth_by_email(app.config["ADMIN_EMAIL"]):
            user_model.create_user(
                app.config["ADMIN_EMAIL"],
                app.config["ADMIN_PASSWORD"],
                "Administrator",
                role="admin",
            )

    return db


def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(_BASE_DIR, "templates"),
        static_folder=os.path.join(_BASE_DIR, "static"),
    )
    app.config.from_object(Config)

    init_db(app)

    from app.routes.api import api_bp
    from app.routes.auth import auth_bp
    from app.routes.views import views_bp

    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(views_bp)

    return app
