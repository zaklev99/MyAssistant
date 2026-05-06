"""
Клавиатуры бота: reply-кнопки и inline-кнопки для оповещений.
"""

from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)


# --- Постоянная reply-клавиатура ---

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="📊 Отчет"),
            KeyboardButton(text="📋 План"),
            KeyboardButton(text="🔔 Оповещение"),
        ]
    ],
    resize_keyboard=True,
    is_persistent=True,
    input_field_placeholder="Введите команду или голосовое..."
)


# --- Inline-клавиатуры для оповещений ---

def notifications_keyboard(settings: dict) -> InlineKeyboardMarkup:
    """
    Генерирует inline-клавиатуру для настройки оповещений.
    settings: {"daily_report": {"enabled": bool, "hour": int, "minute": int},
               "daily_plan": {"enabled": bool, "hour": int, "minute": int}}
    """
    report = settings.get('daily_report', {})
    plan = settings.get('daily_plan', {})

    r_enabled = report.get('enabled', False)
    r_hour = report.get('hour', 0)
    r_min = report.get('minute', 0)
    r_status = "✅" if r_enabled else "❌"

    p_enabled = plan.get('enabled', False)
    p_hour = plan.get('hour', 8)
    p_min = plan.get('minute', 0)
    p_status = "✅" if p_enabled else "❌"

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=f"📊 Отчет — {r_hour:02d}:{r_min:02d}",
                callback_data="notif_info_report"
            ),
            InlineKeyboardButton(
                text=f"{r_status} Вкл/Выкл",
                callback_data="notif_toggle_report"
            ),
        ],
        [
            InlineKeyboardButton(
                text=f"📋 План — {p_hour:02d}:{p_min:02d}",
                callback_data="notif_info_plan"
            ),
            InlineKeyboardButton(
                text=f"{p_status} Вкл/Выкл",
                callback_data="notif_toggle_plan"
            ),
        ],
        [
            InlineKeyboardButton(
                text="⏰ Изменить время отчета",
                callback_data="notif_time_report"
            ),
        ],
        [
            InlineKeyboardButton(
                text="⏰ Изменить время плана",
                callback_data="notif_time_plan"
            ),
        ],
    ])
