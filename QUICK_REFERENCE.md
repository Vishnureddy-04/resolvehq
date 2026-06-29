# 📋 QUICK REFERENCE CARD
## Everything You Need to Deploy ResolveHQ Live

Keep this open while you deploy. Copy-paste the commands as you go.

---

## 🔐 Demo Credentials

```
CUSTOMER LOGIN:
  Email:    customer@acme.com
  Password: demo1234

COMPANY LOGIN:
  Email:    agent@resolvehq.com
  Password: demo1234
```

---

## 📝 GitHub Commands

### Create repo (on GitHub website)
1. Go to https://github.com/new
2. Name: `resolvehq`
3. Click Create

### Clone and push (in terminal)
```bash
git clone https://github.com/YOUR_USERNAME/resolvehq.git
cd resolvehq

# Copy files from outputs
cp /mnt/user-data/outputs/customer-portal.html .
cp /mnt/user-data/outputs/company-portal.html .
cp -r /mnt/user-data/outputs/backend .
cp /mnt/user-data/outputs/vercel.json .
cp /mnt/user-data/outputs/.gitignore .
mkdir -p .github/workflows
cp /mnt/user-data/outputs/.github/workflows/deploy-backend.yml .github/workflows/

# Push to GitHub
git add .
git commit -m "Initial commit: ResolveHQ"
git push origin main
```

---

## 🗄️ Supabase Setup

### Website steps
1. Go to https://supabase.com
2. Create new project named `resolvehq`
3. Save the password (you'll need it)
4. Wait for project to provision

### Get connection string
Settings → Database → Copy URI format:
```
postgresql://postgres:PASSWORD@db.supabase.co:5432/postgres
```

### Create tables
SQL Editor → New Query → Paste this:
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    company VARCHAR(255),
    customer_name VARCHAR(255),
    team VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE tickets (
    id SERIAL PRIMARY KEY,
    ticket_id VARCHAR(50) UNIQUE NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(100) NOT NULL,
    issue_type VARCHAR(50) NOT NULL,
    priority VARCHAR(10),
    status VARCHAR(50) DEFAULT 'submitted',
    created_by INTEGER REFERENCES users(id),
    assigned_to INTEGER REFERENCES users(id),
    assigned_team VARCHAR(100),
    customer_name VARCHAR(255) NOT NULL,
    customer_email VARCHAR(255) NOT NULL,
    customer_company VARCHAR(255) NOT NULL,
    screenshot_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    closed_at TIMESTAMP
);

CREATE TABLE ticket_events (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER REFERENCES tickets(id) ON DELETE CASCADE,
    stage VARCHAR(50) NOT NULL,
    note TEXT,
    is_reply BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_tickets_ticket_id ON tickets(ticket_id);
CREATE INDEX idx_tickets_created_at ON tickets(created_at);
CREATE INDEX idx_ticket_events_ticket_id ON ticket_events(ticket_id);
```

### Seed demo users
SQL Editor → New Query → Paste:
```sql
INSERT INTO users (email, password_hash, name, role, company, customer_name) VALUES
('customer@acme.com', '$2b$12$N9qo8uLOickgx2ZMRZoMye/8FQQx7aTJq/1jhkYmEaWFHqFr3bUSu', 'Alex Carter', 'customer', 'Acme Inc.', 'Priya Mehta'),
('agent@resolvehq.com', '$2b$12$N9qo8uLOickgx2ZMRZoMye/8FQQx7aTJq/1jhkYmEaWFHqFr3bUSu', 'Jamie Doyle', 'company', 'ResolveHQ', NULL);
```

---

## 🚀 Render Deployment

### Website steps
1. Go to https://render.com
2. New → Web Service
3. Connect GitHub (authorize)
4. Select `resolvehq` repo

### Configuration
Fill in these fields:
```
Name:           resolvehq-backend
Environment:    Python 3
Build Command:  pip install -r backend/requirements.txt
Start Command:  cd backend && python app.py
```

### Environment Variables (Advanced)
```
DATABASE_URL = postgresql://postgres:PASSWORD@db.supabase.co:5432/postgres
JWT_SECRET_KEY = your-super-secret-random-string-at-least-32-chars
FLASK_ENV = production
```

### Test after deployment
```bash
curl https://resolvehq-backend.onrender.com/api/auth/me
```

Expected: `{"error":"Missing Authorization Header"}`

---

## 🌐 Vercel Deployment

### Update HTML files first
In both `customer-portal.html` and `company-portal.html`, find:
```javascript
const API_URL = 'http://localhost:5000/api';
```

Replace with:
```javascript
const API_URL = 'https://resolvehq-backend.onrender.com/api';
```

Push to GitHub:
```bash
git add customer-portal.html company-portal.html
git commit -m "Update API URLs"
git push origin main
```

### Website steps
1. Go to https://vercel.com
2. Add New → Project
3. Import Git Repository
4. Select `resolvehq`
5. Framework: Other
6. Deploy

---

## ✅ Testing Checklist

After everything is deployed:

```
[ ] Customer portal loads: https://resolvehq-frontend.vercel.app/customer-portal.html
[ ] Can login as customer@acme.com / demo1234
[ ] Can create a ticket
[ ] Company portal loads: https://resolvehq-frontend.vercel.app/company-portal.html
[ ] Can login as agent@resolvehq.com / demo1234
[ ] Can see customer's ticket in queue
[ ] Can update priority
[ ] Can assign to team
[ ] Can change status
[ ] Ticket updates reflect in database
```

---

## 🔗 Your Live URLs

Once deployed, bookmark these:

```
Customer Portal:
https://resolvehq-frontend.vercel.app/customer-portal.html

Company Portal:
https://resolvehq-frontend.vercel.app/company-portal.html

Backend API:
https://resolvehq-backend.onrender.com/api

Source Code:
https://github.com/YOUR_USERNAME/resolvehq

Database:
https://supabase.com (dashboard)
```

---

## 🆘 Common Issues & Fixes

### CORS Error in console
→ Make sure API_URL in HTML matches backend URL
→ Wait 5 minutes for Vercel to redeploy
→ Hard refresh: Ctrl+Shift+R

### Login fails
→ Check demo users exist in Supabase
→ Check DATABASE_URL is correct in Render
→ View Render logs for errors

### API returns 404
→ Verify backend is running (check Render logs)
→ Verify API_URL is correct in HTML
→ Test with: curl https://resolvehq-backend.onrender.com/api/auth/me

### Database connection error
→ Copy correct Supabase connection string
→ Paste into Render environment variables
→ Make sure password is included

### Frontend blank page
→ Open DevTools (F12)
→ Go to Console tab
→ Check for red errors
→ Fix based on error message

---

## 📞 Support

If something goes wrong:

1. **Check the logs:**
   - Render logs: Dashboard → Your service → Logs
   - Supabase logs: Dashboard → SQL Editor → Run query
   - Browser console: F12 → Console tab

2. **Read error message carefully** — it usually tells you what's wrong

3. **Verify all URLs match:**
   - HTML API_URL should match Render backend URL
   - Database URL should be Supabase connection string
   - CORS should allow Vercel domain

4. **Wait for redeployment:**
   - Render: 2-3 minutes after code push
   - Vercel: 1-2 minutes after code push

---

## ⏱️ Estimated Times

| Step | Time |
|------|------|
| GitHub setup | 5 min |
| Supabase setup | 5 min |
| Render deployment | 10 min |
| Vercel deployment | 10 min |
| Testing | 5 min |
| **Total** | **~35 min** |

---

## 🎉 Success Criteria

You're done when:
✅ Can log in on both portals  
✅ Can create ticket as customer  
✅ Can see ticket as company  
✅ Can update ticket status  
✅ No console errors  
✅ No API errors  
✅ System works on live URLs  

---

**Print or bookmark this card while deploying! 📌**
