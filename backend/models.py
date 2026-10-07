from datetime import datetime, timezone
from extensions import db
from orgs import team_domain


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def ms(dt):
    """Naive-UTC datetime -> epoch milliseconds (what the frontends expect)."""
    if not dt:
        return None
    return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)


def initials(name):
    parts = [p for p in (name or "").split() if p]
    return ("".join(p[0] for p in parts[:2]) or "?").upper()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)          # 'customer' | 'company'
    company = db.Column(db.String(255))                      # customer's organisation
    team = db.Column(db.String(100))                         # agent's team
    is_admin = db.Column(db.Boolean, default=False, nullable=False)   # agents: can manage teammates
    active = db.Column(db.Boolean, default=True, nullable=False)      # deactivated users can't sign in
    notif_seen_at = db.Column(db.DateTime)                            # agents: notifications read up to here
    created_at = db.Column(db.DateTime, default=utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "role": self.role,
            "company": self.company,
            "team": self.team,
            "initials": initials(self.name),
            "teamDomain": team_domain(self.email) if self.role == "customer" else None,
            "isAdmin": bool(self.is_admin),
            "active": self.active is not False,
        }


class Ticket(db.Model):
    __tablename__ = "tickets"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.String(32), unique=True, nullable=False, index=True)  # TKT-1001
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100), nullable=False)
    issue_type = db.Column(db.String(30), nullable=False)    # bug | enhancement | support
    priority = db.Column(db.String(4))                        # P0..P3 or NULL
    status = db.Column(db.String(30), nullable=False, default="submitted")
    assigned_team = db.Column(db.String(100))
    assignee_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)   # agent who owns it

    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    customer_name = db.Column(db.String(255), nullable=False)
    customer_email = db.Column(db.String(255), nullable=False)
    customer_company = db.Column(db.String(255), nullable=False)

    created_at = db.Column(db.DateTime, default=utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=utcnow, index=True)
    resolved_at = db.Column(db.DateTime)
    closed_at = db.Column(db.DateTime)

    events = db.relationship("TicketEvent", backref="ticket", cascade="all, delete-orphan",
                             lazy="selectin", order_by="(TicketEvent.created_at, TicketEvent.id)")
    assignee = db.relationship("User", foreign_keys=[assignee_id], lazy="joined")
    attachments = db.relationship("Attachment", backref="ticket", cascade="all, delete-orphan",
                                  lazy="selectin", order_by="Attachment.id")

    def to_dict(self, signed_urls=None, for_customer=False):
        """signed_urls: optional {attachment_id: url}; when given, attachments carry URLs.
        for_customer: hide internal routing (team, assignee, agent names, internal notes)."""
        d = {
            "id": self.ticket_id,
            "title": self.title,
            "desc": self.description,
            "category": self.category,
            "type": self.issue_type,
            "priority": self.priority,
            "status": self.status,
            "team": self.assigned_team or "",
            "assignee": ({"id": self.assignee.id, "name": self.assignee.name,
                          "initials": initials(self.assignee.name)} if self.assignee else None),
            "customer": {
                "name": self.customer_name,
                "email": self.customer_email,
                "company": self.customer_company,
                "initials": initials(self.customer_name),
            },
            "createdAt": ms(self.created_at),
            "updatedAt": ms(self.updated_at),
            "resolvedAt": ms(self.resolved_at),
            "closedAt": ms(self.closed_at),
            "events": [e.to_dict() for e in self.events],
            "attachmentCount": len(self.attachments),
        }
        if for_customer:
            d["team"] = ""
            d["assignee"] = None
            d["events"] = [e.customer_view() for e in self.events if e.visible_to_customer()]
        if signed_urls is not None:
            d["attachments"] = [a.to_dict(signed_urls.get(a.id)) for a in self.attachments]
        return d


class TicketEvent(db.Model):
    __tablename__ = "ticket_events"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), nullable=False, index=True)
    # A status key (submitted, in_review, ...) for status changes, or 'note' for comments/updates
    stage = db.Column(db.String(30), nullable=False)
    label = db.Column(db.String(60))
    note = db.Column(db.Text)
    author_role = db.Column(db.String(20))   # 'customer' | 'company' | 'system'
    author_name = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=utcnow, index=True)

    # Notes customers may see; everything else (priority, routing, assignee) is internal.
    CUSTOMER_NOTE_LABELS = {"Reply to customer", "Asked customer", "Customer reply", "Customer added images"}

    def visible_to_customer(self):
        return self.stage != "note" or (self.label or "") in self.CUSTOMER_NOTE_LABELS

    def customer_view(self):
        d = self.to_dict()
        if self.author_role == "company":
            d["author"] = ""                     # no agent names
            if self.stage != "note":
                d["note"] = ""                   # e.g. "Engineering is now working on it"
        return d

    def to_dict(self):
        return {
            "stage": self.stage,
            "label": self.label or "",
            "note": self.note or "",
            "by": self.author_role or "system",
            "author": self.author_name or "",
            "at": ms(self.created_at),
        }


class Attachment(db.Model):
    __tablename__ = "attachments"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), nullable=False, index=True)
    storage_path = db.Column(db.String(500), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    content_type = db.Column(db.String(100), nullable=False)
    size_bytes = db.Column(db.Integer, nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=utcnow)

    def to_dict(self, url=None):
        return {
            "id": self.id,
            "name": self.filename,
            "type": self.content_type,
            "size": self.size_bytes,
            "url": url,
        }


class AppSetting(db.Model):
    """Small key/value store (e.g. the push-notification keys generated on first start)."""
    __tablename__ = "app_settings"

    key = db.Column(db.String(80), primary_key=True)
    value = db.Column(db.Text, nullable=False)


class PushSubscription(db.Model):
    """One browser/phone where a teammate turned on alerts."""
    __tablename__ = "push_subscriptions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    endpoint = db.Column(db.Text, nullable=False, unique=True)
    p256dh = db.Column(db.String(255), nullable=False)
    auth = db.Column(db.String(255), nullable=False)
    user_agent = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=utcnow)

    def info(self):
        return {"endpoint": self.endpoint, "keys": {"p256dh": self.p256dh, "auth": self.auth}}
