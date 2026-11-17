"""Wiring check for the Telegram layer: imports, callback data, keyboards, routers."""

from datetime import datetime
from pathlib import Path

import pytest

pytest.importorskip("aiogram")

from aiogram import Dispatcher

from bot import keyboards as kb
from bot.config import BusinessProvider
from bot.handlers import admin, client

CONFIG = Path(__file__).resolve().parent.parent / "configs" / "barbershop.json"


def test_callback_data_roundtrip():
    packed = kb.SlotCb(index=2, at="202611181500").pack()
    assert len(packed.encode()) <= 64  # Telegram limit
    assert kb.SlotCb.unpack(packed) == kb.SlotCb(index=2, at="202611181500")


def test_keyboards_build():
    biz = BusinessProvider(CONFIG).get()
    now = datetime(2026, 11, 18, 9, 0)
    menu = kb.main_menu(biz)
    assert len(menu.inline_keyboard) == len(biz.services) + 2
    picker = kb.slot_picker(biz, 0, [datetime(2026, 11, 18, 15, 0)], now)
    assert picker.inline_keyboard[0][0].text == "Сегодня 15:00"


def test_routers_attach_to_dispatcher():
    dp = Dispatcher()
    dp.include_router(admin.build_router(admin_id=1))
    dp.include_router(client.router)


def test_admin_reply_filter_finds_tag_mid_text():
    from types import SimpleNamespace

    from aiogram import F

    flt = F.reply_to_message.text.regexp(admin.USER_TAG, mode="search")
    msg = SimpleNamespace(
        reply_to_message=SimpleNamespace(text="❓ Вопрос\n👤 Кирилл #id42\n\nтекст")
    )
    match = flt.resolve(msg)
    assert match and match.group(1) == "42"
