import datetime
from bot.config import TZ
from bot.google_api import get_calendar_service, get_tasks_service


def add_calendar_event(summary: str, start_time: str, is_birthday: bool = False, duration_minutes: int = 30):
    """Создает мероприятие или день рождения. start_time: ISO формат."""
    service = get_calendar_service()
    # Берем только часть YYYY-MM-DDTHH:MM:SS, отбрасывая Z или +00:00, чтобы жестко привязать к местному времени
    dt_naive = datetime.datetime.fromisoformat(start_time[:19])
    dt = TZ.localize(dt_naive)

    event = {'summary': summary}
    if is_birthday:
        date_str = dt.strftime('%Y-%m-%d')
        event['start'] = {'date': date_str}
        event['end'] = {'date': date_str}
    else:
        event['start'] = {'dateTime': dt.isoformat()}
        event['end'] = {'dateTime': (dt + datetime.timedelta(minutes=duration_minutes)).isoformat()}

    service.events().insert(calendarId='primary', body=event).execute()
    return f"✅ Создано: {summary}"


def add_google_task(title: str, due_date: str = None):
    """Создает задачу в Tasks. Без времени, только дата (YYYY-MM-DD)."""
    service = get_tasks_service()
    body = {'title': title}
    if due_date:
        body['due'] = f"{due_date}T00:00:00Z"
    service.tasks().insert(tasklist='@default', body=body).execute()
    return f"✅ Задача добавлена: {title}"
