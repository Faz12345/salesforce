"""MongoDB data access for users and one-time password reset tokens."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from werkzeug.security import check_password_hash, generate_password_hash

import app as app_module


def _db():
    return app_module.db


def _now():
    return datetime.now(timezone.utc)


def _serialize(doc):
    if doc is None:
        return None
    result = dict(doc)
    result.pop("_id", None)
    result.pop("password_hash", None)
    result.pop("token_version", None)
    return result


def normalize_email(email):
    return str(email or "").strip().lower()


def find_by_id(user_id):
    return _serialize(_db().users.find_one({"user_id": user_id}))


def find_auth_by_id(user_id):
    return _db().users.find_one({"user_id": user_id})


def find_by_email(email):
    return _serialize(_db().users.find_one({"email": normalize_email(email)}))


def find_auth_by_email(email):
    return _db().users.find_one({"email": normalize_email(email)})


def create_user(email, password, name, role="user"):
    now = _now()
    user = {
        "user_id": str(uuid4()),
        "email": normalize_email(email),
        "name": str(name).strip(),
        "role": role,
        "password_hash": generate_password_hash(password),
        "is_active": True,
        "token_version": 0,
        "created_at": now,
        "updated_at": now,
        "last_login_at": None,
    }
    _db().users.insert_one(user)
    return _serialize(user)


def authenticate(email, password):
    user = find_auth_by_email(email)
    if not user or not user.get("is_active") or not check_password_hash(
        user["password_hash"], password
    ):
        return None
    now = _now()
    _db().users.update_one(
        {"user_id": user["user_id"]}, {"$set": {"last_login_at": now, "updated_at": now}}
    )
    user["last_login_at"] = now
    return user


def update_profile(user_id, name=None, email=None):
    fields = {"updated_at": _now()}
    if name is not None:
        fields["name"] = str(name).strip()
    if email is not None:
        fields["email"] = normalize_email(email)
    _db().users.update_one({"user_id": user_id}, {"$set": fields})
    return find_by_id(user_id)


def set_password(user_id, password):
    _db().users.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "password_hash": generate_password_hash(password),
                "updated_at": _now(),
            },
            "$inc": {"token_version": 1},
        },
    )


def list_users():
    return [_serialize(user) for user in _db().users.find().sort("created_at", 1)]


def count_active_admins():
    return _db().users.count_documents({"role": "admin", "is_active": True})


def delete_user(user_id):
    result = _db().users.delete_one({"user_id": user_id})
    if result.deleted_count:
        _db().password_reset_tokens.delete_many({"user_id": user_id})
        return True
    return False


def set_user_status(user_id, is_active):
    _db().users.update_one(
        {"user_id": user_id},
        {"$set": {"is_active": bool(is_active), "updated_at": _now()}, "$inc": {"token_version": 1}},
    )
    return find_by_id(user_id)


def set_user_role(user_id, role):
    _db().users.update_one(
        {"user_id": user_id},
        {"$set": {"role": role, "updated_at": _now()}, "$inc": {"token_version": 1}},
    )
    return find_by_id(user_id)


def create_reset_token(user_id, expires_in=timedelta(hours=1)):
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    _db().password_reset_tokens.update_many(
        {"user_id": user_id, "used": False}, {"$set": {"used": True}}
    )
    _db().password_reset_tokens.insert_one(
        {
            "token_hash": token_hash,
            "user_id": user_id,
            "expires_at": _now() + expires_in,
            "created_at": _now(),
            "used": False,
        }
    )
    return raw_token


def consume_reset_token(raw_token):
    token_hash = hashlib.sha256(str(raw_token).encode("utf-8")).hexdigest()
    token = _db().password_reset_tokens.find_one_and_update(
        {
            "token_hash": token_hash,
            "used": False,
            "expires_at": {"$gt": _now()},
        },
        {"$set": {"used": True}},
    )
    return token
