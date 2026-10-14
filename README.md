# ResolveHQ

B2B issue tracking. Your clients report problems with a description and screenshots, and your team triages and replies until the issue is resolved.

| Part | File / folder | Who uses it |
|---|---|---|
| Customer portal | `customer-portal.html` | Your client's users (added by your team): report issues with up to 5 images, follow progress, reply |
| Company console | `company-portal.html` | Your team: client business accounts and their users, queue, priority, assignment, status, replies, insights |
| API | `backend/` (Flask) | Both portals, through `config.js` |

**Stack:** static HTML/JS on Vercel · Flask + SQLAlchemy on Render · Supabase Postgres + Storage.

## Quick start (local)

```bash
cd backend && python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt && cp .env.example .env
python app.py                       # http://localhost:5000/api/health
# new terminal, repo root:
python3 -m http.server 8000         # http://localhost:8000/customer-portal.html
```

Create a company-console login with `cd backend && flask --app app create-agent --admin`, then add a client under **Clients** to get a customer login.

**Deploying:** see **[GO_LIVE.md](./GO_LIVE.md)**.

## API

| Method | Path | Who |
|---|---|---|
| POST | `/api/auth/register` | disabled (403): customer logins are created under business accounts |
| POST | `/api/auth/login` | anyone (`role` = `customer` or `company`) |
| GET | `/api/auth/me` | signed in |
| GET | `/api/tickets` | customer: everything raised by their business · company: all |
| POST | `/api/tickets` | customer: multipart form `title, description, category, type, files[]` (≤5 images, ≤5 MB each) |
| GET | `/api/tickets/<id>` | ticket with signed image URLs |
| POST | `/api/tickets/<id>/attachments` | customer adds images (5 total max) |
| PATCH | `/api/tickets/<id>` | company: `priority`, `team`, `assignee`, `status` |
| POST | `/api/tickets/<id>/messages` | company: `{kind: reply or request_info, message}` · customer: `{message}` |
| POST | `/api/auth/password` | signed in: `{current, new}` |
| GET | `/api/agents` | company: list teammates + open assigned counts |
| POST | `/api/agents` | company admin: add teammate `{name, email, team, isAdmin}` → returns `tempPassword` |
| PATCH | `/api/agents/<id>` | company admin: `{team, isAdmin, active, resetPassword}` |
| GET/POST | `/api/businesses` | company: list (with open/urgent/total and user counts) · create `{name, contactEmail, phone, notes}` |
| GET/PATCH | `/api/businesses/<id>` | company: details + `people` · update `{name, contactEmail, phone, notes}`; `active` (pause) is admin only |
| POST | `/api/businesses/<id>/users` | company: add a portal user `{name, email}` → returns `tempPassword` |
| PATCH | `/api/businesses/<id>/users/<uid>` | company: `{name, active, resetPassword}` |
| GET | `/api/health` | health check (database + storage mode) |

## Backend layout

```
backend/
  app.py          app factory, CORS, errors, agent bootstrap, `create-agent` CLI
  config.py       all settings from environment variables
  extensions.py   db, jwt, rate limiter
  models.py       Business, User, Ticket, TicketEvent, Attachment, push models
  orgs.py         email-domain helper (only used to group old self-sign-up customers)
  storage.py      Supabase Storage (prod) or local disk (dev), with signed URLs
  routes/         auth.py, businesses.py, tickets.py, agents.py, notifications.py, push.py, files.py
  seed_data.py    demo data (SEED_DEMO=true, local only)
```
