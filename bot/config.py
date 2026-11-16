"""Runtime settings (from env) and business profile (from JSON)."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, time
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent


def load_dotenv(path: Path) -> None:
    """Minimal .env reader: KEY=VALUE lines, real env vars take precedence."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str
    admin_id: int | None
    business_config: Path
    db_path: Path

    @classmethod
    def from_env(cls) -> Settings:
        load_dotenv(ROOT / ".env")
        token = os.getenv("BOT_TOKEN", "").strip()
        if not token:
            raise RuntimeError("BOT_TOKEN is not set, see .env.example")
        admin_id = os.getenv("ADMIN_ID", "").strip()
        return cls(
            bot_token=token,
            admin_id=int(admin_id) if admin_id else None,
            business_config=ROOT / os.getenv("BUSINESS_CONFIG", "configs/barbershop.json"),
            db_path=ROOT / os.getenv("DB_PATH", "data/bookings.db"),
        )


@dataclass(frozen=True, slots=True)
class Service:
    name: str
    price: str
    description: str = ""


@dataclass(frozen=True, slots=True)
class SlotPolicy:
    times: tuple[time, ...]
    days_ahead: int = 3
    days_off: frozenset[int] = frozenset()  # 0 = Monday ... 6 = Sunday
    min_lead_minutes: int = 60
    max_buttons: int = 8

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SlotPolicy:
        times = tuple(sorted(time.fromisoformat(t) for t in data["times"]))
        if not times:
            raise ValueError("slots.times must not be empty")
        return cls(
            times=times,
            days_ahead=int(data.get("days_ahead", 3)),
            days_off=frozenset(int(d) for d in data.get("days_off", [])),
            min_lead_minutes=int(data.get("min_lead_minutes", 60)),
            max_buttons=int(data.get("max_buttons", 8)),
        )


@dataclass(frozen=True, slots=True)
class Business:
    name: str
    address: str
    phone: str
    work_hours: str
    timezone: ZoneInfo
    services: tuple[Service, ...]
    slots: SlotPolicy
    texts: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Business:
        services = tuple(Service(**s) for s in data["services"])
        if not services:
            raise ValueError("services must not be empty")
        return cls(
            name=data["business_name"],
            address=data["address"],
            phone=data["phone"],
            work_hours=data["work_hours_text"],
            timezone=ZoneInfo(data.get("timezone", "Europe/Moscow")),
            services=services,
            slots=SlotPolicy.from_dict(data["slots"]),
            texts=dict(data["texts"]),
        )

    def text(self, key: str, **kwargs: Any) -> str:
        return self.texts[key].format(**kwargs)

    def now(self) -> datetime:
        """Current local time of the business, naive (slots are stored naive)."""
        return datetime.now(self.timezone).replace(tzinfo=None)


class BusinessProvider:
    """Serves the business profile and hot-reloads it when the file changes.

    A broken edit (invalid JSON, missing key) is logged and the last good
    profile keeps working, so a typo never takes the bot down.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._mtime = 0.0
        self._business = self._load()

    def _load(self) -> Business:
        self._mtime = self._path.stat().st_mtime
        return Business.from_dict(json.loads(self._path.read_text(encoding="utf-8")))

    def get(self) -> Business:
        try:
            if self._path.stat().st_mtime != self._mtime:
                self._business = self._load()
                logger.info("Business profile reloaded from %s", self._path)
        except (OSError, ValueError, KeyError, TypeError):
            logger.exception("Failed to reload %s, keeping previous profile", self._path)
        return self._business
