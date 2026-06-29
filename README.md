# ResolveHQ 🎯

A complete B2B customer issue management platform where customers report problems and companies track resolution in real-time.

**Live Demo:** https://resolvehq-frontend.vercel.app/customer-portal.html

---

## Features

### Customer Portal
- Submit issues with title, description, category, type, and screenshots
- Track ticket progress with live status updates
- View open/closed issues and analytics
- Real-time notifications when company replies

### Company Console
- View all customer issues in a unified queue
- Set priority (P0/P1/P2/P3) and assign to teams
- Update status and send replies to customers
- Analytics dashboard with TAT metrics and recurring issues
- Team workload view

### Backend API
- Full REST API with JWT authentication
- Ticket CRUD operations
- Event timeline for audit trail
- Analytics with time-range filtering
- Supabase PostgreSQL database
- CORS enabled for frontend integration

---

## Quick Start (Local Development)

### Prerequisites
- Python 3.11+
- Git
- Supabase account (free tier)

### Setup

```bash
# 1. Clone repository
git clone https://github.com/YOUR_USERNAME/resolvehq.git
cd resolvehq

# 2. Run setup script
bash setup.sh

# 3. Configure Supabase
# Edit backend/.env with your Supabase connection string:
# DATABASE_URL=postgresql://postgres:PASSWORD@db.supabase.co:5432/postgres

# 4. Start backend
cd backend
source venv/bin/activate
python app.py

# 5. Open frontend in another terminal
# Option A: Direct file (limited features)
open customer-portal.html

# Option B: Local server (recommended)
cd ..
python3 -m http.server 8000
# Then open http://localhost:8000/customer-portal.html
```

**Demo Credentials:**
- Customer: `customer@acme.com` / `demo1234`
- Company: `agent@resolvehq.com` / `demo1234`

---

## Deployment

### Production (GitHub + Supabase + Vercel + Render)

**See [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) for complete step-by-step instructions.**

**Quick summary:**
1. Push code to GitHub
2. Set up Supabase PostgreSQL database
3. Deploy backend to Render
4. Deploy frontends to Vercel
5. Configure API URLs and CORS

**Estimated time: 30 minutes**

---

## Project Structure

```
resolvehq/
├── customer-portal.html       # Customer frontend (merged login + app)
├── company-portal.html        # Company frontend (merged login + app)
├── backend/                   # Flask REST API
│   ├── app.py                # Flask app setup
│   ├── models.py             # SQLAlchemy models
│   ├── seed_data.py          # Demo data
│   ├── requirements.txt       # Python dependencies
│   ├── .env.example          # Environment variables template
│   └── routes/
│       ├── auth.py           # Login, register
│       ├── tickets.py        # Ticket CRUD operations
│       └── analytics.py      # Dashboards and metrics
├── .github/
│   └── workflows/
│       └── deploy-backend.yml # GitHub Actions CI/CD
├── vercel.json               # Vercel deployment config
├── .gitignore                # Git ignore rules
└── DEPLOYMENT_GUIDE.md       # Full deployment instructions
```

---

## Technology Stack

### Frontend
- **HTML5 / CSS3 / Vanilla JavaScript**
- **Responsive design** (mobile, tablet, desktop)
- **No build tools needed** (works directly in browser)

### Backend
- **Flask** — Lightweight Python web framework
- **SQLAlchemy** — ORM for database
- **Flask-JWT-Extended** — JWT authentication
- **Flask-CORS** — Cross-origin requests

### Database
- **Supabase PostgreSQL** — Fully managed database
- **Auto-scaling** and **backups included**

### Hosting
- **Vercel** — Static frontend hosting
- **Render** — Backend API hosting
- **GitHub** — Source control and CI/CD

---

## API Endpoints

### Authentication
```
POST   /api/auth/register          # Create new user
POST   /api/auth/login             # Login, get JWT
GET    /api/auth/me                # Current user
```

### Tickets
```
POST   /api/tickets                # Create ticket (customer)
GET    /api/tickets                # List tickets
GET    /api/tickets/<id>           # Get ticket detail
PATCH  /api/tickets/<id>           # Update ticket (company)
POST   /api/tickets/<id>/reply     # Send message (company)
POST   /api/tickets/<id>/resolve   # Mark resolved (company)
POST   /api/tickets/<id>/close     # Close ticket (company)
```

### Analytics
```
GET    /api/analytics/dashboard    # Dashboard metrics
GET    /api/analytics/metrics      # Detailed metrics
GET    /api/analytics/team-workload # Team assignments
GET    /api/analytics/recurring    # Recurring issues
```

**[Full API docs in backend/README.md](./backend/README.md)**

---

## Environment Variables

### Backend (.env)
```
DATABASE_URL=postgresql://...       # Supabase connection
JWT_SECRET_KEY=your-secret-key      # JWT signing key
FLASK_ENV=production                # Environment
CORS_ORIGINS=https://...            # Allowed domains
```

### Frontend (hardcoded in HTML)
```javascript
const API_URL = 'https://api.example.com/api';  // Update this
```

---

## Features Coming Next

- [ ] Email notifications (SendGrid/Resend)
- [ ] Real-time updates (WebSocket)
- [ ] S3 file uploads for screenshots
- [ ] SLA tracking and breach alerts
- [ ] User management UI
- [ ] Comment threads on tickets
- [ ] Advanced search and filtering
- [ ] Mobile app (React Native)

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/awesome`)
3. Make changes
4. Push to GitHub
5. Open a Pull Request

---

## Support

- **Documentation:** See [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)
- **Backend docs:** See [backend/README.md](./backend/README.md)
- **Frontend integration:** See [backend/FRONTEND_INTEGRATION.md](./backend/FRONTEND_INTEGRATION.md)
- **Issues:** GitHub Issues tab

---

## License

MIT License — See LICENSE file

---

## Deployment Status

| Component | Status | URL |
|-----------|--------|-----|
| Frontend | ✅ Live | https://resolvehq-frontend.vercel.app |
| Backend | ✅ Live | https://resolvehq-backend.onrender.com |
| Database | ✅ Live | Supabase PostgreSQL |

---

## Getting Help

1. **Local issues?** See [backend/README.md](./backend/README.md) → Troubleshooting
2. **Deployment issues?** See [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) → Troubleshooting
3. **API questions?** Check [backend/README.md](./backend/README.md) → API Endpoints

---

Built with ❤️ using Flask, React, and PostgreSQL.
