"""Demo data for LOCAL testing only. Enabled with SEED_DEMO=true. Never enable in production."""
from datetime import timedelta

from werkzeug.security import generate_password_hash

from extensions import db
from models import Ticket, TicketEvent, User, utcnow


def seed_demo_data():
    if User.query.filter_by(email="customer@acme.com").first():
        return
    now = utcnow()
    H, D = timedelta(hours=1), timedelta(days=1)

    cust = User(email="customer@acme.com", name="Alex Carter", company="Acme Inc.", role="customer",
                password_hash=generate_password_hash("demo1234"))
    agent = User(email="agent@resolvehq.com", name="Jordan Mills", company="ResolveHQ", role="company",
                 team="Support", is_admin=True, password_hash=generate_password_hash("demo1234"))
    db.session.add_all([cust, agent])
    db.session.flush()

    def mk(title, desc, cat, typ, prio, status, team, created, events):
        t = Ticket(ticket_id="TMP", title=title, description=desc, category=cat, issue_type=typ,
                   priority=prio, status=status, assigned_team=team, created_by=cust.id,
                   customer_name=cust.name, customer_email=cust.email, customer_company=cust.company,
                   created_at=created, updated_at=events[-1][1])
        db.session.add(t)
        db.session.flush()
        t.ticket_id = f"TKT-{1000 + t.id}"
        for stage, at, note, label, by in events:
            t.events.append(TicketEvent(stage=stage, created_at=at, note=note, label=label, author_role=by))
        if status in ("resolved", "closed"):
            t.resolved_at = events[-1][1]

    mk("Checkout page throws 500 on card payment",
       "Paying with a Visa card on hosted checkout returns a 500 after clicking Pay.",
       "Product bug", "bug", "P0", "in_progress", "Engineering", now - 2 * D,
       [("submitted", now - 2 * D, "", "", "customer"),
        ("in_review", now - 2 * D + 3 * H, "Triaged as P0 — payment-blocking", "", "company"),
        ("in_progress", now - D, "Payments squad investigating gateway logs", "", "company")])
    mk("Invoice PDF shows wrong tax total",
       "The downloaded invoice PDF lists a tax amount that does not match the dashboard.",
       "Billing", "bug", None, "submitted", None, now - 6 * H,
       [("submitted", now - 6 * H, "", "", "customer")])
    db.session.commit()
