"""/api/register, /api/login, /api/logout, /api/me, + shared payment-PIN endpoints"""
import os
import uuid
import random
from datetime import datetime, timedelta, timezone

from flask import Blueprint, request, jsonify, make_response, g
from werkzeug.utils import secure_filename

from db import db
from models import User
from auth import hash_password, verify_password, create_token, token_required, audit
from config import Config
from utils.email_util import send_bulk, email_enabled


def _mask_email(email):
    try:
        name, domain = email.split("@", 1)
        shown = name[0] + "***" if name else "***"
        return f"{shown}@{domain}"
    except ValueError:
        return "your email"

bp = Blueprint("auth", __name__, url_prefix="/api")


def _set_auth_cookie(resp, token):
    resp.set_cookie(
        "access_token", token,
        httponly=True, samesite="Lax", secure=False,  # secure=True behind HTTPS
        max_age=Config.JWT_EXP_HOURS * 3600,
    )
    return resp


@bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    account_type = (data.get("account_type") or "customer").strip().lower()
    phone = (data.get("phone") or "").strip() or None

    if not name or not email or not password:
        return jsonify({"error": "name, email and password are required"}), 400
    if len(password) < 6:
        return jsonify({"error": "password must be at least 6 characters"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "email already registered"}), 409

    if account_type == "warehouse":
        # A warehouse signs itself up: create its Warehouse record + a warehouse
        # login linked to it, so it can log in straight into the warehouse dashboard.
        from models import Warehouse
        wh_name = (data.get("warehouse_name") or "").strip()
        location = (data.get("location") or "").strip()
        if not wh_name or not location:
            return jsonify({"error": "warehouse name and location are required"}), 400
        warehouse = Warehouse(name=wh_name, location=location, phone=phone,
                              email=email, manager_name=name)
        db.session.add(warehouse)
        db.session.flush()  # assign warehouse.id before linking the user
        user = User(name=name, email=email, password_hash=hash_password(password),
                    role="warehouse", warehouse_id=warehouse.id, phone=phone)
    else:
        # Default public registration is customer. They give their delivery address
        # up front (same address field the warehouse fills in) so the profile and
        # checkout are pre-filled.
        address = (data.get("address") or "").strip() or None
        user = User(name=name, email=email, password_hash=hash_password(password),
                    role="customer", phone=phone, address=address)
    user.last_login = datetime.now(timezone.utc)   # they're authenticated right away
    db.session.add(user)
    db.session.commit()

    token = create_token(user)
    resp = make_response(jsonify({"user": user.to_dict(), "token": token}), 201)
    return _set_auth_cookie(resp, token)


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if not user or not verify_password(password, user.password_hash):
        return jsonify({"error": "invalid email or password"}), 401

    # audit the login + stamp last-active time (for the admin's Active/Inactive view)
    user.last_login = datetime.now(timezone.utc)
    from models import AuditLog
    db.session.add(AuditLog(
        user_id=user.id, action="login", details=f"{user.role} login",
        ip_address=request.headers.get("X-Forwarded-For", request.remote_addr),
    ))
    db.session.commit()

    token = create_token(user)
    resp = make_response(jsonify({"user": user.to_dict(), "token": token}))
    return _set_auth_cookie(resp, token)


@bp.post("/logout")
def logout():
    resp = make_response(jsonify({"message": "logged out"}))
    resp.delete_cookie("access_token")
    return resp


@bp.get("/me")
@token_required
def me():
    # Refresh "last active" (the header hits this on every page). Throttle to once
    # every few minutes so we don't write on every single request.
    u = g.current_user
    now = datetime.now(timezone.utc)
    last = u.last_login
    if last is not None and last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    if last is None or (now - last) > timedelta(minutes=5):
        u.last_login = now
        db.session.commit()
    data = u.to_dict()
    # A warehouse account's address is its warehouse's location (entered at sign-up),
    # which lives on the warehouse, not the user — surface it on the profile so the
    # address field isn't blank. The user can still edit/override it.
    if u.role == "warehouse" and u.warehouse is not None:
        if not data.get("address"):
            data["address"] = u.warehouse.location
        if not data.get("pincode"):
            data["pincode"] = u.warehouse.pincode
    data["blocked"] = u.is_blocked   # effective (own flag OR the staff's warehouse is blocked)
    bu = u.effective_blocked_until
    data["blocked_until"] = bu.isoformat() if bu else None
    return jsonify({"user": data})


@bp.put("/me")
@token_required
def update_me():
    """Update the logged-in user's own profile (name/phone/address/pincode).

    For a warehouse account the profile fields *are* the warehouse's identity — the
    name is the warehouse/business name and the address is its location — so we mirror
    edits onto the linked Warehouse record too. Otherwise the warehouse details shown
    to admins and customers would go stale the moment the owner edits their profile.
    """
    data = request.get_json(silent=True) or {}
    user = g.current_user
    wh = user.warehouse if user.role == "warehouse" else None
    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify({"error": "name cannot be empty"}), 400
        user.name = name
        if wh:
            wh.name = name
            wh.manager_name = name
    if "phone" in data:
        user.phone = (data.get("phone") or "").strip() or None
        if wh:
            wh.phone = user.phone
    if "address" in data:
        address = (data.get("address") or "").strip() or None
        user.address = address
        if wh:
            wh.location = address
    if "pincode" in data:
        user.pincode = (data.get("pincode") or "").strip() or None
        if wh:
            wh.pincode = user.pincode
    audit("profile_update")
    db.session.commit()
    return jsonify({"message": "profile updated", "user": user.to_dict()})


@bp.post("/me/avatar")
@token_required
def upload_avatar():
    """Upload/replace the logged-in user's profile picture (stored in uploads/)."""
    user = g.current_user
    if "file" not in request.files:
        return jsonify({"error": "no file part named 'file'"}), 400
    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "empty filename"}), 400
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in Config.IMAGE_EXTENSIONS:
        return jsonify({"error": f"image must be one of: {', '.join(sorted(Config.IMAGE_EXTENSIONS))}"}), 400

    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    safe = secure_filename(f"avatar_{user.id}_{uuid.uuid4().hex[:8]}.{ext}")
    file.save(os.path.join(Config.UPLOAD_FOLDER, safe))

    # remove the previous avatar file if any
    if user.avatar_path:
        old = os.path.join(Config.UPLOAD_FOLDER, user.avatar_path)
        if os.path.exists(old):
            try:
                os.remove(old)
            except OSError:
                pass

    user.avatar_path = safe
    audit("avatar_upload", safe)
    db.session.commit()
    return jsonify({"message": "avatar uploaded", "avatar_path": safe, "user": user.to_dict()})


@bp.delete("/me/avatar")
@token_required
def remove_avatar():
    user = g.current_user
    if user.avatar_path:
        old = os.path.join(Config.UPLOAD_FOLDER, user.avatar_path)
        if os.path.exists(old):
            try:
                os.remove(old)
            except OSError:
                pass
    user.avatar_path = None
    audit("avatar_remove")
    db.session.commit()
    return jsonify({"message": "avatar removed"})


# ---------------------------------------- shared numeric payment PIN (any user)
@bp.get("/payment-pin")
@token_required
def my_pin_status():
    return jsonify({"pin_set": bool(g.current_user.payment_pin_hash)})


@bp.post("/payment-pin")
@token_required
def my_pin_set():
    """Create/set the 6-digit payment PIN (first-time setup)."""
    pin = ((request.get_json(silent=True) or {}).get("new_pin") or "").strip()
    if not (pin.isdigit() and len(pin) == 6):
        return jsonify({"error": "PIN must be exactly 6 digits"}), 400
    g.current_user.payment_pin_hash = hash_password(pin)
    audit("payment_pin_set")
    db.session.commit()
    return jsonify({"ok": True, "message": "payment PIN saved"})


@bp.post("/verify-pin")
@token_required
def my_pin_verify():
    """Verify the numeric payment PIN entered at checkout."""
    if not g.current_user.payment_pin_hash:
        return jsonify({"ok": False, "pin_set": False})
    pin = (request.get_json(silent=True) or {}).get("pin", "")
    return jsonify({"ok": verify_password(pin, g.current_user.payment_pin_hash), "pin_set": True})


def _pin_reset_code_valid(user, code):
    if not user.pin_reset_code or not user.pin_reset_expires:
        return False
    exp = user.pin_reset_expires
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > exp:
        return False
    return verify_password(code or "", user.pin_reset_code)


@bp.post("/pin-reset/request")
@token_required
def my_pin_reset_request():
    """Email a 6-digit code to the user's email; required to change the PIN."""
    user = g.current_user
    code = f"{random.randint(0, 999999):06d}"
    user.pin_reset_code = hash_password(code)
    user.pin_reset_expires = datetime.now(timezone.utc) + timedelta(minutes=10)
    db.session.commit()
    result = send_bulk([user.email], "Your PIN reset code",
                       f"Your jaggery payment-PIN reset code is {code}. It expires in 10 minutes.")
    audit("pin_reset_requested", _mask_email(user.email))
    db.session.commit()
    resp = {"sent": True, "email": _mask_email(user.email), "delivery": result.get("status")}
    if not email_enabled():
        resp["dev_code"] = code  # demo: surface the code so it's testable
    return jsonify(resp)


@bp.post("/pin-reset/verify")
@token_required
def my_pin_reset_verify():
    code = (request.get_json(silent=True) or {}).get("code", "")
    return jsonify({"ok": _pin_reset_code_valid(g.current_user, code)})


@bp.post("/pin-reset/confirm")
@token_required
def my_pin_reset_confirm():
    """Set a new PIN — only valid with the emailed code."""
    data = request.get_json(silent=True) or {}
    user = g.current_user
    if not _pin_reset_code_valid(user, data.get("code", "")):
        return jsonify({"error": "invalid or expired verification code"}), 403
    new_pin = (data.get("new_pin") or "").strip()
    if not (new_pin.isdigit() and len(new_pin) == 6):
        return jsonify({"error": "PIN must be exactly 6 digits"}), 400
    user.payment_pin_hash = hash_password(new_pin)
    user.pin_reset_code = None
    user.pin_reset_expires = None
    audit("payment_pin_reset")
    db.session.commit()
    return jsonify({"ok": True, "message": "PIN reset"})


@bp.post("/verify-password")
@token_required
def verify_password_route():
    """Step-up check: confirm the logged-in user's password (e.g. before paying)."""
    pw = (request.get_json(silent=True) or {}).get("password", "")
    return jsonify({"ok": verify_password(pw, g.current_user.password_hash)})


@bp.post("/change-password")
@token_required
def change_password():
    data = request.get_json(silent=True) or {}
    current = data.get("current_password") or ""
    new = data.get("new_password") or ""
    if not verify_password(current, g.current_user.password_hash):
        return jsonify({"error": "current password is incorrect"}), 403
    if len(new) < 6:
        return jsonify({"error": "new password must be at least 6 characters"}), 400
    g.current_user.password_hash = hash_password(new)
    audit("password_change")
    db.session.commit()
    return jsonify({"message": "password changed"})
