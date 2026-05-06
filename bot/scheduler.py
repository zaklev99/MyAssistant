"""
Планировщик оповещений.
APScheduler v3 + хранение настроек в JSON.
"""

import os
import json
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from bot.config import TZ, NOTIFICATIONS_FILE, DATA_DIR, log, bot
from bot.reports import get_daily_report, get_plan

scheduler = AsyncIOScheduler(timezone=TZ)


# --- Хранение настроек ---

def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def load_all_settings() -> dict:
    """Загружает все настройки оповещений из JSON."""
    if not os.path.exists(NOTIFICATIONS_FILE):
        return {}
    try:
        with open(NOTIFICATIONS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_all_settings(data: dict):
    """Сохраняет все настройки в JSON."""
    _ensure_data_dir()
    with open(NOTIFICATIONS_FILE, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_user_settings(user_id: int) -> dict:
    """Получает настройки конкретного пользователя."""
    all_data = load_all_settings()
    uid = str(user_id)
    if uid not in all_data:
        all_data[uid] = {
            "daily_report": {"enabled": False, "hour": 0, "minute": 0},
            "daily_plan": {"enabled": False, "hour": 8, "minute": 0}
        }
        save_all_settings(all_data)
    return all_data[uid]


def update_user_settings(user_id: int, settings: dict):
    """Обновляет настройки пользователя."""
    all_data = load_all_settings()
    all_data[str(user_id)] = settings
    save_all_settings(all_data)
    # Перестроить расписание для этого пользователя
    _rebuild_user_jobs(user_id, settings)


# --- Задачи планировщика ---

async def _send_daily_report(user_id: int):
    """Отправляет ежедневный отчёт пользователю."""
    try:
        log.info(f"[SCHEDULER] Отправка отчёта пользователю {user_id}")
        report = await asyncio.to_thread(get_daily_report)
        await bot.send_message(user_id, report)
    except Exception as e:
        log.error(f"[SCHEDULER] Ошибка отправки отчёта {user_id}: {e}")


async def _send_daily_plan(user_id: int):
    """Отправляет план на день пользователю."""
    try:
        log.info(f"[SCHEDULER] Отправка плана пользователю {user_id}")
        plan = await asyncio.to_thread(get_plan)
        await bot.send_message(user_id, plan)
    except Exception as e:
        log.error(f"[SCHEDULER] Ошибка отправки плана {user_id}: {e}")


# --- Управление расписанием ---

def _job_id(user_id: int, job_type: str) -> str:
    return f"notif_{user_id}_{job_type}"


def _rebuild_user_jobs(user_id: int, settings: dict):
    """Перестраивает расписание для одного пользователя."""
    # Удаляем старые задачи
    for job_type in ('daily_report', 'daily_plan'):
        jid = _job_id(user_id, job_type)
        if scheduler.get_job(jid):
            scheduler.remove_job(jid)

    # Добавляем новые
    report_cfg = settings.get('daily_report', {})
    if report_cfg.get('enabled'):
        scheduler.add_job(
            _send_daily_report,
            CronTrigger(hour=report_cfg['hour'], minute=report_cfg['minute'], timezone=TZ),
            id=_job_id(user_id, 'daily_report'),
            args=[user_id],
            replace_existing=True
        )
        log.info(f"[SCHEDULER] Отчёт для {user_id} в {report_cfg['hour']:02d}:{report_cfg['minute']:02d}")

    plan_cfg = settings.get('daily_plan', {})
    if plan_cfg.get('enabled'):
        scheduler.add_job(
            _send_daily_plan,
            CronTrigger(hour=plan_cfg['hour'], minute=plan_cfg['minute'], timezone=TZ),
            id=_job_id(user_id, 'daily_plan'),
            args=[user_id],
            replace_existing=True
        )
        log.info(f"[SCHEDULER] План для {user_id} в {plan_cfg['hour']:02d}:{plan_cfg['minute']:02d}")


def start_scheduler():
    """Загружает все настройки и запускает планировщик."""
    all_data = load_all_settings()
    for uid_str, settings in all_data.items():
        try:
            user_id = int(uid_str)
            _rebuild_user_jobs(user_id, settings)
        except (ValueError, TypeError):
            continue

    scheduler.start()
    log.info("🔔 Планировщик оповещений запущен.")
