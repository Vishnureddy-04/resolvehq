# Frontend-Backend Integration Guide

This guide shows how to modify the customer and company portal JavaScript to call the Flask backend API instead of using localStorage.

---

## Global Setup

Add this to the top of both portals (inside the `<script>` tag):

```javascript
/* ---- API Configuration ---- */
const API_URL = 'http://localhost:5000/api';  // Change to your backend URL
let authToken = localStorage.getItem('auth_token');

async function apiCall(endpoint, method='GET', body=null) {
  const opts = {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(authToken && { 'Authorization': `Bearer ${authToken}` }),
    },
  };
  if (body) opts.body = JSON.stringify(body);
  
  const res = await fetch(`${API_URL}${endpoint}`, opts);
  if (res.status === 401) {
    // Token expired, redirect to login
    window.location.href = 'customer-portal.html';
    return null;
  }
  if (!res.ok) {
    const err = await res.json();
    toast((err.error || 'API error'));
    return null;
  }
  return await res.json();
}
```

---

## Customer Portal Integration

### 1. Login

Replace the login submit handler:

```javascript
// BEFORE (in customer-portal.html):
document.getElementById('loginForm').addEventListener('submit', async e=>{
  e.preventDefault();
  // ... validation ...
  const ok = await fakeSignIn(email, password);
  if(ok){ showApp(); return; }
  // ...
});

// AFTER:
document.getElementById('loginForm').addEventListener('submit', async e=>{
  e.preventDefault();
  // ... validation ...
  
  const btn = document.getElementById('submitBtn'), txt = document.getElementById('submitTxt');
  btn.classList.add('loading'); btn.disabled = true; txt.textContent = 'Signing in…';
  
  const data = await apiCall('/auth/login', 'POST', { email, password });
  
  btn.classList.remove('loading'); btn.disabled = false; txt.textContent = 'Sign in';
  
  if (data) {
    authToken = data.access_token;
    localStorage.setItem('auth_token', authToken);
    localStorage.removeItem('auth_token_expires');
    showApp();
  } else {
    document.getElementById('emailErr').textContent = 'Sign-in failed. Check email/password.';
    setInvalid('emailField', true);
  }
});
```

### 2. Submit Issue (Create Ticket)

Replace the `submitIssue()` function:

```javascript
// BEFORE:
function submitIssue(){
  // ... validation ...
  const type=document.querySelector('input[name=ftype]:checked').value;
  const id='TKT-'+(++_seq);
  const ts=now2();
  const t={ id, title, desc, category, type, priority:null, /* ... */ };
  tickets.unshift(t); save(tickets);
  toast('Issue '+id+' submitted');
  openTicket(id);
}

// AFTER:
async function submitIssue(){
  // ... validation (same as before) ...
  const type = document.querySelector('input[name=ftype]:checked').value;
  
  const payload = {
    title: document.getElementById('f-title').value.trim(),
    description: document.getElementById('f-desc').value.trim(),
    category: document.getElementById('f-cat').value,
    type: type,
    screenshot_url: pendingShot,  // base64 or URL
  };
  
  const result = await apiCall('/tickets', 'POST', payload);
  
  if (result) {
    toast('Issue ' + result.id + ' submitted');
    // Fetch fresh ticket data and open it
    const ticket = await apiCall(`/tickets/${result.id}`);
    if (ticket) {
      state.current = ticket;
      state.view = 'dashboard';
      render();
      window.scrollTo(0, 0);
    }
  }
}
```

### 3. Load Tickets

Replace the `load()` function call:

```javascript
// BEFORE:
let tickets = load();  // from localStorage

// AFTER:
let tickets = [];

async function loadTickets() {
  const result = await apiCall('/tickets');
  if (result) {
    tickets = result;
  }
}

// Call on app init:
// (after showApp(), in the render() function)
await loadTickets();
```

### 4. View Ticket Detail

Update `openTicket()`:

```javascript
// BEFORE:
function openTicket(id){ 
  state.current = tickets.find(t=>t.id===id); 
  render(); 
}

// AFTER:
async function openTicket(id) {
  const ticket = await apiCall(`/tickets/${id}`);
  if (ticket) {
    state.current = ticket;
    render();
    window.scrollTo(0, 0);
  }
}
```

### 5. Dashboard Stats

Update `counts()` function:

```javascript
// BEFORE:
function counts(){
  const c={total:tickets.length, open:0, ...};
  tickets.forEach(t=>{ c[STATUS[t.status].group]++; });
  // ...
}

// AFTER:
async function getDashboard() {
  const dashboard = await apiCall('/analytics/dashboard');
  if (dashboard) {
    return {
      total: dashboard.total,
      open: dashboard.open,
      pending: dashboard.pending,
      closed: dashboard.closed,
      avg: dashboard.avg_resolution_hours ? 
        fmtDur(dashboard.avg_resolution_hours) : '—',
      recent: dashboard.recent,
    };
  }
  return null;
}

// Use in viewDashboard():
async function viewDashboard() {
  const c = await getDashboard();
  if (!c) return '<div class="empty">Loading dashboard...</div>';
  // ... render with c.total, c.open, etc
}
```

---

## Company Portal Integration

### 1. Login

Same as customer (see above).

### 2. Load Tickets for Queue

Replace `load()`:

```javascript
// BEFORE:
let tickets = load();  // from localStorage

// AFTER:
let tickets = [];

async function loadTickets(filter='all') {
  let endpoint = '/tickets';
  if (filter !== 'all') {
    endpoint += `?status=${filter}`;
  }
  const result = await apiCall(endpoint);
  if (result) {
    tickets = result;
  }
}

// Call on app init:
await loadTickets();
```

### 3. Update Ticket (Priority, Team, Status)

Replace `saveField()`:

```javascript
// BEFORE:
function saveField(field, val){
  if(val===undefined){ toast('Nothing selected.'); return; }
  mutate(state.current.id, t=>{ t[field]=val||null; });
  toast('Saved — '+field+' updated.');
}

// AFTER:
async function saveField(field, val) {
  if (!val && val !== null) { toast('Nothing selected.'); return; }
  
  const payload = { [field]: val };
  const result = await apiCall(`/tickets/${state.current.id}`, 'PATCH', payload);
  
  if (result) {
    state.current = result;
    render();
    toast('Saved — ' + field + ' updated.');
  }
}
```

### 4. Send Reply to Customer

Replace `sendReply()`:

```javascript
// BEFORE:
function sendReply(resolve){
  const msg=$('#det-reply').value.trim();
  if(!msg){ toast('Please write a message first.'); return; }
  mutate(state.current.id, t=>{
    t.events.push(ev('in_progress', Date.now(), msg, true));
  });
  toast('Reply sent to customer.');
}

// AFTER:
async function sendReply(resolve) {
  const msg = document.getElementById('det-reply').value.trim();
  if (!msg) { toast('Please write a message first.'); return; }
  
  const payload = { message: msg };
  const result = await apiCall(`/tickets/${state.current.id}/reply`, 'POST', payload);
  
  if (result) {
    state.current = result;
    document.getElementById('det-reply').value = '';
    render();
    toast('Reply sent to customer.');
  }
}
```

### 5. Mark Resolved

Replace `markResolved()`:

```javascript
// BEFORE:
function markResolved(){
  const msg=$('#det-reply').value.trim()||'Your issue has been resolved...';
  mutate(state.current.id, t=>{
    t.status='resolved'; t.resolvedAt=t.resolvedAt||Date.now();
    t.events.push(ev('resolved', Date.now(), msg, true));
  });
  toast('Marked as resolved — customer notified.');
}

// AFTER:
async function markResolved() {
  const msg = document.getElementById('det-reply').value.trim() || 
    'Your issue has been resolved. Please confirm if everything looks good.';
  
  const result = await apiCall(`/tickets/${state.current.id}/resolve`, 'POST', { message: msg });
  
  if (result) {
    state.current = result;
    document.getElementById('det-reply').value = '';
    render();
    toast('Marked as resolved — customer notified.');
  }
}
```

### 6. Analytics Dashboard

Replace `viewAnalytics()`:

```javascript
// BEFORE:
function viewAnalytics(){
  // Uses local ticket list and calculations
  // ...
}

// AFTER:
async function viewAnalytics() {
  const r = state.range;
  const metrics = await apiCall(`/analytics/metrics?days=${r}`);
  const recurring = await apiCall('/analytics/recurring');
  const workload = await apiCall('/analytics/team-workload');
  
  if (!metrics || !recurring) return '<div class="empty">Loading analytics...</div>';
  
  // Build HTML using metrics data
  return `<div>...your analytics HTML using metrics object...</div>`;
}
```

### 7. Get Dashboard

Replace `dashCounts()`:

```javascript
// BEFORE:
function dashCounts(){
  const c={total:tickets.length, open:0, ...};
  tickets.forEach(t=>{ /* count */ });
  return c;
}

// AFTER:
async function getDashboard() {
  return await apiCall('/analytics/dashboard');
}

// Use in viewDashboard():
async function viewDashboard() {
  const c = await getDashboard();
  if (!c) return '<div class="empty">Loading dashboard...</div>';
  // ... render with c.total, c.open, c.p0_active, etc
}
```

---

## Session Management

Add logout functionality:

```javascript
function showLogin() {
  authToken = null;
  localStorage.removeItem('auth_token');
  // ... show login screen (existing code)
}

// Check on app load:
async function initApp() {
  if (!authToken) {
    // Show login screen
    document.getElementById('loginScreen').style.display = '';
    return;
  }
  
  // Verify token is still valid
  const user = await apiCall('/auth/me');
  if (!user) {
    // Token expired
    showLogin();
    return;
  }
  
  // Load data and show app
  await loadTickets();
  showApp();
}

// Call on page load:
initApp();
```

---

## Error Handling

Wrap API calls with try-catch for network errors:

```javascript
async function apiCall(endpoint, method='GET', body=null) {
  try {
    const opts = {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...(authToken && { 'Authorization': `Bearer ${authToken}` }),
      },
    };
    if (body) opts.body = JSON.stringify(body);
    
    const res = await fetch(`${API_URL}${endpoint}`, opts);
    
    if (res.status === 401) {
      showLogin();
      return null;
    }
    
    if (!res.ok) {
      const err = await res.json();
      toast(err.error || `Error: ${res.status}`);
      return null;
    }
    
    return await res.json();
  } catch (e) {
    toast('Network error: ' + e.message);
    console.error(e);
    return null;
  }
}
```

---

## CORS Configuration

Make sure your Flask backend allows requests from your frontend origin.

In `app.py`:
```python
CORS(app, resources={
  r"/api/*": {
    "origins": ["http://localhost:3000", "http://localhost:5173", "https://yourdomain.com"],
    "methods": ["GET", "POST", "PATCH", "OPTIONS"],
    "allow_headers": ["Content-Type", "Authorization"]
  }
})
```

---

## Testing

1. Start the backend: `python app.py`
2. Open the portal in browser
3. Sign in with demo credentials
4. Check browser DevTools Console for any fetch errors
5. Verify tickets are loading from `/api/tickets`
6. Test creating, updating, and resolving tickets

---

## Deployment Checklist

- [ ] Update `API_URL` to production backend URL
- [ ] Set `JWT_SECRET_KEY` in backend to a strong random value
- [ ] Switch database to PostgreSQL
- [ ] Enable HTTPS (SSL/TLS)
- [ ] Set up CORS for production domain
- [ ] Test authentication and ticket operations
- [ ] Set up monitoring and error logging
- [ ] Add email notifications for ticket updates
