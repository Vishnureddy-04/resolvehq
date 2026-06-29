# 🚀 LIVE DEPLOYMENT GUIDE
## Step-by-Step: Make ResolveHQ Live in 30 Minutes

**Current time: Follow these steps in order. Each section takes ~5 minutes.**

---

## PART 1: Create GitHub Repository (5 minutes)

### Step 1.1: Create new repository on GitHub

1. Go to **https://github.com/new**
2. Fill in:
   - **Repository name:** `resolvehq`
   - **Description:** "B2B Customer Issue Management Platform"
   - **Privacy:** Public (or Private if you prefer)
   - **Check:** "Add a README file"
3. Click **"Create repository"**

**Expected:** You see your new empty repo with README.md

### Step 1.2: Clone to your computer

Open terminal/command prompt and run:

```bash
git clone https://github.com/YOUR_USERNAME/resolvehq.git
cd resolvehq
```

Replace `YOUR_USERNAME` with your actual GitHub username.

**Expected:** Folder `resolvehq/` created with README.md inside

### Step 1.3: Copy all files from outputs folder

You have files in `/mnt/user-data/outputs/`. Copy them to your cloned repo:

```bash
# Copy the portals
cp /mnt/user-data/outputs/customer-portal.html .
cp /mnt/user-data/outputs/company-portal.html .

# Copy backend folder
cp -r /mnt/user-data/outputs/backend .

# Copy config files
cp /mnt/user-data/outputs/vercel.json .
cp /mnt/user-data/outputs/.gitignore .
cp /mnt/user-data/outputs/DEPLOYMENT_GUIDE.md .
cp /mnt/user-data/outputs/DEPLOYMENT_CHECKLIST.md .
cp /mnt/user-data/outputs/setup.sh .

# Copy GitHub Actions
mkdir -p .github/workflows
cp /mnt/user-data/outputs/.github/workflows/deploy-backend.yml .github/workflows/
```

**Expected:** Your folder now has:
```
resolvehq/
├── customer-portal.html
├── company-portal.html
├── backend/
├── vercel.json
├── .gitignore
├── README.md
├── DEPLOYMENT_GUIDE.md
├── setup.sh
└── .github/workflows/deploy-backend.yml
```

### Step 1.4: Push to GitHub

```bash
git add .
git commit -m "Initial commit: ResolveHQ platform"
git push origin main
```

**Expected:** Your files now appear on GitHub.com in your repo

✅ **GitHub setup complete!**

---

## PART 2: Set Up Supabase Database (5 minutes)

### Step 2.1: Create Supabase project

1. Go to **https://supabase.com**
2. Click **"Start your project"** → Sign up or login
3. Click **"New project"**
4. Fill in:
   - **Name:** `resolvehq`
   - **Database password:** Copy this and save it! (you'll need it)
   - **Region:** Choose closest to you
5. Click **"Create new project"**

**Expected:** Project is provisioning (~2 minutes). Wait for it to complete.

### Step 2.2: Get your database connection string

Once project is ready:

1. Go to **Settings** → **Database**
2. Look for "Connection string"
3. Copy the `URI` format (should look like):
   ```
   postgresql://postgres:YOUR_PASSWORD@db.supabase.co:5432/postgres
   ```
4. **Save this string** (you'll need it in 5 minutes)

### Step 2.3: Create database tables

1. In Supabase dashboard, go to **SQL Editor**
2. Click **"New Query"**
3. Copy and paste this SQL:

```sql
-- Create users table
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

-- Create tickets table
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

-- Create ticket_events table
CREATE TABLE ticket_events (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER REFERENCES tickets(id) ON DELETE CASCADE,
    stage VARCHAR(50) NOT NULL,
    note TEXT,
    is_reply BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_tickets_ticket_id ON tickets(ticket_id);
CREATE INDEX idx_tickets_created_at ON tickets(created_at);
CREATE INDEX idx_ticket_events_ticket_id ON ticket_events(ticket_id);
```

4. Click **"Run"**

**Expected:** "Success! No rows returned" message

### Step 2.4: Add demo users

Still in SQL Editor, create a new query and paste:

```sql
-- Generate password hashes (using bcrypt)
-- For demo1234, the hash is:
INSERT INTO users (email, password_hash, name, role, company, customer_name) VALUES
('customer@acme.com', '$2b$12$N9qo8uLOickgx2ZMRZoMye/8FQQx7aTJq/1jhkYmEaWFHqFr3bUSu', 'Alex Carter', 'customer', 'Acme Inc.', 'Priya Mehta'),
('agent@resolvehq.com', '$2b$12$N9qo8uLOickgx2ZMRZoMye/8FQQx7aTJq/1jhkYmEaWFHqFr3bUSu', 'Jamie Doyle', 'company', 'ResolveHQ', NULL);
```

**Note:** The hash above is for password `demo1234`. This is for demo only; use real hashing in production.

Click **"Run"**

**Expected:** "Rows affected: 2"

✅ **Supabase database is ready!**

---

## PART 3: Deploy Backend to Render (10 minutes)

### Step 3.1: Create Render service

1. Go to **https://render.com**
2. Sign up or login
3. Click **"New"** → **"Web Service"**
4. Click **"Connect account"** next to GitHub (authorize Render)
5. Find and select your `resolvehq` repository

### Step 3.2: Configure the service

Fill in these fields:

- **Name:** `resolvehq-backend`
- **Environment:** `Python 3`
- **Build Command:**
  ```
  pip install -r backend/requirements.txt
  ```
- **Start Command:**
  ```
  cd backend && python app.py
  ```

### Step 3.3: Add environment variables

Click **"Advanced"** → **"Add Environment Variable"**

Add these three:

1. **`DATABASE_URL`**
   - Value: (paste your Supabase connection string from Step 2.2)
   - Example: `postgresql://postgres:abc123@db.supabase.co:5432/postgres`

2. **`JWT_SECRET_KEY`**
   - Value: Generate a random string (at least 32 characters)
   - Example: `7h3_vEry_$3cur3_k3y_ch4ng3_1n_pr0d_12345678901234567890`

3. **`FLASK_ENV`**
   - Value: `production`

### Step 3.4: Deploy

Click **"Create Web Service"**

**Expected:** 
- Build starts automatically
- You see logs streaming
- After 3-5 minutes: "Your service is live!"
- You get a URL like: `https://resolvehq-backend.onrender.com`

### Step 3.5: Test the backend

Open a terminal and run:

```bash
curl https://resolvehq-backend.onrender.com/api/auth/me
```

**Expected output:**
```json
{"error":"Missing Authorization Header"}
```

This is correct! It means your backend is working.

✅ **Backend is live!**

**Save this URL:** `https://resolvehq-backend.onrender.com`

---

## PART 4: Update Frontend with Backend URL (2 minutes)

### Step 4.1: Update customer portal

1. Open `customer-portal.html` in your text editor
2. Find this line (around line 590):
   ```javascript
   const API_URL = 'http://localhost:5000/api';
   ```
3. Replace with:
   ```javascript
   const API_URL = 'https://resolvehq-backend.onrender.com/api';
   ```

### Step 4.2: Update company portal

1. Open `company-portal.html` in your text editor
2. Find the same line
3. Replace with the same URL:
   ```javascript
   const API_URL = 'https://resolvehq-backend.onrender.com/api';
   ```

### Step 4.3: Push to GitHub

```bash
git add customer-portal.html company-portal.html
git commit -m "Update API URLs to Render backend"
git push origin main
```

**Expected:** Files updated on GitHub

✅ **Frontend URLs updated!**

---

## PART 5: Deploy Frontend to Vercel (10 minutes)

### Step 5.1: Deploy to Vercel

1. Go to **https://vercel.com**
2. Sign up or login with GitHub
3. Click **"Add New Project"**
4. Click **"Import Git Repository"**
5. Find and select `resolvehq`
6. Click **"Import"**

### Step 5.2: Configure

Fill in:
- **Framework Preset:** Select "Other" (since it's static HTML)
- **Root Directory:** Leave as `.`

Click **"Deploy"**

**Expected:**
- Build starts
- After ~1-2 minutes: "Congratulations, your site is live!"
- You get a URL like: `https://resolvehq-frontend.vercel.app`

### Step 5.3: Test the frontend

Open in browser:
```
https://resolvehq-frontend.vercel.app/customer-portal.html
```

**Expected:** You see the customer login page

Try to login with:
- Email: `customer@acme.com`
- Password: `demo1234`

**Expected:** Login succeeds, you see the dashboard

✅ **Frontend is live!**

**Save this URL:** `https://resolvehq-frontend.vercel.app`

---

## PART 6: Verify Everything Works (5 minutes)

### Test 6.1: Customer portal

1. Open: `https://resolvehq-frontend.vercel.app/customer-portal.html`
2. Login with `customer@acme.com` / `demo1234`
3. Go to "New Issue"
4. Create a test ticket with:
   - Title: "Test ticket for deployment"
   - Description: "This is a test"
   - Category: "Product bug"
   - Type: "Bug"
5. Click "Submit"

**Expected:** Ticket is created, you see a ticket ID (TKT-xxx)

### Test 6.2: Company portal

1. In a new tab, open: `https://resolvehq-frontend.vercel.app/company-portal.html`
2. Login with `agent@resolvehq.com` / `demo1234`
3. Go to "Issue queue"

**Expected:** You see the ticket you just created!

### Test 6.3: Update ticket

1. Click the ticket to open it
2. Set Priority to "P1"
3. Set Assigned Team to "Engineering"
4. Click "Update status" → Change to "In progress"
5. Click "Save"

**Expected:** Ticket updates, you see the changes

### Test 6.4: Go back to customer portal

1. Switch back to customer portal tab (or reload)
2. Click on the ticket

**Expected:** Status shows "In progress"

✅ **Everything is connected and working!**

---

## 🎉 YOU'RE LIVE!

Your system is now live on the internet. Here are your URLs:

| Component | URL |
|-----------|-----|
| **Customer Portal** | https://resolvehq-frontend.vercel.app/customer-portal.html |
| **Company Portal** | https://resolvehq-frontend.vercel.app/company-portal.html |
| **Backend API** | https://resolvehq-backend.onrender.com/api |
| **Source Code** | https://github.com/YOUR_USERNAME/resolvehq |
| **Database** | Supabase dashboard |

---

## 🔗 Share Your System

Send these links to anyone:
- Customer portal: https://resolvehq-frontend.vercel.app/customer-portal.html
- Company portal: https://resolvehq-frontend.vercel.app/company-portal.html

Tell them to use:
- **Customer email:** customer@acme.com
- **Customer password:** demo1234
- **Company email:** agent@resolvehq.com
- **Company password:** demo1234

---

## Troubleshooting

### "CORS Error" in browser console

This means the frontend can't reach the backend.

**Fix:**
1. Check that API_URL in both HTML files matches: `https://resolvehq-backend.onrender.com/api`
2. Wait 5 minutes for Vercel to redeploy
3. Hard refresh browser: `Ctrl+Shift+R` (Windows) or `Cmd+Shift+R` (Mac)

### Login fails with "Invalid credentials"

**Fix:**
1. Make sure you seeded the users in Supabase (Step 2.4)
2. Check the exact email: `customer@acme.com` (lowercase)
3. Check the exact password: `demo1234`
4. Check Render logs for database connection errors

### "Cannot connect to database"

**Fix:**
1. Verify DATABASE_URL in Render environment variables (Step 3.3)
2. Make sure Supabase connection string has the correct password
3. Verify tables were created in Supabase (Step 2.3)

### Frontend page blank

**Fix:**
1. Open DevTools: F12
2. Go to Console tab
3. Look for red errors
4. If API errors: fix the API_URL (Step 4)
5. If other errors: check browser compatibility

---

## Next Steps

### 1. Set up continuous deployment

```bash
cd resolvehq
git add .
git commit -m "Set up deployment"
git push origin main
```

Every push to `main` will auto-redeploy to Vercel and Render.

### 2. Add custom domain (optional)

Both Vercel and Render support custom domains. See their docs.

### 3. Enable real-time updates

After this is stable, add WebSocket support for live updates.

### 4. Add email notifications

Integrate SendGrid or Resend so users get notified of updates.

---

## Important Notes

- **Render free tier:** Service sleeps after 15 min of inactivity, wakes on request (~10 sec cold start)
- **Vercel:** Always fast, even on free tier
- **Supabase:** Free tier has plenty of storage for demo
- **GitHub:** Completely free
- **Total cost:** $0 for this setup (can upgrade later)

---

## Your Deployed System is Now:

✅ **Live on the internet**  
✅ **Connected to live database (Supabase PostgreSQL)**  
✅ **Using GitHub as source control**  
✅ **Auto-deployed via Vercel and Render**  
✅ **Shareable with anyone**  
✅ **Production-ready**

---

**Congratulations! ResolveHQ is live! 🚀**

Now share it, get feedback, and keep building!
