"""Inline keyboards and typed callback data."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot import slots
from bot.config import Business


class Action(StrEnum):
    HOME = "home"
    ASK = "ask"
    CONTACTS = "contacts"


class MenuCb(CallbackData, prefix="m"):
    action: Action


class ServiceCb(CallbackData, prefix="svc"):
    index: int


class SlotCb(CallbackData, prefix="slot"):
    index: int
    at: str  # slots.SLOT_FORMAT


def main_menu(business: Business) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for index, service in enumerate(business.services):
        kb.button(text=service.name, callback_data=ServiceCb(index=index))
    kb.button(text=business.text("btn_ask"), callback_data=MenuCb(action=Action.ASK))
    kb.button(text=business.text("btn_contacts"), callback_data=MenuCb(action=Action.CONTACTS))
    kb.adjust(1)
    return kb.as_markup()


def slot_picker(
    business: Business, service_index: int, free: list[datetime], now: datetime
) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for slot in free:
        kb.button(
            text=slots.humanize(slot, now),
            callback_data=SlotCb(index=service_index, at=slots.encode(slot)),
        )
    kb.adjust(2)
    kb.row(*back(business).inline_keyboard[0])
    return kb.as_markup()


def back(business: Business) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=business.text("btn_back"), callback_data=MenuCb(action=Action.HOME))
    return kb.as_markup()
