from datetime import datetime, time

import pytest

from bot import slots
from bot.config import SlotPolicy

POLICY = SlotPolicy(
    times=(time(10), time(15), time(18)),
    days_ahead=3,
    days_off=frozenset({6}),  # Sunday
    min_lead_minutes=60,
    max_buttons=8,
)


def test_skips_past_and_too_soon_slots():
    now = datetime(2026, 11, 18, 14, 30)  # Wed; 15:00 is within the 60-min lead
    free = slots.free_slots(POLICY, busy=set(), now=now)
    assert free[0] == datetime(2026, 11, 18, 18, 0)


def test_skips_days_off():
    now = datetime(2026, 11, 21, 9, 0)  # Saturday
    free = slots.free_slots(POLICY, busy=set(), now=now)
    assert all(s.weekday() != 6 for s in free)
    assert datetime(2026, 11, 23, 10, 0) in free  # Monday is offered


def test_skips_busy_slots():
    now = datetime(2026, 11, 18, 8, 0)
    taken = datetime(2026, 11, 18, 10, 0)
    assert taken not in slots.free_slots(POLICY, busy={taken}, now=now)


def test_respects_max_buttons():
    policy = SlotPolicy(times=tuple(time(h) for h in range(8, 20)), max_buttons=4)
    assert len(slots.free_slots(policy, busy=set(), now=datetime(2026, 11, 18, 0, 0))) == 4


@pytest.mark.parametrize(
    ("slot", "expected"),
    [
        (datetime(2026, 11, 18, 15, 0), "Сегодня 15:00"),
        (datetime(2026, 11, 19, 10, 0), "Завтра 10:00"),
        (datetime(2026, 11, 21, 18, 30), "сб 21.11 18:30"),
    ],
)
def test_humanize(slot, expected):
    assert slots.humanize(slot, now=datetime(2026, 11, 18, 9, 0)) == expected


def test_encode_roundtrip_fits_callback_data():
    slot = datetime(2026, 11, 18, 15, 0)
    encoded = slots.encode(slot)
    assert ":" not in encoded  # aiogram's CallbackData separator
    assert slots.decode(encoded) == slot
