"""Team sharing: customers with the same *work* email domain see each other's tickets.

Personal / free email providers are never grouped (every gmail.com user is a stranger).
"""
import os

PUBLIC_DOMAINS = {
    "gmail.com", "googlemail.com", "yahoo.com", "yahoo.co.in", "yahoo.co.uk", "ymail.com", "rocketmail.com",
    "outlook.com", "hotmail.com", "hotmail.co.uk", "live.com", "live.in", "msn.com", "windowslive.com",
    "icloud.com", "me.com", "mac.com", "aol.com", "proton.me", "protonmail.com", "pm.me",
    "zoho.com", "zohomail.in", "yandex.com", "yandex.ru", "mail.com", "gmx.com", "gmx.net", "gmx.de",
    "rediffmail.com", "inbox.com", "fastmail.com", "tutanota.com", "hey.com", "qq.com", "163.com",
    "126.com", "naver.com", "web.de", "mail.ru", "duck.com", "mailinator.com",
}
# Extra domains to treat as personal (comma-separated), e.g. your own company's domain
PUBLIC_DOMAINS |= {d.strip().lower() for d in os.getenv("NO_SHARE_DOMAINS", "").split(",") if d.strip()}


def team_domain(email):
    """Return the shareable domain for an email, or None if it must stay private."""
    if not email or "@" not in email:
        return None
    domain = email.rsplit("@", 1)[1].strip().lower()
    if not domain or domain in PUBLIC_DOMAINS:
        return None
    return domain


def same_team(email_a, email_b):
    d = team_domain(email_a)
    return d is not None and d == team_domain(email_b)
