"""Web push alerts to the team's laptops and phones (works with the console closed).

Keys (VAPID) are generated automatically on first start and kept in the database,
so no setup is needed. Optional: VAPID_SUBJECT=mailto:you@company.com.
"""
import base64
import json
import threading

from cryptography.hazmat.primitives import serialization
from flask import current_app
from py_vapid import Vapid
from pywebpush import WebPushException, webpush
from sqlalchemy.exc import IntegrityError

from extensions import db

_KEY = "vapid_private_pem"
_cache = {}


def _b64url(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def ensure_keys():
    """Create the push keys once; every worker then reads the same ones."""
    from models import AppSetting
    row = db.session.get(AppSetting, _KEY)
    if row:
        return
    v = Vapid()
    v.generate_keys()
    db.session.add(AppSetting(key=_KEY, value=v.private_pem().decode()))
    try:
        db.session.commit()
    except IntegrityError:          # another worker created them at the same moment
        db.session.rollback()


def _vapid():
    if "v" not in _cache:
        from models import AppSetting
        row = db.session.get(AppSetting, _KEY)
        if not row:
            ensure_keys()
            row = db.session.get(AppSetting, _KEY)
        _cache["v"] = Vapid.from_pem(row.value.encode())
    return _cache["v"]


def public_key():
    pub = _vapid().public_key.public_bytes(serialization.Encoding.X962,
                                           serialization.PublicFormat.UncompressedPoint)
    return _b64url(pub)


def _subject():
    s = current_app.config.get("VAPID_SUBJECT") or ""
    if not s:
        admin = current_app.config.get("ADMIN_EMAIL") or "alerts@resolvehq.app"
        s = "mailto:" + admin
    return s


def _deliver(app, subs, payload, vapid, subject):
    """Runs in a background thread so the customer never waits for push services."""
    dead = []
    body = json.dumps(payload)
    for sub_id, info in subs:
        try:
            webpush(subscription_info=info, data=body, vapid_private_key=vapid,
                    vapid_claims={"sub": subject}, ttl=86400, timeout=10)
        except WebPushException as e:
            code = getattr(getattr(e, "response", None), "status_code", None)
            if code in (404, 410):          # the device unsubscribed or the browser was reset
                dead.append(sub_id)
            else:
                app.logger.warning("push failed (%s): %s", code, str(e)[:200])
        except Exception as e:
            app.logger.warning("push error: %s", str(e)[:200])
    if dead:
        with app.app_context():
            from models import PushSubscription
            PushSubscription.query.filter(PushSubscription.id.in_(dead)).delete(synchronize_session=False)
            db.session.commit()


def send(payload, user_ids=None):
    """Push to all active company teammates (or just user_ids)."""
    from models import PushSubscription, User
    q = (PushSubscription.query.join(User, User.id == PushSubscription.user_id)
         .filter(User.role == "company", User.active.isnot(False)))
    if user_ids is not None:
        q = q.filter(PushSubscription.user_id.in_(list(user_ids)))
    subs = [(s.id, s.info()) for s in q.all()]
    if not subs:
        return 0
    app = current_app._get_current_object()
    threading.Thread(target=_deliver, args=(app, subs, payload, _vapid(), _subject()), daemon=True).start()
    return len(subs)
