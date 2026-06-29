# 🚀 Deployment Checklist

Follow this checklist to deploy ResolveHQ live in 30 minutes.

---

## ✅ Pre-Deployment (Setup accounts - 5 minutes)

- [ ] Create GitHub account (github.com)
- [ ] Create Supabase account (supabase.com)
- [ ] Create Vercel account (vercel.com)
- [ ] Create Render account (render.com)

---

## ✅ Step 1: GitHub Repository (5 minutes)

- [ ] Create new GitHub repository named `resolvehq`
- [ ] Clone repository locally
- [ ] Copy all project files to repository folder
- [ ] Run: `git add .`
- [ ] Run: `git commit -m "Initial commit"`
- [ ] Run: `git push origin main`
- [ ] Verify files appear on GitHub.com

---

## ✅ Step 2: Supabase Database Setup (5 minutes)

- [ ] Create Supabase project named `resolvehq`
- [ ] Wait for project to provision (~2 minutes)
- [ ] Go to Settings → Database → Copy Connection String
- [ ] Save connection string (looks like: `postgresql://...`)
- [ ] Go to SQL Editor → Run the SQL schema (from DEPLOYMENT_GUIDE.md)
- [ ] Verify tables created: users, tickets, ticket_events
- [ ] Seed demo data (users table at minimum)

**Supabase Connection String:**
```
postgresql://postgres:YOUR_PASSWORD@db.supabase.co:5432/postgres
```

---

## ✅ Step 3: Deploy Backend to Render (10 minutes)

- [ ] Go to render.com/dashboard
- [ ] Click "New Web Service"
- [ ] Connect GitHub (authorize if needed)
- [ ] Select `resolvehq` repository
- [ ] Set name: `resolvehq-backend`
- [ ] Set environment: `Python 3`
- [ ] Set build command: `pip install -r backend/requirements.txt`
- [ ] Set start command: `cd backend && python app.py`
- [ ] Click Advanced → Add environment variables:
  - [ ] `DATABASE_URL` = (Supabase connection string)
  - [ ] `JWT_SECRET_KEY` = (random long string)
  - [ ] `FLASK_ENV` = `production`
- [ ] Click "Create Web Service"
- [ ] Wait for build to complete (~3-5 minutes)
- [ ] Get service URL (looks like: `https://resolvehq-backend.onrender.com`)
- [ ] Test backend: 
  ```bash
  curl https://resolvehq-backend.onrender.com/api/auth/me
  ```
  (Should return error about missing auth header - that's correct!)

**Render Backend URL:**
```
https://resolvehq-backend.onrender.com/api
```

---

## ✅ Step 4: Update Frontend API URLs (2 minutes)

- [ ] Edit `customer-portal.html` → Find `const API_URL`
- [ ] Replace with: `const API_URL = 'https://resolvehq-backend.onrender.com/api'`
- [ ] Edit `company-portal.html` → Find `const API_URL`
- [ ] Replace with: `const API_URL = 'https://resolvehq-backend.onrender.com/api'`
- [ ] Run: `git add customer-portal.html company-portal.html`
- [ ] Run: `git commit -m "Update API URLs to Render backend"`
- [ ] Run: `git push origin main`

---

## ✅ Step 5: Deploy Frontend to Vercel (10 minutes)

- [ ] Go to vercel.com/dashboard
- [ ] Click "Add New" → "Project"
- [ ] Click "Import Git Repository"
- [ ] Select `resolvehq` repository
- [ ] Set project name: `resolvehq-frontend`
- [ ] Set framework: Select "Other" (static HTML)
- [ ] Set root directory: `.`
- [ ] Add environment variable (optional):
  - [ ] `NEXT_PUBLIC_API_URL` = `https://resolvehq-backend.onrender.com/api`
- [ ] Click "Deploy"
- [ ] Wait for deployment (~2-3 minutes)
- [ ] Get Vercel URL (looks like: `https://resolvehq-frontend.vercel.app`)
- [ ] Click "Visit" to test deployment

**Vercel Frontend URL:**
```
https://resolvehq-frontend.vercel.app
```

---

## ✅ Step 6: Test Live System (5 minutes)

- [ ] Open customer portal: `https://resolvehq-frontend.vercel.app/customer-portal.html`
- [ ] Open developer console (F12)
- [ ] Try login with `customer@acme.com` / `demo1234`
- [ ] Verify no CORS errors in console
- [ ] Verify login succeeds
- [ ] Create a test ticket
- [ ] Watch the request in Network tab
- [ ] Verify ticket appears in database (Supabase SQL Editor)
- [ ] Switch to company portal: `https://resolvehq-frontend.vercel.app/company-portal.html`
- [ ] Login with `agent@resolvehq.com` / `demo1234`
- [ ] Verify customer's ticket appears in queue

---

## ✅ Step 7: Update CORS Settings (2 minutes)

- [ ] Edit `backend/app.py` → Find CORS section
- [ ] Add Vercel domain to origins:
  ```python
  "origins": ["https://resolvehq-frontend.vercel.app", ...]
  ```
- [ ] Run: `git add backend/app.py`
- [ ] Run: `git commit -m "Update CORS for Vercel domain"`
- [ ] Run: `git push origin main`
- [ ] Wait for Render to auto-deploy (~1-2 minutes)
- [ ] Verify deployment in Render logs

---

## ✅ Step 8: Configure Auto-Deployment (Optional, 3 minutes)

- [ ] Go to GitHub Settings → Secrets and variables → Actions
- [ ] Add secret `RENDER_API_KEY` (from Render account settings)
- [ ] Add secret `RENDER_SERVICE_ID` (from your service URL)
- [ ] Now pushes to `main` auto-deploy backend

---

## ✅ Verification Checklist

Test all critical paths:

- [ ] Customer can login
- [ ] Customer can create ticket
- [ ] Ticket appears in database
- [ ] Company can login
- [ ] Company sees customer's ticket
- [ ] Company can update priority
- [ ] Company can assign team
- [ ] Company can update status
- [ ] Customer sees status update
- [ ] Analytics dashboard loads
- [ ] No console errors in browser
- [ ] No errors in Render logs
- [ ] CORS errors resolved

---

## 🎉 You're Live!

| Component | URL |
|-----------|-----|
| **Customer Portal** | https://resolvehq-frontend.vercel.app/customer-portal.html |
| **Company Portal** | https://resolvehq-frontend.vercel.app/company-portal.html |
| **Backend API** | https://resolvehq-backend.onrender.com/api |
| **Database** | Supabase dashboard |
| **Source Code** | https://github.com/YOUR_USERNAME/resolvehq |

---

## Troubleshooting

### "CORS Error" in browser console
- ✅ Update CORS in backend/app.py with Vercel domain
- ✅ Push to GitHub and wait for Render to redeploy

### "Cannot POST /api/tickets" (404)
- ✅ Check API_URL is correct in HTML
- ✅ Verify backend is running (Render logs)
- ✅ Test backend directly: curl https://resolvehq-backend.onrender.com/api/auth/me

### Login fails
- ✅ Verify demo users exist in database (Supabase SQL Editor)
- ✅ Check DATABASE_URL in Render environment variables
- ✅ View Render logs for Python errors

### Page loads but no API calls work
- ✅ Open DevTools → Network tab
- ✅ See which requests are failing
- ✅ Check API_URL matches your actual backend URL
- ✅ Test with curl from terminal

---

## Next Steps After Deployment

1. **Share the links!** Send to friends, colleagues, investors
2. **Add email notifications** (SendGrid or Resend)
3. **Set up custom domain** (both Vercel and Render support)
4. **Enable monitoring** (Render has built-in monitoring)
5. **Back up database** (Supabase auto-backs up)
6. **Test with real users** and gather feedback

---

## Important Notes

- **Render free tier:** Service goes to sleep after 15 minutes of inactivity but wakes on request
- **Vercel:** Frontend is static, always fast and free
- **Supabase:** Free tier includes 500MB storage and good performance
- **Total cost:** ~$0 for demo, $5-20/month for production with traffic

---

**Time to deployment: 30 minutes** ⏱️

Start the checklist above and you'll be live soon! 🚀
