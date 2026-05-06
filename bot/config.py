import os
import logging
import pytz
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from google import genai

load_dotenv()

# --- ЛОГИРОВАНИЕ ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
log = logging.getLogger('bot')

# --- КОНФИГУРАЦИЯ ---
MODEL_ID = "gemini-3.1-flash-lite-preview"
TZ = pytz.timezone('Europe/Moscow')
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/tasks'
]

# --- КЛИЕНТЫ ---
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
dp = Dispatcher()

# --- ПУТИ ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
NOTIFICATIONS_FILE = os.path.join(DATA_DIR, 'notifications.json')
