# ResolveHQ demo (sample data)

Clickable demo of the customer portal and company console. No backend: both portals share one
demo database kept in the viewer's own browser, so issues raised in the customer portal appear in
the company console. "Reset demo" restores the sample data. Safe to share.

Deploy (from this folder):

    npx vercel login
    npx vercel --prod

Links after deploy:
- https://<project>.vercel.app/                  (landing page with demo logins)
- https://<project>.vercel.app/customer-portal
- https://<project>.vercel.app/company-portal
