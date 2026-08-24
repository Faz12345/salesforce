"""Stateless JWT authentication helpers."""

from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import current_app, g, jsonify, request

from app.models import user as user_model


def issue_access_token(user):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user["user_id"],
        "role": user["role"],
        "token_version": user.get("token_version", 0),
        "iat": now,
        "exp": now + timedelta(minutes=current_app.config["JWT_ACCESS_MINUTES"]),
    }
    return jwt.encode(payload, current_app.config["JWT_SECRET_KEY"], algorithm="HS256")


def _unauthorized(message):
    return jsonify({"error": message}), 401


def get_request_user():
    """Return the authenticated user from a Bearer header or JWT cookie."""
    header = request.headers.get("Authorization", "")
    token = header[7:].strip() if header.startswith("Bearer ") else request.cookies.get("access_token", "")
    if not token:
        return None
    try:
        claims = jwt.decode(
            token,
            current_app.config["JWT_SECRET_KEY"],
            algorithms=["HS256"],
            options={"require": ["sub", "iat", "exp"]},
        )
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None
    user = user_model.find_auth_by_id(claims["sub"])
    if (
        not user
        or not user.get("is_active")
        or user.get("token_version", 0) != claims.get("token_version", 0)
    ):
        return None
    g.current_user = user
    g.jwt_claims = claims
    return user


def jwt_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not get_request_user():
            return _unauthorized("Authorization Bearer token required")
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    @jwt_required
    def wrapped(*args, **kwargs):
        if g.current_user.get("role") != "admin":
            return jsonify({"error": "Admin role required"}), 403
        return view(*args, **kwargs)

    return wrapped
