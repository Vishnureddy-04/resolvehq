from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

import storage
from extensions import db, limiter
from models import Attachment, Ticket, TicketEvent, User, utcnow
from orgs import same_team, team_domain

bp = Blueprint("tickets", __name__, url_prefix="/api/tickets")

TYPES = {"bug", "enhancement", "support"}
CATEGORIES = {"Product bug", "Onboarding", "Billing", "Feature request", "Integration",
              "Account & access", "Other"}
STATUSES = {"submitted", "in_review", "in_progress", "awaiting_customer", "resolved", "closed"}
PRIORITIES = {"P0", "P1", "P2", "P3"}
TEAMS = {"Engineering", "Implementation", "Product", "Support", "Billing"}


# ---------------------------------------------------------------- helpers
def current_user():
    return db.session.get(User, int(get_jwt_identity()))


def err(msg, code=400, **extra):
    return jsonify({"error": msg, **extra}), code


def find_ticket_for(user, code, write=False):
    """Customers may read their own and their teammates' tickets, but only change their own."""
    t = Ticket.query.filter_by(ticket_id=code).first()
    if not t:
        return None
    if user.role == "customer" and t.created_by != user.id:
        if write or not same_team(user.email, t.customer_email):
            return None  # don't reveal other customers' tickets exist
    return t


def log(ticket, stage, user=None, label="", note=""):
    ticket.events.append(TicketEvent(
        stage=stage, label=label[:60] if label else None, note=note or None,
        author_role=(user.role if user else "system"),
        author_name=(user.name if user else None),
    ))


def set_status(ticket, new_status, user):
    if new_status == ticket.status:
        return
    ticket.status = new_status
    now = utcnow()
    if new_status == "resolved" and not ticket.resolved_at:
        ticket.resolved_at = now
    if new_status == "closed":
        ticket.closed_at = now
        if not ticket.resolved_at:
            ticket.resolved_at = now
    if new_status not in ("resolved", "closed"):
        ticket.closed_at = None
    log(ticket, new_status, user)


def read_images(existing=0):
    """Validate uploaded images. Returns (list_of(name, bytes, ctype), error_response|None)."""
    cfg = current_app.config
    files = [f for f in request.files.getlist("files") if f and f.filename]
    if existing + len(files) > cfg["MAX_FILES_PER_TICKET"]:
        return None, err(f"You can attach up to {cfg['MAX_FILES_PER_TICKET']} images per issue.")
    out = []
    for f in files:
        data = f.read(cfg["MAX_FILE_BYTES"] + 1)
        if len(data) > cfg["MAX_FILE_BYTES"]:
            return None, err(f"“{f.filename}” is larger than 5 MB.")
        if not data:
            return None, err(f"“{f.filename}” is empty.")
        ctype = storage.sniff_image_type(data[:16])
        if not ctype:
            return None, err(f"“{f.filename}” isn't a PNG, JPG or WebP image.")
        out.append((f.filename[-200:], data, ctype))
    return out, None


def store_images(ticket, images, user):
    """Upload images; on any failure remove what was uploaded and re-raise."""
    saved = []
    try:
        for name, data, ctype in images:
            path = storage.new_path(ticket.ticket_id, ctype)
            storage.save(path, data, ctype)
            saved.append(path)
            ticket.attachments.append(Attachment(
                storage_path=path, filename=name, content_type=ctype,
                size_bytes=len(data), uploaded_by=user.id))
    except Exception:
        storage.delete(saved)
        raise
    return saved


def detail(ticket, viewer=None):
    d = ticket.to_dict(signed_urls=storage.signed_urls(ticket.attachments),
                       for_customer=viewer is not None and viewer.role == "customer")
    if viewer is not None:
        d["mine"] = ticket.created_by == viewer.id
    return d


# ---------------------------------------------------------------- customer: create
@bp.post("")
@jwt_required()
@limiter.limit("30 per hour")
def create_ticket():
    user = current_user()
    if not user or user.role != "customer":
        return err("Only customers can submit issues.", 403)

    form = request.form if request.form else (request.get_json(silent=True) or {})
    title = (form.get("title") or "").strip()
    desc = (form.get("description") or "").strip()
    category = (form.get("category") or "Other").strip()
    itype = (form.get("type") or "").strip()

    fields = {}
    if not title:
        fields["title"] = "Please add a title."
    if not desc:
        fields["description"] = "Please describe the issue."
    if itype not in TYPES:
        fields["type"] = "Choose Urgent fix or Feature change."
    if fields:
        return err("Please fill in the required fields.", fields=fields)
    if category not in CATEGORIES:
        category = "Other"

    images, bad = read_images()
    if bad:
        return bad

    t = Ticket(ticket_id="PENDING-" + storage.uuid.uuid4().hex[:12], title=title[:200],
               description=desc[:20000], category=category, issue_type=itype, status="submitted",
               created_by=user.id, customer_name=user.name, customer_email=user.email,
               customer_company=user.company or "—")
    db.session.add(t)
    db.session.flush()
    t.ticket_id = f"TKT-{1000 + t.id}"
    log(t, "submitted", user, note="Issue submitted — our team will review shortly")
    if itype == "bug":  # "Urgent fix": blocking the customer's operations
        t.priority = "P0"
        log(t, "note", user, label="Priority", note="Set to P0 — customer marked this as an urgent fix")

    saved = []
    try:
        saved = store_images(t, images, user)
        db.session.commit()
    except Exception:
        db.session.rollback()
        storage.delete(saved)
        current_app.logger.exception("ticket create failed")
        return err("We couldn't save your attachments. Please try again.", 502)

    return jsonify(detail(t, user)), 201


@bp.post("/<code>/attachments")
@jwt_required()
@limiter.limit("30 per hour")
def add_attachments(code):
    user = current_user()
    t = find_ticket_for(user, code)
    if not t:
        return err("Ticket not found", 404)
    if user.role == "customer" and t.created_by != user.id:
        return err(f"Only {t.customer_name} (who raised this issue) can add images.", 403)
    if user.role != "customer":
        return err("Only the customer can add attachments.", 403)
    images, bad = read_images(existing=len(t.attachments))
    if bad:
        return bad
    if not images:
        return err("Choose at least one image.")
    saved = []
    try:
        saved = store_images(t, images, user)
        log(t, "note", user, label="Customer added images",
            note=f"{len(images)} image{'s' if len(images) > 1 else ''} attached")
        t.updated_at = utcnow()
        db.session.commit()
    except Exception:
        db.session.rollback()
        storage.delete(saved)
        current_app.logger.exception("attachment add failed")
        return err("We couldn't save your attachments. Please try again.", 502)
    return jsonify(detail(t, user)), 201


# ---------------------------------------------------------------- read
@bp.get("")
@jwt_required()
def list_tickets():
    user = current_user()
    if not user:
        return err("User not found", 401)
    q = Ticket.query
    if user.role == "customer":
        domain = team_domain(user.email)
        if domain:
            safe = domain.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            q = q.filter(Ticket.customer_email.like("%@" + safe, escape="\\"))
        else:
            q = q.filter_by(created_by=user.id)
    tickets = q.order_by(Ticket.updated_at.desc()).all()
    out = []
    for t in tickets:
        d = t.to_dict(for_customer=user.role == "customer")
        d["mine"] = t.created_by == user.id
        out.append(d)
    return jsonify(out), 200


@bp.get("/<code>")
@jwt_required()
def get_ticket(code):
    user = current_user()
    t = find_ticket_for(user, code) if user else None
    if not t:
        return err("Ticket not found", 404)
    return jsonify(detail(t, user)), 200


# ---------------------------------------------------------------- company: triage
@bp.patch("/<code>")
@jwt_required()
def update_ticket(code):
    user = current_user()
    if not user or user.role != "company":
        return err("Only company agents can update tickets.", 403)
    t = Ticket.query.filter_by(ticket_id=code).first()
    if not t:
        return err("Ticket not found", 404)
    data = request.get_json(silent=True) or {}

    if "priority" in data:
        p = data["priority"] or None
        if p is not None and p not in PRIORITIES:
            return err("Invalid priority")
        if p != t.priority:
            t.priority = p
            if t.status == "submitted" and p:
                t.status = "in_review"
                log(t, "in_review", user, note="Triaged & prioritized")
            log(t, "note", user, label="Priority", note=f"Set to {p}" if p else "Cleared")

    if "team" in data:
        tm = data["team"] or None
        if tm is not None and tm not in TEAMS:
            return err("Invalid team")
        if tm != t.assigned_team:
            t.assigned_team = tm
            log(t, "note", user, label="Assigned", note=f"Routed to {tm}" if tm else "Unassigned")
            if tm and t.status in ("submitted", "in_review"):
                t.status = "in_progress"
                log(t, "in_progress", user, note=f"{tm} is now working on it")

    if "assignee" in data:
        aid = data["assignee"]
        agent = None
        if aid not in (None, "", 0):
            agent = db.session.get(User, int(aid))
            if not agent or agent.role != "company" or agent.active is False:
                return err("Pick an active teammate.")
        new_id = agent.id if agent else None
        if new_id != t.assignee_id:
            t.assignee_id = new_id
            if agent:
                log(t, "note", user, label="Assignee", note=f"Assigned to {agent.name}" if agent.id != user.id else f"{user.name} took this ticket")
                if not t.assigned_team and agent.team in TEAMS:
                    t.assigned_team = agent.team
                    log(t, "note", user, label="Assigned", note=f"Routed to {agent.team}")
                    if t.status in ("submitted", "in_review"):
                        t.status = "in_progress"
                        log(t, "in_progress", user, note=f"{agent.team} is now working on it")
            else:
                log(t, "note", user, label="Assignee", note="Unassigned")

    if "status" in data:
        s = data["status"]
        if s not in STATUSES:
            return err("Invalid status")
        set_status(t, s, user)

    t.updated_at = utcnow()
    db.session.commit()
    return jsonify(detail(t, user)), 200


# ---------------------------------------------------------------- messages (both sides)
@bp.post("/<code>/messages")
@jwt_required()
@limiter.limit("60 per hour")
def post_message(code):
    user = current_user()
    t = find_ticket_for(user, code) if user else None
    if not t:
        return err("Ticket not found", 404)
    if user.role == "customer" and t.created_by != user.id:
        return err(f"Only {t.customer_name} (who raised this issue) can reply.", 403)
    data = request.get_json(silent=True) or {}
    msg = (data.get("message") or "").strip()[:10000]
    kind = data.get("kind", "reply")

    if user.role == "company":
        if kind == "request_info":
            set_status(t, "awaiting_customer", user)
            if msg:
                log(t, "note", user, label="Asked customer", note=msg)
        else:
            if not msg:
                return err("Write an update first.")
            log(t, "note", user, label="Reply to customer", note=msg)
    else:
        if not msg:
            return err("Write a message first.")
        if t.status == "closed":
            return err("This ticket is closed. Please raise a new issue.")
        log(t, "note", user, label="Customer reply", note=msg)
        if t.status == "awaiting_customer":
            set_status(t, "in_progress" if t.assigned_team else "in_review", user)

    t.updated_at = utcnow()
    db.session.commit()
    return jsonify(detail(t, user)), 200
