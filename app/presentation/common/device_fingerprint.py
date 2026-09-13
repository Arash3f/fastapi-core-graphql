import hashlib

from starlette.requests import Request


def get_device_fingerprint(request: Request) -> str:
    """SHA-256 fingerprint from User-Agent (matches nest-core-clean device binding)."""
    raw = request.headers.get("user-agent") or "unknown"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
