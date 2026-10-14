import click
from flask import Flask, jsonify
from flask_cors import CORS
from sqlalchemy import text
from werkzeug.exceptions import HTTPException
from werkzeug.security import generate_password_hash

from config import Config
from extensions import db, jwt, limiter


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)

    db.init_app(app)
    jwt.init_app(app)
    limiter.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
         allow_headers=["Content-Type", "Authorization"],
         methods=["GET", "POST", "PATCH", "OPTIONS"])

    @jwt.user_lookup_loader
    def _load_user(_header, payload):
        from models import User
        return db.session.get(User, int(payload["sub"]))

    @jwt.user_lookup_error_loader
    def _user_gone(_header, _payload):
        return jsonify({"error": "Your account is no longer active. Please sign in again."}), 401

    @jwt.token_verification_loader
    def _still_active(_header, payload):
        from models import User
        u = db.session.get(User, int(payload["sub"]))
        if not u or u.active is False:
            return False
        if u.role == "customer" and (not u.business or u.business.active is False):
            return False                     # business paused: sign everyone out
        return True

    @jwt.token_verification_failed_loader
    def _deactivated(_header, _payload):
        return jsonify({"error": "Your account has been deactivated. Contact your admin."}), 401

    from routes import agents, auth, businesses, files, notifications, push as push_routes, tickets
    app.register_blueprint(auth.bp)
    app.register_blueprint(businesses.bp)
    app.register_blueprint(push_routes.bp)
    app.register_blueprint(notifications.bp)
    app.register_blueprint(agents.bp)
    app.register_blueprint(tickets.bp)
    app.register_blueprint(files.bp)

    _register_errors(app)
    _register_cli(app)

    @app.get("/")
    @app.get("/api/health")
    def health():
        try:
            db.session.execute(text("SELECT 1"))
            database = "ok"
        except Exception:
            database = "unreachable"
        return jsonify({"service": "ResolveHQ API", "status": "ok", "database": database,
                        "storage": "supabase" if app.config["SUPABASE_URL"] and app.config["SUPABASE_SERVICE_KEY"] else "local"})

    with app.app_context():
        import models  # noqa: F401  (register tables)
        # gunicorn starts several workers at once: let only one run the setup at a time
        lock = db.engine.connect() if db.engine.dialect.name == "postgresql" else None
        if lock is not None:
            lock.execute(text("SELECT pg_advisory_lock(724111)"))
        try:
            db.create_all()
            _add_missing_columns()
            _backfill_businesses(app)
            _bootstrap_admin(app)
            try:
                import push
                push.ensure_keys()
            except Exception:
                app.logger.exception("could not prepare push keys")
            if app.config["SEED_DEMO"]:
                from seed_data import seed_demo_data
                seed_demo_data()
        finally:
            db.session.remove()
            if lock is not None:
                lock.execute(text("SELECT pg_advisory_unlock(724111)"))
                lock.close()

    return app


def _register_errors(app):
    @app.errorhandler(413)
    def too_large(_e):
        return jsonify({"error": "Upload too large. Each image must be 5 MB or less (max 5 images)."}), 413

    @app.errorhandler(429)
    def rate_limited(_e):
        return jsonify({"error": "Too many requests. Please wait a few minutes and try again."}), 429

    @app.errorhandler(HTTPException)
    def http_error(e):
        return jsonify({"error": e.description or e.name}), e.code

    @app.errorhandler(Exception)
    def unhandled(e):
        app.logger.exception("Unhandled error")
        return jsonify({"error": "Something went wrong on our side. Please try again."}), 500

    @jwt.unauthorized_loader
    def _missing(_msg):
        return jsonify({"error": "Please sign in."}), 401

    @jwt.invalid_token_loader
    def _invalid(_msg):
        return jsonify({"error": "Your session is invalid. Please sign in again."}), 401

    @jwt.expired_token_loader
    def _expired(_h, _p):
        return jsonify({"error": "Your session expired. Please sign in again."}), 401


def _add_missing_columns():
    """Tiny forward-only migration: add columns introduced after a database was first created."""
    from sqlalchemy import inspect
    insp = inspect(db.engine)
    pg = db.engine.dialect.name == "postgresql"
    true_, false_ = ("TRUE", "FALSE") if pg else ("1", "0")
    wanted = {
        "users": {"is_admin": f"BOOLEAN NOT NULL DEFAULT {false_}",
                  "active": f"BOOLEAN NOT NULL DEFAULT {true_}",
                  "notif_seen_at": "TIMESTAMP",
                  "business_id": "INTEGER REFERENCES businesses(id)",
                  "must_change_password": f"BOOLEAN NOT NULL DEFAULT {false_}",
                  "last_login_at": "TIMESTAMP"},
        "tickets": {"assignee_id": "INTEGER REFERENCES users(id)",
                    "business_id": "INTEGER REFERENCES businesses(id)"},
    }
    with db.engine.begin() as conn:
        for table, cols in wanted.items():
            have = {c["name"] for c in insp.get_columns(table)}
            for col, ddl in cols.items():
                if col not in have:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}"))


def _backfill_businesses(app):
    """One-time move from self-sign-up to business accounts: customers without a business are
    grouped by work-email domain (personal emails get their own), and their tickets follow."""
    from models import Business, Ticket, User
    from orgs import team_domain
    loose = User.query.filter(User.role == "customer", User.business_id.is_(None)).order_by(User.id).all()
    if loose:
        groups = {}
        for u in loose:
            groups.setdefault(team_domain(u.email) or u.email, []).append(u)
        for key, members in groups.items():
            name = (members[0].company or key).strip()[:255] or key
            base, n = name, 2
            while Business.query.filter(db.func.lower(Business.name) == name.lower()).first():
                name = f"{base} ({n})"; n += 1
            b = Business(name=name)
            db.session.add(b)
            db.session.flush()
            for u in members:
                u.business_id = b.id
                u.company = b.name
        db.session.commit()
        app.logger.info("Moved %d customers into business accounts", len(loose))
    orphan = Ticket.query.filter(Ticket.business_id.is_(None)).all()
    if orphan:
        owners = {u.id: u for u in User.query.filter(User.id.in_({t.created_by for t in orphan})).all()}
        for t in orphan:
            o = owners.get(t.created_by)
            if o and o.business_id:
                t.business_id = o.business_id
        db.session.commit()


def _bootstrap_admin(app):
    """Create the first company agent from ADMIN_EMAIL / ADMIN_PASSWORD (Render has no shell on free tier)."""
    from models import User
    email = app.config["ADMIN_EMAIL"].strip().lower()
    pw = app.config["ADMIN_PASSWORD"]
    if not email or not pw:
        return
    existing = User.query.filter_by(email=email).first()
    if existing:
        if existing.role == "company" and not existing.is_admin:
            existing.is_admin = True
            db.session.commit()
        return
    db.session.add(User(email=email, name=app.config["ADMIN_NAME"], role="company",
                        company="ResolveHQ", team="Support", is_admin=True,
                        password_hash=generate_password_hash(pw)))
    try:
        db.session.commit()
        app.logger.info("Created company agent %s", email)
    except Exception:  # another worker created it at the same moment
        db.session.rollback()


def _register_cli(app):
    @app.cli.command("create-agent")
    @click.option("--email", prompt=True)
    @click.option("--name", prompt=True)
    @click.option("--team", default="Support", show_default=True)
    @click.option("--admin", is_flag=True, help="Can add and manage teammates")
    @click.password_option()
    def create_agent(email, name, team, admin, password):
        """Create a company (agent) login for the company console."""
        from models import User
        email = email.strip().lower()
        if User.query.filter_by(email=email).first():
            click.echo("That email already exists.")
            return
        db.session.add(User(email=email, name=name, role="company", company="ResolveHQ",
                            team=team, is_admin=admin, password_hash=generate_password_hash(password)))
        db.session.commit()
        click.echo(f"Agent {email} created.")


app = create_app()

if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG") == "1")
