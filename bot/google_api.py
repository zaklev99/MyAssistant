import os
import datetime
import pytz

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from bot.config import SCOPES, TZ, BASE_DIR, log


def get_google_creds() -> Credentials:
    """Загружает токен и обновляет его при необходимости."""
    token_path = os.path.join(BASE_DIR, 'token.json')
    if not os.path.exists(token_path):
        raise FileNotFoundError("token.json не найден. Запусти auth.py для авторизации.")

    creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if creds.expired and creds.refresh_token:
        log.info("Токен истёк — обновляю...")
        creds.refresh(Request())
        with open(token_path, 'w') as f:
            f.write(creds.to_json())
        log.info("Токен успешно обновлён.")

    return creds


def get_calendar_service():
    return build('calendar', 'v3', credentials=get_google_creds())


def get_tasks_service():
    return build('tasks', 'v1', credentials=get_google_creds())


def get_all_tasks():
    """Получает ВСЕ задачи из Google Tasks (включая скрытые завершённые)."""
    task_service = get_tasks_service()
    tasks = []
    page_token = None
    while True:
        result = task_service.tasks().list(
            tasklist='@default', showCompleted=True, showHidden=True,
            maxResults=100, pageToken=page_token
        ).execute()
        tasks.extend(result.get('items', []))
        page_token = result.get('nextPageToken')
        if not page_token:
            break
    return tasks


def get_events_for_range(start_date, end_date):
    """Получает события из ВСЕХ календарей за диапазон дат."""
    cal_service = get_calendar_service()
    t_start = TZ.localize(
        datetime.datetime.combine(start_date, datetime.time.min)
    ).astimezone(pytz.UTC).isoformat()
    t_end = TZ.localize(
        datetime.datetime.combine(end_date, datetime.time(23, 59, 59))
    ).astimezone(pytz.UTC).isoformat()

    all_events = []
    for cal_entry in cal_service.calendarList().list().execute().get('items', []):
        try:
            ev = cal_service.events().list(
                calendarId=cal_entry['id'], timeMin=t_start, timeMax=t_end,
                singleEvents=True
            ).execute().get('items', [])
            all_events.extend(ev)
        except Exception as e:
            log.warning(f"Ошибка чтения календаря {cal_entry['id']}: {e}")
    return all_events
