"""Authentication helpers: bcrypt password hashing + JWT (HTTP-only cookie / Bearer)."""
from datetime import datetime, timedelta, timezone
from functools import wraps

import bcrypt
import jwt
from flask import request, jsonify, g

from config import Config
from models import User


# --- password hashing ------------------------------------------------------
def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# --- JWT -------------------------------------------------------------------
def create_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "name": user.name,
        "warehouse_id": user.warehouse_id,
        "iat": now,
        "exp": now + timedelta(hours=Config.JWT_EXP_HOURS),
    }
    return jwt.encode(payload, Config.JWT_SECRET, algorithm=Config.JWT_ALGO)


def _decode_token(token: str):
    return jwt.decode(token, Config.JWT_SECRET, algorithms=[Config.JWT_ALGO])


def _extract_token():
    """Accept token from HTTP-only cookie OR Authorization: Bearer header."""
    token = request.cookies.get("access_token")
    if token:
        return token
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth.split(" ", 1)[1]
    return None


# --- decorators ------------------------------------------------------------
def token_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = _extract_token()
        if not token:
            return jsonify({"error": "Authentication required"}), 401
        try:
            payload = _decode_token(token)
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        user = db_get_user(int(payload["sub"]))
        if not user:
            return jsonify({"error": "User no longer exists"}), 401
        g.current_user = user
        return fn(*args, **kwargs)

    return wrapper


def optional_auth(fn):
    """
    Public read-only endpoint: works with OR without a login.

    Sets g.current_user to the signed-in user when a valid token is present, and
    to None for a guest (browsing the shop before registering). A bad/expired
    token is treated as a guest rather than an error, so a stale cookie still
    lets someone browse the catalogue.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        g.current_user = None
        token = _extract_token()
        if token:
            try:
                payload = _decode_token(token)
                user = db_get_user(int(payload["sub"]))
                # a blocked account browses as a guest — it can't act anyway
                if user and not user.is_blocked:
                    g.current_user = user
            except (jwt.InvalidTokenError, KeyError, ValueError, TypeError):
                pass
        return fn(*args, **kwargs)

    return wrapper


def role_required(*roles):
    """Use AFTER token_required, or standalone (it implies token_required)."""
    def decorator(fn):
        @wraps(fn)
        @token_required
        def wrapper(*args, **kwargs):
            if g.current_user.role not in roles:
                return jsonify({"error": "Forbidden: insufficient role"}), 403
            # A blocked account keeps all its data but can perform NO actions.
            # /api/me + logout use token_required only, so they still work (lets the
            # user see the "you are blocked" notice and sign out).
            if g.current_user.is_blocked:
                return jsonify({
                    "error": "blocked",
                    "message": "Your account has been blocked by the administrator.",
                }), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def db_get_user(user_id: int):
    # local import keeps auth.py importable before app context exists
    from db import db
    return db.session.get(User, user_id)


# --- convenience role decorators (as requested in the spec) -----------------
def customer_required(fn):
    return role_required("customer")(fn)


def warehouse_required(fn):
    return role_required("warehouse")(fn)


def admin_required(fn):
    return role_required("admin")(fn)


# --- audit log helper ------------------------------------------------------
def audit(action: str, details: str = None):
    """Record an action by the current user. Safe to call inside any request."""
    from db import db
    from models import AuditLog
    user = getattr(g, "current_user", None)
    log = AuditLog(
        user_id=user.id if user else None,
        action=action,
        details=details,
        ip_address=request.headers.get("X-Forwarded-For", request.remote_addr),
    )
    db.session.add(log)
    # caller is responsible for commit (often part of a larger transaction)
