"""Company-console notifications: things customers did that the team should see.

Derived from ticket activity (no separate table): a new issue, a customer reply,
or images a customer added. Each agent has their own "read up to" time.
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import and_, or_

from extensions import db
from models import Ticket, TicketEvent, User, ms, utcnow

bp = Blueprint("notifications", __name__, url_prefix="/api/notifications")

KINDS = {"Customer reply": "reply", "Customer added images": "images"}


def _agent():
    u = db.session.get(User, int(get_jwt_identity()))
    return u if u and u.role == "company" else None


def _customer_activity():
    return and_(
        TicketEvent.author_role == "customer",
        or_(TicketEvent.stage == "submitted", TicketEvent.label.in_(list(KINDS))),
    )


@bp.get("")
@jwt_required()
def list_notifications():
    me = _agent()
    if not me:
        return jsonify({"error": "Company access only."}), 403
    limit = min(int(request.args.get("limit", 30)), 100)
    seen = me.notif_seen_at or me.created_at
    rows = (db.session.query(TicketEvent, Ticket)
            .join(Ticket, Ticket.id == TicketEvent.ticket_id)
            .filter(_customer_activity())
            .order_by(TicketEvent.created_at.desc(), TicketEvent.id.desc())
            .limit(limit).all())
    unread = (db.session.query(TicketEvent.id)
              .filter(_customer_activity(), TicketEvent.created_at > seen).count())
    items = []
    for e, t in rows:
        kind = "new" if e.stage == "submitted" else KINDS.get(e.label, "update")
        items.append({
            "id": e.id,
            "kind": kind,
            "ticketId": t.ticket_id,
            "title": t.title,
            "company": t.customer_company,
            "customer": e.author_name or t.customer_name,
            "urgent": kind == "new" and t.issue_type == "bug",
            "priority": t.priority,
            "note": (e.note or "")[:140] if kind != "new" else "",
            "at": ms(e.created_at),
            "unread": e.created_at > seen,
        })
    return jsonify({"unread": unread, "items": items, "seenAt": ms(seen)}), 200


@bp.post("/seen")
@jwt_required()
def mark_seen():
    me = _agent()
    if not me:
        return jsonify({"error": "Company access only."}), 403
    me.notif_seen_at = utcnow()
    db.session.commit()
    return jsonify({"unread": 0, "seenAt": ms(me.notif_seen_at)}), 200
