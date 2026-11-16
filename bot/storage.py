"""SQLite persistence for bookings.

A single master is assumed, so a slot can be booked once: the UNIQUE
constraint makes double booking impossible even under concurrent clicks.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS bookings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    user_name   TEXT    NOT NULL,
    service     TEXT    NOT NULL,
    price       TEXT    NOT NULL,
    slot        TEXT    NOT NULL UNIQUE,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_bookings_user ON bookings (user_id);
"""


@dataclass(frozen=True, slots=True)
class Booking:
    user_id: int
    user_name: str
    service: str
    price: str
    slot: datetime


class BookingRepository:
    def __init__(self, path: Path | str) -> None:
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        # The bot runs in a single event-loop thread; queries are tiny.
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.executescript(SCHEMA)

    def close(self) -> None:
        self._db.close()

    def try_book(self, booking: Booking) -> bool:
        """Persist the booking. Returns False if the slot is already taken."""
        try:
            with self._db:
                self._db.execute(
                    "INSERT INTO bookings (user_id, user_name, service, price, slot)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (
                        booking.user_id,
                        booking.user_name,
                        booking.service,
                        booking.price,
                        booking.slot.isoformat(timespec="minutes"),
                    ),
                )
        except sqlite3.IntegrityError:
            return False
        return True

    def busy_slots(self, since: datetime) -> set[datetime]:
        rows = self._db.execute(
            "SELECT slot FROM bookings WHERE slot >= ?",
            (since.isoformat(timespec="minutes"),),
        )
        return {datetime.fromisoformat(slot) for (slot,) in rows}

    def upcoming(self, since: datetime) -> list[Booking]:
        rows = self._db.execute(
            "SELECT user_id, user_name, service, price, slot FROM bookings"
            " WHERE slot >= ? ORDER BY slot",
            (since.isoformat(timespec="minutes"),),
        )
        return [
            Booking(user_id, user_name, service, price, datetime.fromisoformat(slot))
            for user_id, user_name, service, price, slot in rows
        ]
