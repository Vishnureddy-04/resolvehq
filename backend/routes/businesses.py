"""Client business accounts and their portal users (company console → Clients).

Our team creates a business per client, then adds that client's people. Only those
people can sign in to the customer portal; everything they raise is filed under
their business.
"""
import re
import secrets

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import func
from werkzeug.security import generate_password_hash

from extensions import db
from models import Business, Ticket, User, ms

bp = Blueprint("businesses", __name__, url_prefix="/api/businesses")

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
OPEN = ("submitted", "in_review", "in_progress", "awaiting_customer")


def _agent():
    u = db.session.get(User, int(get_jwt_identity()))
    return u if u and u.role == "company" and u.active is not False else None


def _err(msg, code=400, **kw):
    return jsonify({"error": msg, **kw}), code


def _temp_password():
    # readable, no look-alike characters
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789"
    return "".join(secrets.choice(alphabet) for _ in range(10))


def _stats():
    """{business_id: {open, urgent, total, lastAt}} in two queries."""
    out = {}
    for bid, status, prio, upd in db.session.query(Ticket.business_id, Ticket.status, Ticket.priority,
                                                    Ticket.updated_at).filter(Ticket.business_id.isnot(None)):
        s = out.setdefault(bid, {"open": 0, "urgent": 0, "total": 0, "lastAt": None})
        s["total"] += 1
        if status in OPEN:
            s["open"] += 1
            if prio in ("P0", "P1"):
                s["urgent"] += 1
        at = ms(upd)
        if at and (s["lastAt"] is None or at > s["lastAt"]):
            s["lastAt"] = at
    return out


def _user_dict(u):
    return {
        "id": u.id, "name": u.name, "email": u.email,
        "active": u.active is not False,
        "mustChangePassword": bool(u.must_change_password),
        "lastLoginAt": ms(u.last_login_at), "createdAt": ms(u.created_at),
    }


def _business_dict(b, stats, user_counts):
    d = b.to_dict()
    d.update(stats.get(b.id, {"open": 0, "urgent": 0, "total": 0, "lastAt": None}))
    d["users"] = user_counts.get(b.id, 0)
    return d


def _name_taken(name, exclude_id=None):
    q = Business.query.filter(func.lower(Business.name) == name.lower())
    if exclude_id:
        q = q.filter(Business.id != exclude_id)
    return db.session.query(q.exists()).scalar()


# ---------------------------------------------------------------- businesses
@bp.get("")
@jwt_required()
def list_businesses():
    if not _agent():
        return _err("Company access only.", 403)
    counts = dict(db.session.query(User.business_id, func.count(User.id))
                  .filter(User.role == "customer", User.business_id.isnot(None))
                  .group_by(User.business_id).all())
    stats = _stats()
    rows = [_business_dict(b, stats, counts) for b in Business.query.all()]
    rows.sort(key=lambda r: (not r["active"], -r["open"], -(r["lastAt"] or 0), r["name"].lower()))
    return jsonify(rows), 200


@bp.post("")
@jwt_required()
def create_business():
    if not _agent():
        return _err("Company access only.", 403)
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()[:255]
    contact = (data.get("contactEmail") or "").strip().lower()[:255]
    if not name:
        return _err("Enter the business name.", fields={"name": "Required."})
    if contact and not EMAIL_RE.match(contact):
        return _err("Enter a valid contact email.", fields={"contactEmail": "Invalid email."})
    if _name_taken(name):
        return _err(f"A business called “{name}” already exists.", 409, fields={"name": "Already exists."})
    b = Business(name=name, contact_email=contact or None,
                 phone=(data.get("phone") or "").strip()[:50] or None,
                 notes=(data.get("notes") or "").strip()[:5000] or None)
    db.session.add(b)
    db.session.commit()
    return jsonify(_business_dict(b, {}, {})), 201


@bp.get("/<int:bid>")
@jwt_required()
def get_business(bid):
    if not _agent():
        return _err("Company access only.", 403)
    b = db.session.get(Business, bid)
    if not b:
        return _err("Business not found.", 404)
    users = User.query.filter_by(role="customer", business_id=b.id).order_by(User.active.desc(), User.name).all()
    d = _business_dict(b, _stats(), {b.id: len(users)})
    d["people"] = [_user_dict(u) for u in users]
    return jsonify(d), 200


@bp.patch("/<int:bid>")
@jwt_required()
def update_business(bid):
    me = _agent()
    if not me:
        return _err("Company access only.", 403)
    b = db.session.get(Business, bid)
    if not b:
        return _err("Business not found.", 404)
    data = request.get_json(silent=True) or {}
    if "name" in data:
        name = (data.get("name") or "").strip()[:255]
        if not name:
            return _err("Enter the business name.")
        if _name_taken(name, exclude_id=b.id):
            return _err(f"A business called “{name}” already exists.", 409)
        if name != b.name:
            b.name = name
            # keep stored copies in step (used in alerts and exports)
            Ticket.query.filter_by(business_id=b.id).update({Ticket.customer_company: name}, synchronize_session=False)
            User.query.filter_by(business_id=b.id).update({User.company: name}, synchronize_session=False)
    if "contactEmail" in data:
        c = (data.get("contactEmail") or "").strip().lower()
        if c and not EMAIL_RE.match(c):
            return _err("Enter a valid contact email.")
        b.contact_email = c or None
    if "phone" in data:
        b.phone = (data.get("phone") or "").strip()[:50] or None
    if "notes" in data:
        b.notes = (data.get("notes") or "").strip()[:5000] or None
    if "active" in data:
        if not me.is_admin:
            return _err("Only admins can pause or restore a business.", 403)
        b.active = bool(data["active"])
    db.session.commit()
    return get_business(bid)


# ---------------------------------------------------------------- users of a business
@bp.post("/<int:bid>/users")
@jwt_required()
def add_user(bid):
    if not _agent():
        return _err("Company access only.", 403)
    b = db.session.get(Business, bid)
    if not b:
        return _err("Business not found.", 404)
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()[:255]
    email = (data.get("email") or "").strip().lower()
    fields = {}
    if not name:
        fields["name"] = "Enter the person's name."
    if not EMAIL_RE.match(email):
        fields["email"] = "Enter a valid email."
    if fields:
        return _err("Please fix the highlighted fields.", fields=fields)
    existing = User.query.filter_by(email=email).first()
    if existing:
        where = (f"the business “{existing.business.name}”" if existing.role == "customer" and existing.business
                 else "a Finnoto teammate" if existing.role == "company" else "another account")
        return _err(f"This email is already used by {where}.", 409, fields={"email": "Already in use."})
    temp = _temp_password()
    u = User(email=email, name=name, role="customer", business_id=b.id, company=b.name,
             password_hash=generate_password_hash(temp), must_change_password=True)
    db.session.add(u)
    db.session.commit()
    out = _user_dict(u)
    out["tempPassword"] = temp            # shown once so we can send it to the person
    return jsonify(out), 201


@bp.patch("/<int:bid>/users/<int:uid>")
@jwt_required()
def update_user(bid, uid):
    me = _agent()
    if not me:
        return _err("Company access only.", 403)
    u = db.session.get(User, uid)
    if not u or u.role != "customer" or u.business_id != bid:
        return _err("User not found in this business.", 404)
    data = request.get_json(silent=True) or {}
    extra = {}
    if "name" in data and (data.get("name") or "").strip():
        u.name = data["name"].strip()[:255]
    if "active" in data:
        u.active = bool(data["active"])
    if data.get("resetPassword"):
        temp = _temp_password()
        u.password_hash = generate_password_hash(temp)
        u.must_change_password = True
        extra["tempPassword"] = temp
    db.session.commit()
    out = _user_dict(u)
    out.update(extra)
    return jsonify(out), 200
