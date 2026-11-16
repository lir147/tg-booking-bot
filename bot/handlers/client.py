"""Client-facing flow: menu -> service -> time slot -> booking, plus questions."""

from __future__ import annotations

import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, User

from bot import keyboards as kb
from bot import slots
from bot.config import Business, BusinessProvider, Settings
from bot.storage import Booking, BookingRepository

router = Router(name="client")
logger = logging.getLogger(__name__)


class AskQuestion(StatesGroup):
    waiting_text = State()


def display_name(user: User) -> str:
    return f"{user.full_name} (@{user.username})" if user.username else user.full_name


def user_tag(user: User) -> str:
    """Marker the admin reply handler uses to route an answer back."""
    return f"#id{user.id}"


async def notify_admin(bot: Bot, settings: Settings, text: str) -> None:
    if settings.admin_id is None:
        return
    try:
        await bot.send_message(settings.admin_id, text)
    except Exception:  # admin hasn't started the bot, blocked it, etc.
        logger.exception("Could not notify admin %s", settings.admin_id)


def greeting(business: Business, user: User) -> str:
    return business.text("greeting", name=escape(user.first_name), business=business.name)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, business: BusinessProvider) -> None:
    await state.clear()
    biz = business.get()
    await message.answer(greeting(biz, message.from_user), reply_markup=kb.main_menu(biz))


@router.callback_query(kb.MenuCb.filter(F.action == kb.Action.HOME))
async def show_home(cb: CallbackQuery, state: FSMContext, business: BusinessProvider) -> None:
    await state.clear()
    biz = business.get()
    await cb.message.edit_text(greeting(biz, cb.from_user), reply_markup=kb.main_menu(biz))
    await cb.answer()


@router.callback_query(kb.MenuCb.filter(F.action == kb.Action.CONTACTS))
async def show_contacts(cb: CallbackQuery, business: BusinessProvider) -> None:
    biz = business.get()
    await cb.message.edit_text(
        biz.text("contacts", address=biz.address, phone=biz.phone, hours=biz.work_hours),
        reply_markup=kb.back(biz),
    )
    await cb.answer()


async def render_service(
    cb: CallbackQuery, biz: Business, index: int, repo: BookingRepository
) -> None:
    service = biz.services[index]
    now = biz.now()
    free = slots.free_slots(biz.slots, repo.busy_slots(since=now), now)

    text = biz.text(
        "service_card",
        service=service.name,
        price=service.price,
        description=service.description,
    )
    if free:
        text += "\n\n" + biz.text("choose_time")
    else:
        text += "\n\n" + biz.text("no_slots", phone=biz.phone)
    await cb.message.edit_text(text, reply_markup=kb.slot_picker(biz, index, free, now))


@router.callback_query(kb.ServiceCb.filter())
async def show_service(
    cb: CallbackQuery,
    callback_data: kb.ServiceCb,
    business: BusinessProvider,
    repo: BookingRepository,
) -> None:
    biz = business.get()
    if callback_data.index >= len(biz.services):  # menu changed since the message was sent
        await cb.answer(biz.text("outdated"), show_alert=True)
        return
    await render_service(cb, biz, callback_data.index, repo)
    await cb.answer()


@router.callback_query(kb.SlotCb.filter())
async def book_slot(
    cb: CallbackQuery,
    callback_data: kb.SlotCb,
    bot: Bot,
    business: BusinessProvider,
    repo: BookingRepository,
    settings: Settings,
) -> None:
    biz = business.get()
    if callback_data.index >= len(biz.services):
        await cb.answer(biz.text("outdated"), show_alert=True)
        return

    service = biz.services[callback_data.index]
    slot = slots.decode(callback_data.at)
    now = biz.now()
    booking = Booking(
        cb.from_user.id, display_name(cb.from_user), service.name, service.price, slot
    )

    if slot < now or not repo.try_book(booking):
        await cb.answer(biz.text("slot_taken"), show_alert=True)
        await render_service(cb, biz, callback_data.index, repo)
        return

    when = slots.humanize(slot, now)
    await cb.message.edit_text(
        biz.text(
            "booked",
            service=service.name,
            price=service.price,
            slot=when,
            address=biz.address,
            phone=biz.phone,
        ),
        reply_markup=kb.back(biz),
    )
    await cb.answer("✅")
    await notify_admin(
        bot,
        settings,
        f"🆕 <b>Новая запись</b>\n"
        f"{escape(service.name)} — {escape(service.price)}\n"
        f"🗓 {when} ({slot:%d.%m %H:%M})\n"
        f"👤 {escape(booking.user_name)} {user_tag(cb.from_user)}",
    )


@router.callback_query(kb.MenuCb.filter(F.action == kb.Action.ASK))
async def ask_question(cb: CallbackQuery, state: FSMContext, business: BusinessProvider) -> None:
    biz = business.get()
    await state.set_state(AskQuestion.waiting_text)
    await cb.message.edit_text(biz.text("ask_prompt"), reply_markup=kb.back(biz))
    await cb.answer()


@router.message(AskQuestion.waiting_text, F.text)
async def receive_question(
    message: Message,
    state: FSMContext,
    bot: Bot,
    business: BusinessProvider,
    settings: Settings,
) -> None:
    biz = business.get()
    await state.clear()
    await message.answer(biz.text("ask_thanks"), reply_markup=kb.main_menu(biz))
    await notify_admin(
        bot,
        settings,
        f"❓ <b>Вопрос от клиента</b>\n"
        f"👤 {escape(display_name(message.from_user))} {user_tag(message.from_user)}\n\n"
        f"{escape(message.text)}\n\n"
        f"<i>Ответьте реплаем на это сообщение — ответ уйдёт клиенту.</i>",
    )


@router.message()
async def fallback(message: Message, business: BusinessProvider) -> None:
    biz = business.get()
    await message.answer(biz.text("fallback"), reply_markup=kb.main_menu(biz))
