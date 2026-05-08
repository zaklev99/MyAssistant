"""
Модуль форматирования отчётов и планов.
Красивый вывод с отступами, эмодзи, хронологическим порядком.
"""

import datetime
from bot.config import TZ


# --- Структура данных для элементов дня ---

class DayItem:
    """Элемент дня: задача или событие."""
    __slots__ = ('title', 'time', 'end_time', 'is_completed')

    def __init__(self, title: str, time: datetime.time | None = None, end_time: datetime.time | None = None, is_completed: bool = False):
        self.title = title
        self.time = time  # None = без времени
        self.end_time = end_time
        self.is_completed = is_completed

    @property
    def sort_key(self):
        """Для сортировки: timed первые (по времени), untimed последние."""
        if self.time:
            return (0, self.time)
        return (1, datetime.time.max)

    def format(self) -> str:
        """Форматирует элемент с отступом."""
        if self.time:
            time_str = self.time.strftime('%H:%M')
            if self.end_time:
                time_str += f" - {self.end_time.strftime('%H:%M')}"
            return f"   🕐 {time_str}  {self.title}"
        return f"         •  {self.title}"


class DayData:
    """Данные одного дня."""
    __slots__ = ('date', 'birthdays', 'pending', 'completed')

    def __init__(self, date: datetime.date):
        self.date = date
        self.birthdays: list[str] = []
        self.pending: list[DayItem] = []
        self.completed: list[DayItem] = []

    def sort(self):
        """Сортирует: timed по хронологии, untimed в конце."""
        self.pending.sort(key=lambda x: x.sort_key)
        self.completed.sort(key=lambda x: x.sort_key)

    @property
    def is_empty(self) -> bool:
        return not self.birthdays and not self.pending and not self.completed


# --- Построение данных дня ---

def build_day_data(target_date: datetime.date, events: list, tasks: list) -> DayData:
    """
    Строит данные для одного дня из событий календаря и задач.
    Возвращает DayData с отсортированными элементами.
    """
    iso = target_date.strftime('%Y-%m-%d')
    day = DayData(target_date)
    now = datetime.datetime.now(TZ)

    # --- Обработка событий календаря ---
    for e in events:
        summary = e.get('summary', '(без названия)')
        start = e.get('start', {})

        # Весь день (дни рождения и т.д.)
        if 'date' in start and start['date'] == iso:
            day.birthdays.append(summary)
        # С конкретным временем
        elif 'dateTime' in start:
            dt = datetime.datetime.fromisoformat(start['dateTime']).astimezone(TZ)
            
            end = e.get('end', {})
            dt_end = None
            if 'dateTime' in end:
                dt_end = datetime.datetime.fromisoformat(end['dateTime']).astimezone(TZ)
                
            if dt.date() == target_date:
                # Определяем, прошло ли событие
                event_ended = False
                if target_date < now.date():
                    # Прошедший день — все события завершены
                    event_ended = True
                elif target_date == now.date():
                    # Сегодня — проверяем end_time (или start + 30 мин)
                    end_check = dt_end if dt_end else (dt + datetime.timedelta(minutes=30))
                    event_ended = end_check <= now

                item = DayItem(summary, time=dt.time(),
                               end_time=dt_end.time() if dt_end else None,
                               is_completed=event_ended)
                if event_ended:
                    day.completed.append(item)
                else:
                    day.pending.append(item)

    # --- Обработка задач ---
    for t in tasks:
        title = t.get('title', '(без названия)')
        has_due_today = t.get('due', '').startswith(iso)

        # Конвертируем completed из UTC в локальное время
        completed_dt = None
        if t.get('completed'):
            try:
                completed_dt = datetime.datetime.fromisoformat(
                    t['completed'].replace('Z', '+00:00')
                ).astimezone(TZ)
            except (ValueError, KeyError):
                pass

        completed_local_date = completed_dt.date() if completed_dt else None

        # Задача без due, но завершённая в этот день
        completed_today_no_due = (
            not t.get('due')
            and t.get('status') == 'completed'
            and completed_local_date == target_date
        )

        if has_due_today:
            if t.get('status') == 'completed':
                item_time = completed_dt.time() if completed_dt else None
                day.completed.append(DayItem(title, time=item_time, is_completed=True))
            else:
                day.pending.append(DayItem(title))
        elif completed_today_no_due:
            item_time = completed_dt.time() if completed_dt else None
            day.completed.append(DayItem(title, time=item_time, is_completed=True))

    day.sort()
    return day


# --- Форматирование отчёта ---

SEPARATOR = "━━━━━━━━━━━━━━━━━━━━━━"


def format_single_day_report(day: DayData) -> str:
    """Форматирует отчёт за один день."""
    lines = [
        f"📅 Отчет за: {day.date.strftime('%d.%m.%Y')}",
        SEPARATOR
    ]

    if day.birthdays:
        lines.append("")
        lines.append("🎂 Дни рождения:")
        for b in day.birthdays:
            lines.append(f"   • {b}")

    if day.completed:
        lines.append("")
        lines.append("✅ Выполнено:")
        for item in day.completed:
            lines.append(item.format())

    if not day.birthdays and not day.completed:
        lines.append("")
        lines.append("Нет данных за эту дату.")

    return "\n".join(lines)


def format_multi_day_report(days: list[DayData]) -> str:
    """Форматирует отчёт за несколько дней."""
    if not days:
        return "Нет данных за этот период."

    first = days[0].date.strftime('%d.%m.%Y')
    last = days[-1].date.strftime('%d.%m.%Y')
    lines = [
        f"📅 Отчет за период: {first} — {last}",
        SEPARATOR
    ]

    has_anything = False
    for day in days:
        if not day.birthdays and not day.completed:
            continue
        has_anything = True
        lines.append("")
        lines.append(f"📅 {day.date.strftime('%d.%m.%Y')}:")
        if day.birthdays:
            lines.append(f"   🎂 {', '.join(day.birthdays)}")
        if day.completed:
            lines.append("   ✅ Выполнено:")
            for item in day.completed:
                lines.append("   " + item.format())
    
    if not has_anything:
        lines.append("")
        lines.append("Нет данных за этот период.")

    return "\n".join(lines)


def format_single_day_plan(day: DayData) -> str:
    """Форматирует план на один день."""
    lines = [
        f"🚀 План на {day.date.strftime('%d.%m.%Y')}",
        SEPARATOR
    ]

    if day.birthdays:
        lines.append("")
        lines.append("🎂 Дни рождения:")
        for b in day.birthdays:
            lines.append(f"   • {b}")

    if day.pending:
        lines.append("")
        for item in day.pending:
            lines.append(item.format())

    if not day.birthdays and not day.pending:
        lines.append("")
        lines.append("Ничего не запланировано.")

    return "\n".join(lines)


def format_multi_day_plan(days: list[DayData]) -> str:
    """Форматирует план на несколько дней."""
    if not days:
        return "Ничего не запланировано."

    first = days[0].date.strftime('%d.%m.%Y')
    last = days[-1].date.strftime('%d.%m.%Y')
    lines = [
        f"🚀 План на период: {first} — {last}",
        SEPARATOR
    ]

    has_anything = False
    for day in days:
        if not day.birthdays and not day.pending:
            continue
        has_anything = True
        lines.append("")
        lines.append(f"📅 {day.date.strftime('%d.%m.%Y')}:")
        if day.birthdays:
            lines.append(f"   🎂 {', '.join(day.birthdays)}")
        if day.pending:
            for item in day.pending:
                lines.append("   " + item.format())

    if not has_anything:
        lines.append("")
        lines.append("Ничего не запланировано.")

    return "\n".join(lines)
