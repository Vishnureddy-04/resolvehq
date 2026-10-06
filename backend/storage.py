"""Attachment storage.

- Production: Supabase Storage (private bucket). The API hands out short-lived signed URLs.
- Local dev:  files on disk under UPLOAD_DIR, served by /api/files/<token> with a signed,
              expiring token (same behaviour as Supabase signed URLs).
"""
import os
import uuid

import requests
from flask import current_app, url_for
from itsdangerous import URLSafeTimedSerializer

ALLOWED = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
}


def sniff_image_type(head: bytes):
    """Identify the real file type from its first bytes (don't trust the browser's label)."""
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    return None


def _use_supabase():
    c = current_app.config
    return bool(c["SUPABASE_URL"] and c["SUPABASE_SERVICE_KEY"])


def _sb_headers(extra=None):
    key = current_app.config["SUPABASE_SERVICE_KEY"]
    h = {"apikey": key}
    # Legacy service_role keys are JWTs and also go in Authorization.
    # New secret keys (sb_secret_...) are sent in the apikey header only.
    if key.startswith("eyJ"):
        h["Authorization"] = f"Bearer {key}"
    if extra:
        h.update(extra)
    return h


def new_path(ticket_code: str, content_type: str):
    return f"tickets/{ticket_code}/{uuid.uuid4().hex}.{ALLOWED[content_type]}"


def save(path: str, data: bytes, content_type: str):
    if _use_supabase():
        c = current_app.config
        r = requests.post(
            f"{c['SUPABASE_URL']}/storage/v1/object/{c['SUPABASE_BUCKET']}/{path}",
            headers=_sb_headers({"Content-Type": content_type, "x-upsert": "false"}),
            data=data,
            timeout=30,
        )
        if r.status_code >= 300:
            raise RuntimeError(f"Supabase upload failed ({r.status_code}): {r.text[:200]}")
        return
    full = os.path.join(current_app.config["UPLOAD_DIR"], path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "wb") as f:
        f.write(data)


def delete(paths):
    if not paths:
        return
    try:
        if _use_supabase():
            c = current_app.config
            requests.delete(
                f"{c['SUPABASE_URL']}/storage/v1/object/{c['SUPABASE_BUCKET']}",
                headers=_sb_headers({"Content-Type": "application/json"}),
                json={"prefixes": list(paths)},
                timeout=30,
            )
        else:
            for p in paths:
                full = os.path.join(current_app.config["UPLOAD_DIR"], p)
                if os.path.exists(full):
                    os.remove(full)
    except Exception:  # best-effort cleanup
        current_app.logger.exception("attachment cleanup failed")


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="attachment")


def signed_urls(attachments):
    """Return {attachment.id: url} valid for SIGNED_URL_SECONDS."""
    attachments = list(attachments)
    if not attachments:
        return {}
    c = current_app.config
    if _use_supabase():
        r = requests.post(
            f"{c['SUPABASE_URL']}/storage/v1/object/sign/{c['SUPABASE_BUCKET']}",
            headers=_sb_headers({"Content-Type": "application/json"}),
            json={"expiresIn": c["SIGNED_URL_SECONDS"], "paths": [a.storage_path for a in attachments]},
            timeout=15,
        )
        out = {}
        if r.status_code < 300:
            by_path = {}
            for item in r.json():
                if item.get("signedURL"):
                    by_path[item.get("path")] = f"{c['SUPABASE_URL']}/storage/v1{item['signedURL']}"
            for a in attachments:
                out[a.id] = by_path.get(a.storage_path)
        else:
            current_app.logger.error("Supabase sign failed %s %s", r.status_code, r.text[:200])
        return out
    s = _serializer()
    return {a.id: url_for("files.serve", token=s.dumps(a.storage_path), _external=True) for a in attachments}


def load_local(token):
    """Validate a local-dev file token -> (absolute path) or None."""
    try:
        path = _serializer().loads(token, max_age=current_app.config["SIGNED_URL_SECONDS"])
    except Exception:
        return None
    root = os.path.abspath(current_app.config["UPLOAD_DIR"])
    full = os.path.abspath(os.path.join(root, path))
    if not full.startswith(root + os.sep) or not os.path.exists(full):
        return None
    return full
