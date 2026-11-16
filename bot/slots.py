"""Free-slot calculation, independent from Telegram."""

from __future__ import annotations

from collections.abc import Collection
from datetime import datetime, timedelta

from bot.config import SlotPolicy

WEEKDAYS = ("пн", "вт", "ср", "чт", "пт", "сб", "вс")
SLOT_FORMAT = "%Y%m%d%H%M"  # compact and separator-free, safe for callback_data


def free_slots(policy: SlotPolicy, busy: Collection[datetime], now: datetime) -> list[datetime]:
    """Upcoming bookable slots: skips days off, past/too-soon and already taken ones."""
    earliest = now + timedelta(minutes=policy.min_lead_minutes)
    result: list[datetime] = []
    for offset in range(policy.days_ahead):
        day = (now + timedelta(days=offset)).date()
        if day.weekday() in policy.days_off:
            continue
        for t in policy.times:
            slot = datetime.combine(day, t)
            if slot >= earliest and slot not in busy:
                result.append(slot)
                if len(result) == policy.max_buttons:
                    return result
    return result


def humanize(slot: datetime, now: datetime) -> str:
    """'Сегодня 15:00', 'Завтра 10:00' or 'пт 21.11 18:00'."""
    days = (slot.date() - now.date()).days
    if days == 0:
        day = "Сегодня"
    elif days == 1:
        day = "Завтра"
    else:
        day = f"{WEEKDAYS[slot.weekday()]} {slot:%d.%m}"
    return f"{day} {slot:%H:%M}"


def encode(slot: datetime) -> str:
    return slot.strftime(SLOT_FORMAT)


def decode(value: str) -> datetime:
    return datetime.strptime(value, SLOT_FORMAT)
