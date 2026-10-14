import re

from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db, limiter
from models import User, utcnow

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _token_for(user):
    return create_access_token(identity=str(user.id), additional_claims={"role": user.role})


@bp.post("/register")
@limiter.limit("10 per hour")
def register():
    """Customer accounts are created by our team inside a business account (Clients tab)."""
    return jsonify({"error": "Accounts are created by our team. Please contact your account manager for access."}), 403


@bp.post("/login")
@limiter.limit("20 per 10 minutes")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    role = data.get("role")  # optional: which portal the user is signing into

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Email or password is incorrect."}), 401
    if user.active is False:
        return jsonify({"error": "This account has been deactivated. Contact your admin."}), 403
    if user.role == "customer" and (not user.business or user.business.active is False):
        return jsonify({"error": "Your company's access is paused. Please contact your account manager."}), 403
    if role and role != user.role:
        where = "company console" if user.role == "company" else "customer portal"
        return jsonify({"error": f"This account belongs to the {where}."}), 403

    user.last_login_at = utcnow()
    db.session.commit()
    return jsonify({"access_token": _token_for(user), "user": user.to_dict()}), 200


@bp.get("/me")
@jwt_required()
def me():
    user = db.session.get(User, int(get_jwt_identity()))
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user.to_dict()), 200


@bp.post("/password")
@jwt_required()
@limiter.limit("10 per hour")
def change_password():
    user = db.session.get(User, int(get_jwt_identity()))
    data = request.get_json(silent=True) or {}
    current = data.get("current") or ""
    new = data.get("new") or ""
    if not user or not check_password_hash(user.password_hash, current):
        return jsonify({"error": "Your current password is incorrect.", "fields": {"current": "Incorrect."}}), 400
    if len(new) < 8:
        return jsonify({"error": "Use at least 8 characters.", "fields": {"new": "Too short."}}), 400
    if new == current:
        return jsonify({"error": "Choose a new password that's different from the temporary one.", "fields": {"new": "Same as before."}}), 400
    user.password_hash = generate_password_hash(new)
    user.must_change_password = False
    db.session.commit()
    return jsonify({"message": "Password updated."}), 200
