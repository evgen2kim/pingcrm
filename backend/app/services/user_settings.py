"""User settings service — priority settings helpers."""
from __future__ import annotations

from app.models.user import User

DEFAULT_PRIORITY_SETTINGS: dict[str, int] = {"high": 30, "medium": 60, "low": 180}

DEFAULT_SUGGESTION_PREFS: dict = {
    "max_suggestions": 10,
    "include_dormant": True,
    "birthday_reminders": True,
    "pushbullet_enabled": False,
    "preferred_channel": "auto",
    "dormancy_threshold_days": 365,
    "language": "ru",
}


def get_priority_settings(user: User) -> dict:
    """Return priority settings with defaults fallback."""
    if user.priority_settings:
        return {**DEFAULT_PRIORITY_SETTINGS, **user.priority_settings}
    return dict(DEFAULT_PRIORITY_SETTINGS)
