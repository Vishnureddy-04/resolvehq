# ResolveHQ Flask Backend

A complete Flask REST API backend for the ResolveHQ customer-company issue management platform.

## Features

- **User authentication** (JWT) for customers and company agents
- **Ticket management** (CRUD, status updates, prioritization)
- **Team assignment** and workload tracking
- **Customer replies** and communication timeline
- **Analytics & dashboards** with TAT metrics and recurring issue detection
- **SQLAlchemy ORM** with PostgreSQL (or SQLite for demo)
- **CORS enabled** for frontend integration

---

## Quick Start

### 1. Install dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Set environment variables (optional)

Create a `.env` file in the backend directory:

```
DATABASE_URL=sqlite:///resolvehq.db
# For PostgreSQL: postgresql://user:password@localhost/resolvehq
JWT_SECRET_KEY=your-secret-key-here
FLASK_ENV=development
```

If no `.env` is set, the app defaults to SQLite for demo.

### 3. Run the server

```bash
python app.py
```

The API will be available at `http://localhost:5000/api`

Demo data is auto-seeded on first run.

---

## API Endpoints

### Authentication

**POST /api/auth/register**
```json
{
  "email": "user@company.com",
  "password": "password123",
  "name": "John Doe",
  "role": "customer",  // or "company"
  "company": "Acme Inc.",
  "customer_name": "John Doe",
  "team": "Engineering"  // for company users
}
```
Returns: `{ access_token, user }`

**POST /api/auth/login**
```json
{
  "email": "user@company.com",
  "password": "password123"
}
```
Returns: `{ access_token, user }`

**GET /api/auth/me** (requires JWT)
Returns current authenticated user.

---

### Tickets

**POST /api/tickets** (Customer only)
Create a new ticket.
```json
{
  "title": "Checkout page throws 500 error",
  "description": "When paying with card...",
  "category": "Product bug",
  "type": "bug",
  "screenshot_url": "data:image/png;base64,..."  // optional, base64 or URL
}
```
Returns: Created ticket object

**GET /api/tickets** (Requires JWT)
List all tickets (customers see only their own; company sees all).

Query params:
- `status=submitted|in_review|in_progress|awaiting_customer|resolved|closed`
- `priority=P0|P1|P2|P3` (company only)
- `team=Engineering|Implementation|...` (company only)
- `customer=Company Name` (company only)
- `sort=updated|created`

**GET /api/tickets/<ticket_id>** (Requires JWT)
Get ticket details including full event timeline.

**PATCH /api/tickets/<ticket_id>** (Company only)
Update ticket fields.
```json
{
  "priority": "P0",
  "category": "Product bug",
  "type": "bug",
  "assigned_team": "Engineering",
  "status": "in_progress"
}
```

**POST /api/tickets/<ticket_id>/reply** (Company only)
Send a message to customer.
```json
{
  "message": "We're working on this issue...",
  "status": "in_progress"  // optional, update status too
}
```

**POST /api/tickets/<ticket_id>/resolve** (Company only)
Mark ticket as resolved.
```json
{
  "message": "Issue has been fixed in v4.2.1"
}
```

**POST /api/tickets/<ticket_id>/close** (Company only)
Close a resolved ticket.

---

### Analytics

**GET /api/analytics/dashboard** (Requires JWT)
Get role-specific dashboard metrics (totals, recent activity).

**GET /api/analytics/metrics** (Company only)
Detailed metrics with time filtering.

Query params:
- `days=7|30|90|all`

Returns: type/category/priority breakdowns, TAT metrics, closure rate.

**GET /api/analytics/team-workload** (Company only)
Open tickets by assigned team.

**GET /api/analytics/recurring** (Company only)
Detect recurring issues in last 90 days (keyword similarity clustering).

**GET /api/analytics/customer/<customer_company>** (Company only)
Analytics for a specific customer account.

---

## Demo Credentials

Customers:
- Email: `customer@acme.com`
- Password: `demo1234`

Company agents:
- Email: `agent@resolvehq.com`
- Password: `demo1234`

---

## Connecting the Frontend Portals

The frontend portals (customer-portal.html and company-portal.html) need to be updated to call the API instead of using localStorage.

### In the front-end JavaScript, replace these sections:

**Customer portal (customer-portal.html)**

In the form submission (`submitIssue()`):
```javascript
// Before:
tickets.unshift(t); save(tickets);

// After:
const token = localStorage.getItem('access_token');
const res = await fetch('http://localhost:5000/api/tickets', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
  body: JSON.stringify({
    title, description, category, type,
    screenshot_url: pendingShot
  })
});
if (res.ok) {
  const ticket = await res.json();
  openTicket(ticket.id);
}
```

**Company portal (company-portal.html)**

In ticket actions (saveField, saveStatus, sendReply, etc.):
```javascript
// Before:
mutate(state.current.id, t => { t.field = value; });

// After:
const token = localStorage.getItem('access_token');
const res = await fetch(`http://localhost:5000/api/tickets/${state.current.id}`, {
  method: 'PATCH',
  headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
  body: JSON.stringify({ field: value })
});
```

---

## Database Models

### User
- id, email, password_hash, name, role (customer|company)
- company, customer_name, team
- created_at, updated_at

### Ticket
- id, ticket_id (TKT-xxxx), title, description, category, issue_type
- priority (P0-P3), status
- created_by (user_id), assigned_to (user_id), assigned_team
- customer_name, customer_email, customer_company
- screenshot_url
- created_at, updated_at, resolved_at, closed_at

### TicketEvent
- id, ticket_id, stage, note, is_reply, created_at

---

## Switching from SQLite to PostgreSQL (Production)

1. Install PostgreSQL locally or use a hosted service (Heroku, AWS RDS, etc.)
2. Update `.env`:
   ```
   DATABASE_URL=postgresql://user:password@localhost/resolvehq_db
   ```
3. Install psycopg2 (already in requirements.txt)
4. Run `python app.py` — tables are auto-created

---

## Deployment

### Heroku
```bash
heroku create resolvehq-backend
heroku addons:create heroku-postgresql:hobby-dev
heroku config:set JWT_SECRET_KEY=your-secret-key
git push heroku main
```

### AWS / DigitalOcean / Render / Railway
All support Flask apps with PostgreSQL. Set the `DATABASE_URL` and `JWT_SECRET_KEY` environment variables, and push/deploy.

---

## Next Steps

1. Update the frontend portals to call the API
2. Add email notifications (when tickets are created, updated, or resolved)
3. Implement WebSocket/real-time updates for live status tracking
4. Add SLA alerts and breach notifications
5. Build user management (admins create company/customer accounts)
6. Add comment threads on tickets
7. Implement file uploads to S3 for screenshots

---

## Troubleshooting

**"Circular import" errors**
- Make sure `app.py` defines `db` and `jwt` before models are imported

**"No module named 'routes'"**
- Ensure `routes/__init__.py` exists and is in the same directory as app.py

**JWT token errors**
- Check that the `Authorization: Bearer <token>` header is included in requests
- Make sure the JWT_SECRET_KEY in frontend and backend match

**SQLite locking errors in concurrent requests**
- Switch to PostgreSQL for production — SQLite is for demo/testing only
