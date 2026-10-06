"""Company teammates (agents). Any agent can list them; only admins can add or change them."""
import re
import secrets

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import func
from werkzeug.security import generate_password_hash

from extensions import db
from models import Ticket, User

bp = Blueprint("agents", __name__, url_prefix="/api/agents")

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
TEAMS = {"Engineering", "Implementation", "Product", "Support", "Billing"}
OPEN = ("submitted", "in_review", "in_progress", "awaiting_customer")


def _me():
    u = db.session.get(User, int(get_jwt_identity()))
    return u if u and u.role == "company" else None


def _err(msg, code=400, **kw):
    return jsonify({"error": msg, **kw}), code


def _agent_dict(u, open_counts):
    d = u.to_dict()
    d["openAssigned"] = open_counts.get(u.id, 0)
    d["createdAt"] = int(u.created_at.timestamp() * 1000) if u.created_at else None
    return d


def _open_counts():
    rows = (db.session.query(Ticket.assignee_id, func.count(Ticket.id))
            .filter(Ticket.assignee_id.isnot(None), Ticket.status.in_(OPEN))
            .group_by(Ticket.assignee_id).all())
    return dict(rows)


@bp.get("")
@jwt_required()
def list_agents():
    if not _me():
        return _err("Company access only.", 403)
    agents = User.query.filter_by(role="company").order_by(User.active.desc(), User.name).all()
    counts = _open_counts()
    return jsonify([_agent_dict(a, counts) for a in agents]), 200


@bp.post("")
@jwt_required()
def add_agent():
    me = _me()
    if not me:
        return _err("Company access only.", 403)
    if not me.is_admin:
        return _err("Only admins can add teammates.", 403)
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    team = data.get("team") or "Support"
    password = data.get("password") or ""
    fields = {}
    if not name:
        fields["name"] = "Enter a name."
    if not EMAIL_RE.match(email):
        fields["email"] = "Enter a valid email."
    if team not in TEAMS:
        fields["team"] = "Pick a team."
    if password and len(password) < 8:
        fields["password"] = "Use at least 8 characters."
    if fields:
        return _err("Please fix the highlighted fields.", fields=fields)
    existing = User.query.filter_by(email=email).first()
    if existing:
        what = "a customer account" if existing.role == "customer" else "a teammate"
        return _err(f"This email is already used by {what}.", 409, fields={"email": "Already in use."})
    temp = password or secrets.token_urlsafe(9)
    u = User(email=email, name=name[:255], role="company", company="ResolveHQ", team=team,
             is_admin=bool(data.get("isAdmin")), password_hash=generate_password_hash(temp))
    db.session.add(u)
    db.session.commit()
    out = _agent_dict(u, {})
    out["tempPassword"] = temp  # shown once to the admin so they can share it
    return jsonify(out), 201


@bp.patch("/<int:agent_id>")
@jwt_required()
def update_agent(agent_id):
    me = _me()
    if not me:
        return _err("Company access only.", 403)
    if not me.is_admin:
        return _err("Only admins can change teammates.", 403)
    u = db.session.get(User, agent_id)
    if not u or u.role != "company":
        return _err("Teammate not found.", 404)
    data = request.get_json(silent=True) or {}
    out_extra = {}

    if "name" in data and (data["name"] or "").strip():
        u.name = data["name"].strip()[:255]
    if "team" in data:
        if data["team"] not in TEAMS:
            return _err("Pick a team.")
        u.team = data["team"]
    if "isAdmin" in data:
        if u.id == me.id and not data["isAdmin"]:
            return _err("You can't remove your own admin access.")
        u.is_admin = bool(data["isAdmin"])
    if "active" in data:
        if u.id == me.id and not data["active"]:
            return _err("You can't deactivate yourself.")
        u.active = bool(data["active"])
        if not u.active:
            # hand their open tickets back to the queue
            Ticket.query.filter(Ticket.assignee_id == u.id, Ticket.status.in_(OPEN)) \
                .update({Ticket.assignee_id: None}, synchronize_session=False)
    if data.get("resetPassword"):
        temp = secrets.token_urlsafe(9)
        u.password_hash = generate_password_hash(temp)
        out_extra["tempPassword"] = temp

    # always keep at least one active admin
    if not User.query.filter_by(role="company", is_admin=True, active=True).count():
        db.session.rollback()
        return _err("There must be at least one active admin.")
    db.session.commit()
    out = _agent_dict(u, _open_counts())
    out.update(out_extra)
    return jsonify(out), 200
