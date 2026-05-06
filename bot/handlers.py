"""
Обработчики сообщений и callback-ов бота.
"""

import asyncio
from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from google.genai import types as g_types

from bot.config import bot, log
from bot.keyboards import main_keyboard, notifications_keyboard
from bot.reports import get_daily_report, get_plan
from bot.ai_chat import process_ai_message
from bot.scheduler import get_user_settings, update_user_settings

router = Router()


# --- FSM для ввода времени оповещения ---

class NotificationTimeInput(StatesGroup):
    waiting_time = State()


# --- /start ---

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я твой ассистент.\n\n"
        "Используй кнопки внизу или просто напиши/скажи, что нужно сделать.",
        reply_markup=main_keyboard
    )


# --- Reply-кнопки ---

@router.message(F.text == "📊 Отчет")
async def btn_report(message: types.Message):
    log.info(f"[BTN] Отчет от user_id={message.from_user.id}")
    report = await asyncio.to_thread(get_daily_report)
    await message.answer(report)


@router.message(F.text == "📋 План")
async def btn_plan(message: types.Message):
    log.info(f"[BTN] План от user_id={message.from_user.id}")
    plan = await asyncio.to_thread(get_plan)
    await message.answer(plan)


@router.message(F.text == "🔔 Оповещение")
async def btn_notifications(message: types.Message):
    log.info(f"[BTN] Оповещение от user_id={message.from_user.id}")
    settings = get_user_settings(message.from_user.id)
    await message.answer(
        "🔔 *Настройка оповещений*\n\n"
        "Включай/выключай оповещения и настраивай время:",
        reply_markup=notifications_keyboard(settings),
        parse_mode="Markdown"
    )


# --- Inline callback-ы оповещений ---

@router.callback_query(F.data == "notif_toggle_report")
async def toggle_report(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    settings = get_user_settings(user_id)
    settings['daily_report']['enabled'] = not settings['daily_report']['enabled']
    update_user_settings(user_id, settings)

    status = "включен ✅" if settings['daily_report']['enabled'] else "выключен ❌"
    await callback.answer(f"Ежедневный отчет {status}")
    await callback.message.edit_reply_markup(reply_markup=notifications_keyboard(settings))
    await callback.message.answer(f"🔔 Оповещение 'Ежедневный отчет' {status}", reply_markup=main_keyboard)


@router.callback_query(F.data == "notif_toggle_plan")
async def toggle_plan(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    settings = get_user_settings(user_id)
    settings['daily_plan']['enabled'] = not settings['daily_plan']['enabled']
    update_user_settings(user_id, settings)

    status = "включен ✅" if settings['daily_plan']['enabled'] else "выключен ❌"
    await callback.answer(f"Ежедневный план {status}")
    await callback.message.edit_reply_markup(reply_markup=notifications_keyboard(settings))
    await callback.message.answer(f"🔔 Оповещение 'Ежедневный план' {status}", reply_markup=main_keyboard)


@router.callback_query(F.data == "notif_info_report")
async def info_report(callback: types.CallbackQuery):
    settings = get_user_settings(callback.from_user.id)
    r = settings.get('daily_report', {})
    status = "✅ Включен" if r.get('enabled') else "❌ Выключен"
    await callback.answer(
        f"📊 Ежедневный отчет\nВремя: {r.get('hour',0):02d}:{r.get('minute',0):02d}\nСтатус: {status}",
        show_alert=True
    )


@router.callback_query(F.data == "notif_info_plan")
async def info_plan(callback: types.CallbackQuery):
    settings = get_user_settings(callback.from_user.id)
    p = settings.get('daily_plan', {})
    status = "✅ Включен" if p.get('enabled') else "❌ Выключен"
    await callback.answer(
        f"📋 Ежедневный план\nВремя: {p.get('hour',8):02d}:{p.get('minute',0):02d}\nСтатус: {status}",
        show_alert=True
    )


@router.callback_query(F.data == "notif_time_report")
async def ask_time_report(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(NotificationTimeInput.waiting_time)
    await state.update_data(target="daily_report")
    await callback.message.answer(
        "⏰ Введи новое время для *ежедневного отчета* в формате ЧЧ:ММ\n"
        "Например: `00:00` или `23:30`",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "notif_time_plan")
async def ask_time_plan(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(NotificationTimeInput.waiting_time)
    await state.update_data(target="daily_plan")
    await callback.message.answer(
        "⏰ Введи новое время для *ежедневного плана* в формате ЧЧ:ММ\n"
        "Например: `08:00` или `10:30`",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(NotificationTimeInput.waiting_time)
async def process_time_input(message: types.Message, state: FSMContext):
    text = message.text.strip()
    try:
        parts = text.split(':')
        hour = int(parts[0])
        minute = int(parts[1])
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError()
    except (ValueError, IndexError):
        await message.answer("⚠️ Неверный формат. Введи время как ЧЧ:ММ (например: 08:00)")
        return

    data = await state.get_data()
    target = data.get('target', 'daily_report')
    await state.clear()

    user_id = message.from_user.id
    settings = get_user_settings(user_id)
    settings[target]['hour'] = hour
    settings[target]['minute'] = minute
    update_user_settings(user_id, settings)

    name = "отчета" if target == "daily_report" else "плана"
    await message.answer(
        f"✅ Время {name} установлено на {hour:02d}:{minute:02d}",
        reply_markup=main_keyboard
    )

    # Показать обновлённые настройки
    await message.answer(
        "🔔 Обновлённые настройки:",
        reply_markup=notifications_keyboard(settings)
    )


# --- Текст и голос → AI ---

@router.message(F.voice)
async def h_voice(m: types.Message):
    log.info(f"[VOICE] user_id={m.from_user.id}")
    f = await bot.get_file(m.voice.file_id)
    b = await bot.download_file(f.file_path)
    await process_ai_message(
        m, [g_types.Part.from_bytes(data=b.read(), mime_type="audio/ogg"), "Выполни"]
    )


@router.message(F.text)
async def h_text(m: types.Message):
    log.info(f"[TEXT] user_id={m.from_user.id}: {m.text[:80]}")
    await process_ai_message(m, m.text)
