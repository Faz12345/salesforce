"""Authentication, profile, and administrator API routes."""

import re

from flask import Blueprint, current_app, g, jsonify, request
from pymongo.errors import DuplicateKeyError

from app import auth
from app import mailer
from app.models import user as user_model


auth_bp = Blueprint("auth", __name__)
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _valid_password(password):
    return isinstance(password, str) and len(password) >= 8


def _public_user(user):
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
        "is_active": user["is_active"],
        "created_at": user["created_at"].isoformat() if user.get("created_at") else None,
        "last_login_at": user["last_login_at"].isoformat() if user.get("last_login_at") else None,
    }


def _credentials(data):
    email = user_model.normalize_email(data.get("email"))
    password = data.get("password")
    if not _EMAIL_RE.match(email):
        return None, (jsonify({"error": "A valid email is required"}), 400)
    if not _valid_password(password):
        return None, (jsonify({"error": "Password must be at least 8 characters"}), 400)
    return (email, password), None


@auth_bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    credentials, error = _credentials(data)
    if error:
        return error
    email, password = credentials
    name = str(data.get("name", "")).strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400
    try:
        user = user_model.create_user(email, password, name)
    except DuplicateKeyError:
        return jsonify({"error": "Email is already registered"}), 409
    token = auth.issue_access_token(user)
    response = jsonify({"user": _public_user(user), "access_token": token}), 201
    response[0].set_cookie("access_token", token, httponly=True, secure=current_app.config["SESSION_COOKIE_SECURE"], samesite="Lax", max_age=current_app.config["JWT_ACCESS_MINUTES"] * 60)
    return response


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = user_model.normalize_email(data.get("email"))
    password = data.get("password")
    user = user_model.authenticate(email, password) if email and password else None
    if not user:
        return jsonify({"error": "Invalid email or password"}), 401
    token = auth.issue_access_token(user)
    response = jsonify({"user": _public_user(user), "access_token": token})
    response.set_cookie("access_token", token, httponly=True, secure=current_app.config["SESSION_COOKIE_SECURE"], samesite="Lax", max_age=current_app.config["JWT_ACCESS_MINUTES"] * 60)
    return response


@auth_bp.get("/me")
@auth.jwt_required
def me():
    return jsonify({"user": _public_user(g.current_user)})


@auth_bp.patch("/profile")
@auth.jwt_required
def update_profile():
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    email = data.get("email")
    if name is not None and not str(name).strip():
        return jsonify({"error": "Name cannot be empty"}), 400
    if email is not None and not _EMAIL_RE.match(user_model.normalize_email(email)):
        return jsonify({"error": "A valid email is required"}), 400
    try:
        user = user_model.update_profile(g.current_user["user_id"], name=name, email=email)
    except DuplicateKeyError:
        return jsonify({"error": "Email is already registered"}), 409
    return jsonify({"user": _public_user(user)})


@auth_bp.post("/forgot-password")
def forgot_password():
    data = request.get_json(silent=True) or {}
    user = user_model.find_auth_by_email(data.get("email"))
    response = {"message": "If that email exists, a reset link has been sent."}
    if user and user.get("is_active"):
        token = user_model.create_reset_token(user["user_id"])
        mailer.send_password_reset_email(user["email"], token)
        if current_app.config["EXPOSE_RESET_TOKEN"] and not mailer.is_configured():
            response["reset_token"] = token
    return jsonify(response)


@auth_bp.post("/reset-password")
def reset_password():
    data = request.get_json(silent=True) or {}
    token = data.get("token")
    password = data.get("password")
    if not token or not _valid_password(password):
        return jsonify({"error": "A reset token and password of at least 8 characters are required"}), 400
    reset = user_model.consume_reset_token(token)
    if not reset:
        return jsonify({"error": "Invalid or expired reset token"}), 400
    user_model.set_password(reset["user_id"], password)
    return jsonify({"message": "Password has been reset. Please log in again."})


@auth_bp.get("/admin/users")
@auth.admin_required
def list_users():
    return jsonify({"users": [_public_user(user) for user in user_model.list_users()]})


@auth_bp.patch("/admin/users/<user_id>")
@auth.admin_required
def update_user(user_id):
    data = request.get_json(silent=True) or {}
    user = user_model.find_by_id(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    if user_id == g.current_user["user_id"] and data.get("is_active") is False:
        return jsonify({"error": "You cannot deactivate your own account"}), 400
    if "name" in data and not str(data["name"]).strip():
        return jsonify({"error": "Name cannot be empty"}), 400
    if "email" in data and not _EMAIL_RE.match(user_model.normalize_email(data["email"])):
        return jsonify({"error": "A valid email is required"}), 400
    if "role" in data and data["role"] not in ("user", "admin"):
        return jsonify({"error": "Role must be user or admin"}), 400
    if "is_active" in data and not isinstance(data["is_active"], bool):
        return jsonify({"error": "is_active must be a boolean"}), 400
    removes_active_admin = (
        user.get("role") == "admin"
        and user.get("is_active")
        and (data.get("role") == "user" or data.get("is_active") is False)
    )
    if removes_active_admin and user_model.count_active_admins() <= 1:
        return jsonify({"error": "You cannot remove the last active administrator"}), 400
    try:
        if "name" in data or "email" in data:
            user = user_model.update_profile(user_id, name=data.get("name"), email=data.get("email"))
    except DuplicateKeyError:
        return jsonify({"error": "Email is already registered"}), 409
    if "role" in data:
        user = user_model.set_user_role(user_id, data["role"])
    if "is_active" in data:
        user = user_model.set_user_status(user_id, data["is_active"])
    return jsonify({"user": _public_user(user)})


@auth_bp.delete("/admin/users/<user_id>")
@auth.admin_required
def delete_user(user_id):
    user = user_model.find_by_id(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    if user_id == g.current_user["user_id"]:
        return jsonify({"error": "You cannot delete your own account"}), 400
    if (
        user.get("role") == "admin"
        and user.get("is_active")
        and user_model.count_active_admins() <= 1
    ):
        return jsonify({"error": "You cannot delete the last active administrator"}), 400
    user_model.delete_user(user_id)
    return jsonify({"message": "User deleted"})
