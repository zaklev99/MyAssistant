"""
Модуль AI-чата: Gemini сессии и обработка сообщений.
"""

import asyncio
import datetime

from google.genai import types as g_types

from bot.config import MODEL_ID, FALLBACK_MODEL_ID, TZ, gemini_client, log
from bot.tools import add_calendar_event, add_google_task
from bot.reports import get_daily_report, get_plan
from bot.keyboards import main_keyboard


# --- Хранилище чатов ---
user_chats: dict[int, object] = {}

# Маппинг функций
FUNC_MAP = {
    "add_calendar_event": add_calendar_event,
    "add_google_task": add_google_task,
    "get_daily_report": get_daily_report,
    "get_plan": get_plan,
}

TOOLS_LIST = [add_calendar_event, add_google_task, get_daily_report, get_plan]


def get_system_instruction():
    now = datetime.datetime.now(TZ)
    return (
        f"Ты ассистент Льва. Часовой пояс UTC+4. Сейчас: {now.strftime('%d.%m.%Y %H:%M')}. "
        "ПРАВИЛА: 1. Удалять нельзя. 2. 'в 6' = 18:00, 'в 6 утра' = 06:00. "
        "КОМАНДЫ: "
        "'отчет' → get_daily_report(). "
        "'отчет ДД.ММ' → get_daily_report(date_str='ДД.ММ'). "
        "'отчет за 7 дней' / 'отчет за неделю' → get_daily_report(days=7) (последние 7 дней). "
        "'план на завтра' → get_plan(). "
        "'план на ДД.ММ' → get_plan(date_str='ДД.ММ'). "
        "'план на неделю' → get_plan(days=7). "
        "НЕ ГОВОРИ, ЧТО НЕ МОЖЕШЬ — вызывай функции."
    )


def _create_chat(model_id: str):
    """Создаёт новую чат-сессию с указанной моделью."""
    return gemini_client.aio.chats.create(
        model=model_id,
        config=g_types.GenerateContentConfig(
            tools=TOOLS_LIST,
            system_instruction=get_system_instruction(),
            automatic_function_calling=g_types.AutomaticFunctionCallingConfig(
                disable=True
            )
        )
    )


def get_or_create_chat(user_id: int):
    """Получает или создаёт чат-сессию с контекстом для пользователя."""
    if user_id not in user_chats:
        user_chats[user_id] = _create_chat(MODEL_ID)
        log.info(f"Создана новая чат-сессия для user_id={user_id}")
    return user_chats[user_id]


async def process_ai_message(message, content):
    """Обрабатывает сообщение через Gemini AI."""
    user_id = message.from_user.id
    chat = get_or_create_chat(user_id)

    try:
        res = await chat.send_message(content)

        responses = []
        if res.candidates and res.candidates[0].content.parts:
            for part in res.candidates[0].content.parts:
                if part.function_call:
                    func_name = part.function_call.name
                    if func_name in FUNC_MAP:
                        out = await asyncio.to_thread(
                            FUNC_MAP[func_name], **part.function_call.args
                        )
                        responses.append(out)
                    else:
                        log.warning(f"Неизвестная функция: {func_name}")
                elif part.text:
                    responses.append(part.text)

        if responses:
            await message.answer("\n\n".join(responses), reply_markup=main_keyboard)
        else:
            await message.answer("🤔 Не получил ответ от модели.", reply_markup=main_keyboard)

    except Exception as e:
        error_str = str(e)
        # Retry с fallback-моделью при 503 (перегрузка)
        if '503' in error_str or 'UNAVAILABLE' in error_str:
            log.warning(f"[AI] Модель недоступна, переключаюсь на {FALLBACK_MODEL_ID}")
            try:
                user_chats[user_id] = _create_chat(FALLBACK_MODEL_ID)
                chat = user_chats[user_id]
                res = await chat.send_message(content)
                responses = []
                if res.candidates and res.candidates[0].content.parts:
                    for part in res.candidates[0].content.parts:
                        if part.function_call:
                            func_name = part.function_call.name
                            if func_name in FUNC_MAP:
                                out = await asyncio.to_thread(
                                    FUNC_MAP[func_name], **part.function_call.args
                                )
                                responses.append(out)
                        elif part.text:
                            responses.append(part.text)
                if responses:
                    await message.answer("\n\n".join(responses), reply_markup=main_keyboard)
                    return
            except Exception as retry_err:
                log.error(f"[AI] Fallback тоже упал: {retry_err}")

        log.error(f"Ошибка от user_id={user_id}: {e}", exc_info=True)
        user_chats.pop(user_id, None)
        await message.answer(f"⚠️ Ошибка: {error_str[:200]}", reply_markup=main_keyboard)
