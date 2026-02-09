"""Shared utility helpers for the API."""

import re
from pathlib import Path


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal and unsafe characters."""
    safe = Path(filename).name
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", safe)
    safe = safe.strip("._")
    return safe or "upload.pdf"
