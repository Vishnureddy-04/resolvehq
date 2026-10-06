"""Serves attachments in local development only (production uses Supabase signed URLs)."""
from flask import Blueprint, abort, send_file

import storage

bp = Blueprint("files", __name__, url_prefix="/api/files")


@bp.get("/<token>")
def serve(token):
    full = storage.load_local(token)
    if not full:
        abort(404)
    return send_file(full, max_age=300)
