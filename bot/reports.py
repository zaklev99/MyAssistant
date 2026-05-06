"""
Модуль отчётов и планов.
Использует google_api для данных и formatter для красивого вывода.
"""

import datetime
from bot.config import TZ
from bot.google_api import get_all_tasks, get_events_for_range
from bot.formatter import (
    build_day_data, format_single_day_report, format_multi_day_report,
    format_single_day_plan, format_multi_day_plan, DayItem
)


def _parse_date(date_str: str | None, default: datetime.date) -> datetime.date | str:
    """Парсит дату из строки ДД.ММ или ДД.ММ.ГГГГ. Возвращает date или сообщение об ошибке."""
    if not date_str:
        return default

    now = datetime.datetime.now(TZ)
    try:
        parts = date_str.strip().split('.')
        if len(parts) == 2:
            return datetime.datetime.strptime(f"{date_str}.{now.year}", '%d.%m.%Y').date()
        else:
            return datetime.datetime.strptime(date_str, '%d.%m.%Y').date()
    except ValueError:
        return f"⚠️ Неверный формат даты: {date_str}. Используй ДД.ММ или ДД.ММ.ГГГГ"


def get_daily_report(date_str: str = None, days: int = 1):
    """Формирует отчет. date_str: ДД.ММ или ДД.ММ.ГГГГ. days: кол-во дней (макс 30)."""
    now = datetime.datetime.now(TZ)
    start = _parse_date(date_str, now.date())
    if isinstance(start, str):
        return start  # Ошибка парсинга

    days = max(1, min(days, 30))
    end = start + datetime.timedelta(days=days - 1)
    next_day_date = end + datetime.timedelta(days=1)

    events = get_events_for_range(start, next_day_date)
    tasks = get_all_tasks()

    if days == 1:
        day = build_day_data(start, events, tasks)

        is_today = (start == now.date())
        if is_today:
            target_iso = start.isoformat()
            for t in tasks:
                if t.get('status') == 'completed':
                    continue
                due = t.get('due')
                # Включаем бессрочные и просроченные задачи
                if not due or due[:10] < target_iso[:10]:
                    day.pending.append(DayItem(t['title']))
            day.sort()

        return format_single_day_report(day)
    else:
        day_list = []
        for i in range(days):
            d = start + datetime.timedelta(days=i)
            day_list.append(build_day_data(d, events, tasks))
        return format_multi_day_report(day_list)


def get_plan(date_str: str = None, days: int = 1):
    """Формирует план. date_str: ДД.ММ или ДД.ММ.ГГГГ (по умолчанию завтра). days: кол-во дней."""
    now = datetime.datetime.now(TZ)
    default = now.date() + datetime.timedelta(days=1)
    start = _parse_date(date_str, default)
    if isinstance(start, str):
        return start

    days = max(1, min(days, 30))
    end = start + datetime.timedelta(days=days - 1)

    events = get_events_for_range(start, end)
    tasks = get_all_tasks()

    if days == 1:
        day = build_day_data(start, events, tasks)
        if start <= now.date() + datetime.timedelta(days=1):
            target_iso = start.isoformat()
            for t in tasks:
                if t.get('status') == 'completed':
                    continue
                due = t.get('due')
                if not due or due[:10] < target_iso[:10]:
                    day.pending.append(DayItem(t['title']))
            day.sort()
        return format_single_day_plan(day)
    else:
        day_list = []
        for i in range(days):
            d = start + datetime.timedelta(days=i)
            day_list.append(build_day_data(d, events, tasks))
        return format_multi_day_plan(day_list)
