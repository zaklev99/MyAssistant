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


def _filter_day_by_time(day, day_date: datetime.date,
                        start_dt: datetime.datetime, end_dt: datetime.datetime):
    """Фильтрует элементы дня по временному окну.
    Для первого/последнего дня отсекает элементы за пределами окна.
    Применяется только к элементам с конкретным временем."""
    start_date = start_dt.date()
    end_date = end_dt.date()

    if day_date == start_date and day_date == end_date:
        # Один и тот же день — фильтруем с обеих сторон
        st, et = start_dt.time(), end_dt.time()
        day.completed = [i for i in day.completed if i.time is None or (st <= i.time <= et)]
        day.pending = [i for i in day.pending if i.time is None or (st <= i.time <= et)]
    elif day_date == start_date:
        # Первый день — отсекаем до start_time
        st = start_dt.time()
        day.completed = [i for i in day.completed if i.time is None or i.time >= st]
        day.pending = [i for i in day.pending if i.time is None or i.time >= st]
    elif day_date == end_date:
        # Последний день — отсекаем после end_time
        et = end_dt.time()
        day.completed = [i for i in day.completed if i.time is None or i.time <= et]
        day.pending = [i for i in day.pending if i.time is None or i.time <= et]
    # Средние дни — без фильтрации


def _build_hours_range(start_dt: datetime.datetime, end_dt: datetime.datetime,
                       events: list, tasks: list) -> list:
    """Строит список DayData для временного диапазона с фильтрацией по часам."""
    day_list = []
    current = start_dt.date()
    while current <= end_dt.date():
        day = build_day_data(current, events, tasks)
        _filter_day_by_time(day, current, start_dt, end_dt)
        day_list.append(day)
        current += datetime.timedelta(days=1)
    return day_list


def get_daily_report(date_str: str = None, days: int = 1, hours: int = None):
    """Формирует отчет.
    date_str: ДД.ММ или ДД.ММ.ГГГГ.
    days: кол-во дней (макс 30).
    hours: кол-во часов назад от текущего момента (приоритетнее days).
    """
    now = datetime.datetime.now(TZ)

    # --- Режим часов: отчёт за последние N часов ---
    if hours is not None:
        hours = max(1, min(hours, 720))
        end_dt = now
        start_dt = now - datetime.timedelta(hours=hours)

        events = get_events_for_range(start_dt.date(), end_dt.date() + datetime.timedelta(days=1))
        tasks = get_all_tasks()

        day_list = _build_hours_range(start_dt, end_dt, events, tasks)

        if len(day_list) == 1:
            return format_single_day_report(day_list[0])
        return format_multi_day_report(day_list)

    # --- Режим дней (прежняя логика) ---
    days = max(1, min(days, 30))
    if not date_str and days > 1:
        default_start = now.date() - datetime.timedelta(days=days - 1)
    else:
        default_start = now.date()
    start = _parse_date(date_str, default_start)
    if isinstance(start, str):
        return start

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


def get_plan(date_str: str = None, days: int = 1, hours: int = None):
    """Формирует план.
    date_str: ДД.ММ или ДД.ММ.ГГГГ (по умолчанию сегодня).
    days: кол-во дней.
    hours: кол-во часов вперёд от текущего момента (приоритетнее days).
    """
    now = datetime.datetime.now(TZ)

    # --- Режим часов: план на ближайшие N часов ---
    if hours is not None:
        hours = max(1, min(hours, 720))
        start_dt = now
        end_dt = now + datetime.timedelta(hours=hours)

        events = get_events_for_range(start_dt.date(), end_dt.date() + datetime.timedelta(days=1))
        tasks = get_all_tasks()

        day_list = _build_hours_range(start_dt, end_dt, events, tasks)
        # Добавляем бессрочные задачи в первый день
        if day_list:
            first_day = day_list[0]
            target_iso = first_day.date.isoformat()
            for t in tasks:
                if t.get('status') == 'completed':
                    continue
                due = t.get('due')
                if not due or due[:10] < target_iso[:10]:
                    first_day.pending.append(DayItem(t['title']))
            first_day.sort()

        if len(day_list) == 1:
            return format_single_day_plan(day_list[0])
        return format_multi_day_plan(day_list)

    # --- Режим дней (прежняя логика) ---
    default = now.date()
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
        # Добавляем бессрочные и просроченные задачи в первый день
        if day_list:
            first_day = day_list[0]
            target_iso = first_day.date.isoformat()
            for t in tasks:
                if t.get('status') == 'completed':
                    continue
                due = t.get('due')
                if not due or due[:10] < target_iso[:10]:
                    first_day.pending.append(DayItem(t['title']))
            first_day.sort()
        return format_multi_day_plan(day_list)
