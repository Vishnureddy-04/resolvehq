from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

import push
from extensions import db
from models import PushSubscription, User

bp = Blueprint("push", __name__, url_prefix="/api/push")


def _agent():
    u = db.session.get(User, int(get_jwt_identity()))
    return u if u and u.role == "company" else None


@bp.get("/key")
def key():
    return jsonify({"publicKey": push.public_key()}), 200


@bp.post("/subscribe")
@jwt_required()
def subscribe():
    me = _agent()
    if not me:
        return jsonify({"error": "Company access only."}), 403
    sub = (request.get_json(silent=True) or {}).get("subscription") or {}
    endpoint = (sub.get("endpoint") or "").strip()
    keys = sub.get("keys") or {}
    if not endpoint.startswith("https://") or not keys.get("p256dh") or not keys.get("auth"):
        return jsonify({"error": "Invalid subscription."}), 400
    row = PushSubscription.query.filter_by(endpoint=endpoint).first()
    if not row:
        row = PushSubscription(endpoint=endpoint)
        db.session.add(row)
    row.user_id = me.id                      # a shared browser follows whoever signed in last
    row.p256dh = keys["p256dh"][:255]
    row.auth = keys["auth"][:255]
    row.user_agent = (request.headers.get("User-Agent") or "")[:255]
    db.session.commit()
    devices = PushSubscription.query.filter_by(user_id=me.id).count()
    return jsonify({"ok": True, "devices": devices}), 200


@bp.post("/unsubscribe")
@jwt_required()
def unsubscribe():
    endpoint = ((request.get_json(silent=True) or {}).get("endpoint") or "").strip()
    if endpoint:
        PushSubscription.query.filter_by(endpoint=endpoint, user_id=int(get_jwt_identity())).delete()
        db.session.commit()
    return jsonify({"ok": True}), 200


@bp.post("/test")
@jwt_required()
def test():
    me = _agent()
    if not me:
        return jsonify({"error": "Company access only."}), 403
    n = push.send({"title": "ResolveHQ alerts are on",
                   "body": f"This device will alert you when a customer raises an issue, {me.name.split()[0]}.",
                   "url": "/company-portal", "tag": "rhq-test"}, user_ids=[me.id])
    if not n:
        return jsonify({"error": "Alerts aren't turned on for this device yet."}), 400
    return jsonify({"ok": True, "devices": n}), 200
