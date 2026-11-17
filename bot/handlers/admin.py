"""Admin tools: answer client questions by reply, list upcoming bookings."""

from __future__ import annotations

import re
from html import escape

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.config import BusinessProvider
from bot.storage import BookingRepository

USER_TAG = re.compile(r"#id(\d+)")


def build_router(admin_id: int) -> Router:
    router = Router(name="admin")
    router.message.filter(F.from_user.id == admin_id)

    @router.message(Command("bookings"))
    async def list_bookings(
        message: Message, business: BusinessProvider, repo: BookingRepository
    ) -> None:
        upcoming = repo.upcoming(since=business.get().now())
        if not upcoming:
            await message.answer("Предстоящих записей нет.")
            return
        lines = [
            f"• {b.slot:%d.%m %H:%M} — {escape(b.service)} ({escape(b.price)}), "
            f"{escape(b.user_name)}"
            for b in upcoming
        ]
        await message.answer("<b>Предстоящие записи:</b>\n" + "\n".join(lines))

    @router.message(F.reply_to_message.text.regexp(USER_TAG, mode="search").as_("tag"), F.text)
    async def reply_to_client(
        message: Message, tag: re.Match[str], bot: Bot, business: BusinessProvider
    ) -> None:
        await bot.send_message(
            int(tag.group(1)),
            business.get().text("admin_answer", text=escape(message.text)),
        )
        await message.answer("✅ Ответ отправлен клиенту.")

    return router
