"""Celery task: send Pushbullet birthday reminders."""
from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta

from celery import shared_task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import task_session
from app.models.contact import Contact
from app.models.user import User
from app.services.task_jobs.common import _run

logger = logging.getLogger(__name__)

_RU_MONTHS = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]


def _birthday_message(contact: Contact, today_mmdd: str) -> str:
    """Build a Russian-language birthday reminder string."""
    bday = contact.birthday.strip()
    mmdd = bday[-5:]
    name = contact.full_name or "Неизвестный"
    company = f" ({contact.company})" if contact.company else ""

    if mmdd == today_mmdd:
        return f"Сегодня день рождения у {name}{company}!"
    return f"Завтра день рождения у {name}{company}!"


async def _send_birthday_pushes(db: AsyncSession) -> dict:
    """Send Pushbullet notifications for today's and tomorrow's birthdays."""
    from app.services.pushbullet import send_push

    today = datetime.now(UTC).date()
    today_mmdd = today.strftime("%m-%d")
    tomorrow_mmdd = (today + timedelta(days=1)).strftime("%m-%d")
    target_mmdds = {today_mmdd, tomorrow_mmdd}

    result = await db.execute(select(User))
    users = result.scalars().all()

    sent = 0
    skipped = 0
    errors = 0

    for user in users:
        prefs = (user.priority_settings or {}).get("suggestion_prefs", {})
        if not prefs.get("pushbullet_enabled", False):
            skipped += 1
            continue

        contacts_result = await db.execute(
            select(Contact).where(
                Contact.user_id == user.id,
                Contact.birthday.isnot(None),
                Contact.birthday != "",
            )
        )
        contacts = contacts_result.scalars().all()

        for contact in contacts:
            bday = contact.birthday.strip()
            mmdd = bday[-5:]
            if mmdd not in target_mmdds:
                continue

            text = _birthday_message(contact, today_mmdd)
            url = f"/contacts/{contact.id}"

            ok = send_push(title="День рождения", body=text, url=url)
            if ok:
                sent += 1
            else:
                errors += 1

    return {"sent": sent, "skipped_users": skipped, "errors": errors}


@shared_task(name="app.services.tasks.send_birthday_push_notifications")
def send_birthday_push_notifications() -> dict:
    """Daily task: send Pushbullet push notifications for upcoming birthdays.

    Runs at 07:00 UTC. Checks today's and tomorrow's birthdays for all users
    who have ``pushbullet_enabled`` in their suggestion preferences.
    """
    logger.info("send_birthday_push_notifications: starting")

    async def _runner() -> dict:
        async with task_session() as db:
            result = await _send_birthday_pushes(db)
            await db.commit()
            return result

    result = _run(_runner())
    logger.info("send_birthday_push_notifications: %s", result)
    return result
