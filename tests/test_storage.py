from datetime import datetime

import pytest

from bot.storage import Booking, BookingRepository

SLOT = datetime(2026, 11, 18, 15, 0)


@pytest.fixture
def repo():
    repo = BookingRepository(":memory:")
    yield repo
    repo.close()


def make_booking(user_id: int = 1, slot: datetime = SLOT) -> Booking:
    return Booking(user_id, f"user{user_id}", "Стрижка", "1 200 ₽", slot)


def test_book_free_slot(repo):
    assert repo.try_book(make_booking())
    assert repo.busy_slots(since=datetime(2026, 11, 18)) == {SLOT}


def test_double_booking_is_rejected(repo):
    assert repo.try_book(make_booking(user_id=1))
    assert not repo.try_book(make_booking(user_id=2))


def test_upcoming_excludes_past_and_is_sorted(repo):
    repo.try_book(make_booking(slot=datetime(2026, 11, 20, 10, 0)))
    repo.try_book(make_booking(slot=datetime(2026, 11, 19, 10, 0)))
    repo.try_book(make_booking(slot=datetime(2026, 11, 17, 10, 0)))

    upcoming = repo.upcoming(since=datetime(2026, 11, 18))
    assert [b.slot.day for b in upcoming] == [19, 20]
