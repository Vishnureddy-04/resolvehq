"""Team alerts outside the console: posts customer activity to a Slack channel.

Set SLACK_WEBHOOK_URL (Slack → Apps → Incoming Webhooks) and CONSOLE_URL
(e.g. https://resolvehq.vercel.app/company-portal). Sending happens in a background
thread so customers never wait for Slack, and a Slack outage never breaks the portal.
"""
import threading

import requests
from flask import current_app

import push

TYPE_LABEL = {"bug": "Urgent fix", "enhancement": "Feature change", "support": "Support issue"}


def _post(url, payload, logger):
    try:
        r = requests.post(url, json=payload, timeout=8)
        if r.status_code >= 300:
            logger.warning("Slack alert failed: %s %s", r.status_code, r.text[:200])
    except Exception as e:  # never let alerts break the request
        logger.warning("Slack alert error: %s", e)


def _send(text, blocks):
    url = current_app.config.get("SLACK_WEBHOOK_URL")
    if not url:
        return
    logger = current_app.logger
    threading.Thread(target=_post, args=(url, {"text": text, "blocks": blocks}, logger), daemon=True).start()


def _push(payload):
    try:
        push.send(payload)
    except Exception:
        current_app.logger.exception("push alert failed")


def _link(ticket_code):
    base = (current_app.config.get("CONSOLE_URL") or "").rstrip("/")
    return f"{base}#{ticket_code}" if base else ""


def _clip(s, n=300):
    s = (s or "").strip().replace("\r", "")
    return s if len(s) <= n else s[: n - 1] + "…"


def new_ticket(t, image_count=0):
    urgent = t.issue_type == "bug"
    head = ("🚨 *URGENT issue*" if urgent else "🆕 *New request*") + f" from *{t.customer_company}*"
    link = _link(t.ticket_id)
    title = f"<{link}|{t.ticket_id} · {t.title}>" if link else f"{t.ticket_id} · {t.title}"
    facts = [
        f"*Raised by:* {t.customer_name} ({t.customer_email})",
        f"*Type:* {TYPE_LABEL.get(t.issue_type, t.issue_type)}",
        f"*Category:* {t.category}",
        f"*Priority:* {t.priority or 'Not set'}",
    ]
    if image_count:
        facts.append(f"*Screenshots:* {image_count}")
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": f"{head}\n{title}"}},
        {"type": "section", "fields": [{"type": "mrkdwn", "text": f} for f in facts]},
        {"type": "section", "text": {"type": "mrkdwn", "text": "> " + _clip(t.description).replace("\n", "\n> ")}},
    ]
    if link:
        blocks.append({"type": "actions", "elements": [{"type": "button", "text": {"type": "plain_text", "text": "Open in console"},
                                                         "url": link, **({"style": "danger"} if urgent else {})}]})
    plain = f"{'URGENT issue' if urgent else 'New request'} from {t.customer_company}: {t.ticket_id} {t.title}"
    _send(plain, blocks)
    _push({
        "title": f"{'🚨 URGENT issue' if urgent else '🆕 New request'} · {t.customer_company}",
        "body": f"{t.ticket_id} · {t.title}\nRaised by {t.customer_name} · {t.category}",
        "url": f"/company-portal#{t.ticket_id}",
        "tag": f"rhq-{t.ticket_id}",
        "urgent": urgent,
    })


def customer_reply(t, author_name, message):
    link = _link(t.ticket_id)
    title = f"<{link}|{t.ticket_id} · {t.title}>" if link else f"{t.ticket_id} · {t.title}"
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn",
                                      "text": f"💬 *{author_name}* ({t.customer_company}) replied on {title}\n> " + _clip(message, 400).replace("\n", "\n> ")}},
    ]
    _send(f"{author_name} replied on {t.ticket_id}: {_clip(message, 120)}", blocks)
    _push({
        "title": f"💬 {author_name} · {t.customer_company} replied",
        "body": f"{t.ticket_id} · {_clip(message, 140)}",
        "url": f"/company-portal#{t.ticket_id}",
        "tag": f"rhq-{t.ticket_id}-reply",
        "urgent": False,
    })
