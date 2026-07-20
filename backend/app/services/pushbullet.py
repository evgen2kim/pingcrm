"""Pushbullet push-notification service."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_API_URL = "https://api.pushbullet.com/v2/pushes"
_ME_URL = "https://api.pushbullet.com/v2/users/me"

_client: httpx.Client | None = None


def _get_client() -> httpx.Client:
    """Return a shared httpx.Client configured with the Pushbullet API key."""
    global _client
    from app.core.config import settings

    if _client is None or _client.is_closed:
        _client = httpx.Client(
            base_url="https://api.pushbullet.com",
            headers={
                "Access-Token": settings.PUSHBULLET_API_KEY,
                "Content-Type": "application/json",
            },
            timeout=10.0,
        )
    return _client


def send_push(
    title: str,
    body: str,
    url: str | None = None,
) -> bool:
    """Send a push notification via Pushbullet. Returns True on success."""
    from app.core.config import settings

    if not settings.PUSHBULLET_API_KEY:
        logger.warning("Pushbullet API key not configured, skipping push")
        return False

    try:
        client = _get_client()
        data: dict = {"type": "link" if url else "note", "title": title, "body": body}
        if url:
            data["url"] = url

        resp = client.post("/v2/pushes", json=data)
        if resp.status_code == 200:
            logger.info("Pushbullet push sent: %s", title)
            return True
        logger.error("Pushbullet push failed: %s %s", resp.status_code, resp.text[:200])
        return False
    except Exception:
        logger.exception("Pushbullet push request failed")
        return False


def test_connection() -> bool:
    """Verify Pushbullet API key is valid. Returns True on success."""
    from app.core.config import settings

    if not settings.PUSHBULLET_API_KEY:
        logger.warning("Pushbullet API key not configured")
        return False

    try:
        client = _get_client()
        resp = client.get("/v2/users/me")
        if resp.status_code == 200:
            email = resp.json().get("email", "unknown")
            logger.info("Pushbullet connected as: %s", email)
            return True
        logger.error("Pushbullet auth failed: %s", resp.status_code)
        return False
    except Exception:
        logger.exception("Pushbullet connection test failed")
        return False
