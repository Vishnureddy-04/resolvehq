import re

from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db, limiter
from models import User

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _token_for(user):
    return create_access_token(identity=str(user.id), additional_claims={"role": user.role})


@bp.post("/register")
@limiter.limit("10 per hour")
def register():
    """Public customer sign-up. Company agents cannot be created here."""
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    company = (data.get("company") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    errors = {}
    if not name:
        errors["name"] = "Please enter your name."
    if not company:
        errors["company"] = "Please enter your company name."
    if not EMAIL_RE.match(email):
        errors["email"] = "Enter a valid email address."
    if len(password) < 8:
        errors["password"] = "Use at least 8 characters."
    if errors:
        return jsonify({"error": "Please fix the highlighted fields.", "fields": errors}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "An account with this email already exists. Try signing in.",
                        "fields": {"email": "Already registered."}}), 409

    user = User(email=email, name=name[:255], company=company[:255], role="customer",
                password_hash=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()
    return jsonify({"access_token": _token_for(user), "user": user.to_dict()}), 201


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
    if role and role != user.role:
        where = "company console" if user.role == "company" else "customer portal"
        return jsonify({"error": f"This account belongs to the {where}."}), 403

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
    user.password_hash = generate_password_hash(new)
    db.session.commit()
    return jsonify({"message": "Password updated."}), 200
