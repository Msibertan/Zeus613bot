import json
import shutil
import re
import random
import threading
import requests
import asyncio
import urllib.parse
import urllib.request
import zipfile
import io
import logging
from pathlib import Path
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_file

from docx import Document
from docx.shared import Inches

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try: from deep_translator import GoogleTranslator
except ImportError: GoogleTranslator = None
try: from num2words import num2words
except ImportError: num2words = None

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaVideo, ReplyKeyboardMarkup
from telegram.constants import ChatAction, ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)

from config import BOT_TOKEN, ADMIN_IDS, WHITELIST_ENABLED, WHITELIST_IDS, LOG_CHAT_ID, NETLIFY_TOKEN, NETLIFY_SITE_ID
from services.doc_generator import render_doc

from modules.media_handlers import (
    WAITING_MEDIA_PHOTO, WAITING_MEDIA_VIDEO_NOTE, WAITING_VOICE_SELECTION, WAITING_VOICE_TEXT, 
    WAITING_VOICE_STABILITY, WAITING_VOICE_DELAY, WAITING_VOICE_VIDEO, WAITING_REVIEW_SEASON, 
    WAITING_REVIEW_WEATHER, WAITING_REVIEW_PERSON, WAITING_REVIEW_LOCATION, WAITING_REVIEW_PHOTO,
    handle_transporter_mode, handle_empty_plate_mode, handle_customs_mode, handle_video_blur_mode,
    handle_video_note_mode, receive_media_photo, handle_media_regen, receive_video_note,
    handle_create_review, handle_review_season, handle_review_weather, handle_review_person,
    handle_review_location, receive_review_photo, handle_voiceover_mode, handle_voice_selection,
    receive_voice_text, handle_voice_stability, handle_voice_delay, receive_voice_video, handle_voice_regen
)

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
COMPANIES_DIR = PROJECT_DIR / "companies"
BANKS_DIR = PROJECT_DIR / "templates_banks"
DOVERS_DIR = PROJECT_DIR / "templates_dovers"
BANKS_DIR.mkdir(parents=True, exist_ok=True)
DOVERS_DIR.mkdir(parents=True, exist_ok=True)
ARCHIVE_DIR = PROJECT_DIR / "clients_archive"
ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
CUSTOMS_TEMPLATES_DIR = PROJECT_DIR / "templates_customs"
INVOICE_TEMPLATES_DIR = PROJECT_DIR / "templates_invoice"
CALC_TEMPLATES_DIR = PROJECT_DIR / "templates_calc"
QUEUE_TEMPLATES_DIR = PROJECT_DIR / "templates_queue"
WHITELIST_FILE = PROJECT_DIR / "whitelist.json"
STATS_FILE = PROJECT_DIR / "user_stats.json"
WHITELIST_MAP = {}

BASE_WEBHOOK_URL = "https://nonnephritic-minda-logarithmically.ngrok-free.dev"

URL_UTIL = "https://raw.githubusercontent.com/gorbacenkovitalij6-prog/photopeautil/main/PHOTOPEAUTIL613.psd"
URL_BRIEF = "https://raw.githubusercontent.com/gorbacenkovitalij6-prog/Brif/main/Brif_photopea.psd"
URL_CV = "https://raw.githubusercontent.com/gorbacenkovitalij6-prog/CarVertical/main/CarVertical_photopea.psd"

BYN_TO_EUR_RATE = 3.38 
RUB_TO_EUR_RATE = 105.0 
DKP_COMMISSION = 50.0 

# База масел
OIL_DB = {
    "volkswagen": ("VW 504 00", "5W-30"),
    "vw": ("VW 504 00", "5W-30"),
    "peugeot": ("PSA B712290", "0W-20"),
    "bmw": ("BMW Longlife-04", "5W-30"),
    "mercedes": ("MB 229.51", "5W-30"),
    "mercedes-benz": ("MB 229.51", "5W-30"),
    "audi": ("VW 507 00", "5W-30"),
    "skoda": ("VW 507 00", "5W-30"),
    "renault": ("PSA B71 2290", "5W-30"),
    "ford": ("RN0720", "5W-30"),
    "toyota": ("WSS-M2C913-D", "5W-30")
}

USER_SCRIPTS = {}

flask_app = Flask(__name__)

# ==========================================
# 🏆 СИСТЕМА ДОСТИЖЕНИЙ (ГЕЙМИФИКАЦИЯ)
# ==========================================
ACHIEVEMENTS = {
    # Сет "Автодилер"
    "brand_audi": {"icon": "💍", "name": "Властелин колец", "desc": "Оформил 10 документов на Audi"},
    "brand_bmw": {"icon": "🦇", "name": "Баварский вентилятор", "desc": "Оформил 10 документов на BMW"},
    "brand_mercedes": {"icon": "⭐", "name": "Трехлучевая звезда", "desc": "Оформил 10 документов на Mercedes"},
    "brand_vw": {"icon": "🚜", "name": "Народный любимец", "desc": "Оформил 10 документов на VW"},
    "brand_kia": {"icon": "🐯", "name": "Корейский тигр", "desc": "Оформил 10 документов на Kia/Hyundai"},
    "brand_toyota": {"icon": "🍣", "name": "Император", "desc": "Оформил 10 документов на Toyota/Lexus"},
    "brand_tesla": {"icon": "⚡", "name": "Электро-Шейх", "desc": "Оформил 10 электрокаров (Tesla/Zeekr)"},
    "brand_volvo": {"icon": "🛡", "name": "Шведская крепость", "desc": "Оформил 10 документов на Volvo"},
    "brand_skoda": {"icon": "🏹", "name": "Чешский стрела", "desc": "Оформил 10 документов на Skoda"},
    "brand_renault": {"icon": "🥖", "name": "Французский багет", "desc": "Оформил 10 документов на Renault/Peugeot"},
    "brand_ford": {"icon": "🦅", "name": "Американская мечта", "desc": "Оформил 10 документов на Ford/Chevrolet"},
    "brand_nissan": {"icon": "⛩", "name": "Японский городовой", "desc": "Оформил 10 документов на Nissan/Mazda/Honda"},
    "brand_geely": {"icon": "🐉", "name": "Китайский дракон", "desc": "Оформил 10 документов на Geely/Haval/Li"},
    "brand_porsche": {"icon": "🏎", "name": "Штутгартский жеребец", "desc": "Оформил 10 документов на Porsche"},
    
    # Сет "Профессионал"
    "doc_first": {"icon": "🍾", "name": "Первая кровь", "desc": "Самый первый документ в карьере"},
    "doc_100": {"icon": "📚", "name": "Бумажный червь", "desc": "Сделал 100 документов"},
    "doc_500": {"icon": "🐲", "name": "Канцелярский монстр", "desc": "Сделал 500 документов"},
    "doc_1000": {"icon": "🌌", "name": "Матрица Таможни", "desc": "Оформил 1000 документов"},
    "master_customs": {"icon": "🛂", "name": "Мастер Таможни", "desc": "50 полных пакетов документов"},
    "master_invoice": {"icon": "💸", "name": "Инвойс-магнат", "desc": "50 инвойсов/выписок"},
    "master_brief": {"icon": "🇩🇪", "name": "Брифист", "desc": "20 немецких брифов"},
    "master_util": {"icon": "♻️", "name": "Король Утиля", "desc": "20 расчетов утильсбора"},
    "master_cv": {"icon": "🚗", "name": "Карвертикальный эксперт", "desc": "20 отчетов CarVertical"},
    "master_qr": {"icon": "📱", "name": "QR-Менеджер", "desc": "50 чеков с QR кодами"},
    
    # Сет "Медиа-Креатор"
    "note_10": {"icon": "🔵", "name": "Блогер", "desc": "Сделал 10 видео-кружков"},
    "note_50": {"icon": "🤳", "name": "Лидер мнений", "desc": "Сделал 50 видео-кружков"},
    "note_100": {"icon": "🎬", "name": "Звезда Telegram", "desc": "Сделал 100 видео-кружков"},
    "blur_10": {"icon": "🕶", "name": "Шпион", "desc": "Замазал номера на 10 видео"},
    "blur_50": {"icon": "🥷", "name": "Анонимус", "desc": "Замазал номера на 50 видео"},
    "transporter_10": {"icon": "🚛", "name": "Грузчик", "desc": "Отправил 10 машин на автовозе"},
    "transporter_50": {"icon": "🛣", "name": "Логист", "desc": "Отправил 50 машин на автовозе"},
    "empty_10": {"icon": "🔲", "name": "Снял транзиты", "desc": "Убрал номера с 10 машин"},
    "empty_50": {"icon": "🧼", "name": "Чистый кузов", "desc": "Убрал номера с 50 машин"},
    "customs_ai_10": {"icon": "📸", "name": "Фотограф СВХ", "desc": "Сгенерировал 10 фото на фоне таможни"},
    "customs_ai_50": {"icon": "🏢", "name": "Брокер-иллюзионист", "desc": "Сгенерировал 50 фото на таможне"},
    "voice_10": {"icon": "🎙", "name": "Диктор", "desc": "Озвучил 10 видео через ИИ"},
    "voice_50": {"icon": "🎧", "name": "Звукорежиссер", "desc": "Озвучил 50 видео нейросетью"},
    "review_10": {"icon": "📝", "name": "Копирайтер", "desc": "Сгенерировал 10 отзывов ИИ"},
    "review_50": {"icon": "🌟", "name": "Пиар-Менеджер", "desc": "Сгенерировал 50 отзывов ИИ"},
    
    # Сет "Машина времени"
    "time_night": {"icon": "🦉", "name": "Ночной дозор", "desc": "Работал с 01:00 до 05:00 утра"},
    "time_early": {"icon": "🌅", "name": "Ранняя пташка", "desc": "Оформил документ с 05:00 до 08:00"},
    "time_0900": {"icon": "🥐", "name": "Завтрак чемпиона", "desc": "Сделал документ ровно в 09:00"},
    "time_1300": {"icon": "🍜", "name": "Обеденный перерыв", "desc": "Сделал документ ровно в 13:00"},
    "time_0000": {"icon": "🧛‍♂️", "name": "Полуночный ковбой", "desc": "Сделал документ ровно в 00:00"},
    "day_sat": {"icon": "🍺", "name": "Субботний папа", "desc": "Работал в субботу"},
    "day_sun": {"icon": "🛋", "name": "Воскресный дилер", "desc": "Работал в воскресенье"},

    # Сет "География и Удача"
    "geo_europe": {"icon": "🇪🇺", "name": "Европеец", "desc": "Оформил авто европейской сборки (VIN W,V,Z)"},
    "geo_usa": {"icon": "🇺🇸", "name": "Американец", "desc": "Оформил авто из США (VIN 1,4,5)"},
    "geo_asia": {"icon": "🇯🇵", "name": "Азиат", "desc": "Оформил авто из Азии (VIN J,K,L)"},
    "luck_gai": {"icon": "👮‍♂️", "name": "Любимчик ГАИ", "desc": "Нашел 1% шанс! Гаишник отпустил без штрафа"},
    "luck_777": {"icon": "🎰", "name": "Джекпот", "desc": "Сделал 777-й документ!"},
    "old_school": {"icon": "📻", "name": "Олдскул", "desc": "Оформил машину старше 2005 года"},
}

def get_rank(docs):
    if docs >= 1000: return "Авто-Шейх 👑"
    if docs >= 600: return "Серый Импортер 🕶"
    if docs >= 300: return "Таможенный Конфискат 👮‍♂️"
    if docs >= 150: return "Хозяин Автохауса 🏢"
    if docs >= 50: return "Перекуп 🚘"
    if docs >= 10: return "Подборщик 🔍"
    return "Пешеход 🚶‍♂️"

def load_stats():
    if not STATS_FILE.exists(): return {}
    try: return json.loads(STATS_FILE.read_text("utf-8"))
    except: return {}

def save_stats(data):
    STATS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=4), "utf-8")

async def track_and_check(context, user, doc_type, raw_text):
    stats = load_stats()
    uid = str(user.id)
    name = user.full_name or user.username or "Неизвестный"
    
    if uid not in stats:
        stats[uid] = {"name": name, "docs": 0, "types": {}, "brands": {}, "achievements": []}
    
    user_data = stats[uid]
    user_data["name"] = name
    user_data["docs"] += 1
    user_data["types"][doc_type] = user_data["types"].get(doc_type, 0) + 1
    
    # 1. Поиск брендов машин
    text_lower = raw_text.lower()
    brand_map = {
        "audi": "audi", "bmw": "bmw", "mercedes": "mercedes", "benz": "mercedes", "vw": "vw", "volkswagen": "vw",
        "kia": "kia", "hyundai": "kia", "toyota": "toyota", "lexus": "toyota", "tesla": "tesla", "zeekr": "tesla",
        "volvo": "volvo", "skoda": "skoda", "renault": "renault", "peugeot": "renault", "ford": "ford", 
        "chevrolet": "ford", "nissan": "nissan", "mazda": "nissan", "honda": "nissan", "geely": "geely", 
        "haval": "geely", "li": "geely", "porsche": "porsche"
    }
    for key, val in brand_map.items():
        if key in text_lower:
            user_data["brands"][val] = user_data["brands"].get(val, 0) + 1
            break # Только один бренд за документ
            
    # 2. Поиск года (для олдскула)
    year_match = re.search(r'\b(199[0-9]|200[0-5])\b', raw_text)
    
    # 3. Поиск VIN (для географии)
    vin_match = re.search(r'\b([A-HJ-NPR-Z0-9]{17})\b', raw_text.upper())
    
    new_achievements = []
    
    # === ПРОВЕРКА УСЛОВИЙ ===
    def award(ach_id):
        if ach_id not in user_data["achievements"]:
            user_data["achievements"].append(ach_id)
            new_achievements.append(ach_id)

    # Кол-во
    if user_data["docs"] >= 1: award("doc_first")
    if user_data["docs"] >= 100: award("doc_100")
    if user_data["docs"] >= 500: award("doc_500")
    if user_data["docs"] >= 1000: award("doc_1000")
    if user_data["docs"] == 777: award("luck_777")
    
    # Типы
    if user_data["types"].get("customs_full", 0) >= 50: award("master_customs")
    if user_data["types"].get("invoice_all", 0) + user_data["types"].get("invoice_statement", 0) >= 50: award("master_invoice")
    if user_data["types"].get("psd_brief", 0) >= 20: award("master_brief")
    if user_data["types"].get("psd_util", 0) >= 20: award("master_util")
    if user_data["types"].get("psd_cv", 0) >= 20: award("master_cv")
    if user_data["types"].get("qr", 0) >= 50: award("master_qr")
    
    # Медиа-креатор
    if user_data["types"].get("media_note", 0) >= 10: award("note_10")
    if user_data["types"].get("media_note", 0) >= 50: award("note_50")
    if user_data["types"].get("media_note", 0) >= 100: award("note_100")
    if user_data["types"].get("media_blur", 0) >= 10: award("blur_10")
    if user_data["types"].get("media_blur", 0) >= 50: award("blur_50")
    if user_data["types"].get("media_transporter", 0) >= 10: award("transporter_10")
    if user_data["types"].get("media_transporter", 0) >= 50: award("transporter_50")
    if user_data["types"].get("media_empty", 0) >= 10: award("empty_10")
    if user_data["types"].get("media_empty", 0) >= 50: award("empty_50")
    if user_data["types"].get("media_customs", 0) >= 10: award("customs_ai_10")
    if user_data["types"].get("media_customs", 0) >= 50: award("customs_ai_50")
    if user_data["types"].get("media_voiceover", 0) >= 10: award("voice_10")
    if user_data["types"].get("media_voiceover", 0) >= 50: award("voice_50")
    if user_data["types"].get("media_review", 0) >= 10: award("review_10")
    if user_data["types"].get("media_review", 0) >= 50: award("review_50")
    
    # Бренды
    if user_data["brands"].get("audi", 0) >= 10: award("brand_audi")
    if user_data["brands"].get("bmw", 0) >= 10: award("brand_bmw")
    if user_data["brands"].get("mercedes", 0) >= 10: award("brand_mercedes")
    if user_data["brands"].get("vw", 0) >= 10: award("brand_vw")
    if user_data["brands"].get("kia", 0) >= 10: award("brand_kia")
    if user_data["brands"].get("toyota", 0) >= 10: award("brand_toyota")
    if user_data["brands"].get("tesla", 0) >= 10: award("brand_tesla")
    if user_data["brands"].get("volvo", 0) >= 10: award("brand_volvo")
    if user_data["brands"].get("skoda", 0) >= 10: award("brand_skoda")
    if user_data["brands"].get("renault", 0) >= 10: award("brand_renault")
    if user_data["brands"].get("ford", 0) >= 10: award("brand_ford")
    if user_data["brands"].get("nissan", 0) >= 10: award("brand_nissan")
    if user_data["brands"].get("geely", 0) >= 10: award("brand_geely")
    if user_data["brands"].get("porsche", 0) >= 10: award("brand_porsche")
    
    # Время
    now = datetime.now()
    if 1 <= now.hour <= 4: award("time_night")
    if 5 <= now.hour <= 8: award("time_early")
    if now.hour == 9 and now.minute <= 10: award("time_0900")
    if now.hour == 13 and now.minute <= 10: award("time_1300")
    if now.hour == 0 and now.minute <= 10: award("time_0000")
    if now.weekday() == 5: award("day_sat")
    if now.weekday() == 6: award("day_sun")
    
    # Фановые
    if year_match: award("old_school")
    if random.randint(1, 100) == 1: award("luck_gai")
    
    # География
    if vin_match:
        v = vin_match.group(1)
        if v[0] in ['W','V','Z','S']: award("geo_europe")
        if v[0] in ['1','4','5']: award("geo_usa")
        if v[0] in ['J','K','L']: award("geo_asia")

    save_stats(stats)
    
    # Если есть новые медали — кричим в канал и пользователю!
    for ach_id in new_achievements:
        ach = ACHIEVEMENTS[ach_id]
        msg = f"🎖 <b>ДОСТИЖЕНИЕ РАЗБЛОКИРОВАНО!</b>\nПользователь: <b>{name}</b>\n\n{ach['icon']} <b>«{ach['name']}»</b>\n<i>{ach['desc']}</i>"
        try:
            await context.bot.send_message(chat_id=user.id, text=f"🎉 Поздравляем! Ты получил новую медаль:\n{ach['icon']} <b>«{ach['name']}»</b>", parse_mode=ParseMode.HTML)
            if LOG_CHAT_ID:
                await context.bot.send_message(chat_id=LOG_CHAT_ID, text=msg, parse_mode=ParseMode.HTML)
        except: pass

# ==========================================
# ОСНОВНОЙ КОД БОТА
# ==========================================

@flask_app.route('/', methods=['GET'])
def index(): return "✅ SERVER ONLINE", 200

@flask_app.route('/tools/<chat_id>', methods=['GET'])
def tools_page(chat_id):
    chat_id = str(chat_id)
    script_content = USER_SCRIPTS.get(chat_id, "// Ошибка: Скрипт не найден. Сгенерируйте заново в боте.")
    
    photopea_config = {"files": [USER_SCRIPTS.get(f"{chat_id}_link", URL_UTIL)], "server": {"version": 1, "url": f"{BASE_WEBHOOK_URL}/webhook/{chat_id}?ngrok-skip-browser-warning=true", "formats": ["jpg:0.9"]}}
    photopea_url = f"https://www.photopea.com#{urllib.parse.quote(json.dumps(photopea_config))}"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Панель Инструментов</title>
        <style>
            body {{ font-family: -apple-system, sans-serif; background-color: #1c1c1e; color: white; text-align: center; padding: 20px; }}
            h2 {{ margin-bottom: 20px; color: #fff; }}
            .btn {{ display: block; width: 100%; padding: 18px; margin: 15px 0; border: none; border-radius: 12px; font-size: 18px; font-weight: bold; cursor: pointer; text-decoration: none; box-sizing: border-box; }}
            .btn-copy {{ background-color: #32d74b; color: #000; box-shadow: 0 4px 10px rgba(50, 215, 75, 0.3); }}
            .btn-open {{ background-color: #0a84ff; color: #fff; box-shadow: 0 4px 10px rgba(10, 132, 255, 0.3); }}
            .step {{ text-align: left; margin-bottom: 5px; font-size: 15px; color: #ccc; font-weight: bold; }}
            .hint {{ font-size: 13px; color: #888; text-align: left; margin-bottom: 30px; }}
        </style>
    </head>
    <body>
        <h2>🛠 Панель Инструментов</h2>
        
        <div class="step">Шаг 1: Скопируй код</div>
        <div class="hint">Нажми зеленую кнопку, чтобы код сохранился в буфер обмена.</div>
        <button class="btn btn-copy" onclick="copyCode()">📋 КОПИРОВАТЬ КОД</button>
        
        <div class="step" style="margin-top: 40px;">Шаг 2: Открой редактор</div>
        <div class="hint">В редакторе нажми: <b>File -> Script</b>, вставь код und нажми OK.</div>
        <a href="{photopea_url}" class="btn btn-open" target="_blank">🚀 ОТКРЫТЬ PHOTOPEA</a>

        <textarea id="codeArea" readonly style="position: absolute; left: -9999px;">{script_content}</textarea>

        <script>
            function copyCode() {{
                var copyText = document.getElementById("codeArea");
                copyText.select();
                copyText.setSelectionRange(0, 99999); 
                navigator.clipboard.writeText(copyText.value).then(function() {{
                    alert("✅ КОД УСПЕШНО СКОПИРОВАН!\\n\\nТеперь нажми синюю кнопку 'ОТКРЫТЬ PHOTOPEA'.");
                }}, function() {{
                    document.execCommand("copy");
                    alert("✅ Скопировано!");
                }});
            }}
        </script>
    </body>
    </html>
    """
    return html

def translit_to_german(text):
    if not text: return ""
    mapping = {'а':'a','б':'b','в':'w','г':'g','д':'d','е':'je','ё':'jo','ж':'sch','з':'s','и':'i','й':'j','к':'k','л':'l','м':'m','н':'n','о':'o','п':'p','р':'r','с':'s','т':'t','у':'u','ф':'f','х':'ch','ц':'z','ч':'tsch','ш':'sch','щ':'schtsch','ъ':'','ы':'y','ь':'','э':'e','ю':'ju','я':'ja','А':'A','Б':'B','В':'W','Г':'G','Д':'D','Е':'Je','Ё':'Jo','Ж':'Sch','З':'S','И':'I','Й':'J','К':'K','Л':'L','М':'M','Н':'N','О':'O','П':'P','Р':'R','С':'S','Т':'T','У':'U','Ф':'F','Х':'Ch','Ц':'Z','Ч':'Tsch','Ш':'Sch','Щ':'Schtsch','Ъ':'','Ы':'Y','Ь':'','Э':'E','Ю':'Ju','Я':'Ja'}
    res = ""
    for char in text: res += mapping.get(char, char)
    return res

def get_client_path(raw_name: str) -> Path:
    safe_name = "".join([c for c in raw_name if c.isalnum() or c in (" ", "-", "_")]).strip() or "Client"
    p = ARCHIVE_DIR / safe_name
    p.mkdir(parents=True, exist_ok=True)
    return p

def load_whitelist_store():
    global WHITELIST_MAP
    try:
        if WHITELIST_FILE.exists():
            data = json.loads(WHITELIST_FILE.read_text("utf-8") or "{}")
            if isinstance(data, dict): WHITELIST_MAP = {str(k): str(v) for k,v in data.items()}
            elif isinstance(data, list): WHITELIST_MAP = {str(x): "" for x in data}
    except: pass

def is_allowed(uid: int) -> bool:
    if ADMIN_IDS and uid in ADMIN_IDS: return True
    if not WHITELIST_ENABLED: return True
    return str(uid) in WHITELIST_MAP

def is_admin(uid: int) -> bool: return bool(ADMIN_IDS) and uid in ADMIN_IDS

def deploy_to_netlify(folder_path: Path, html_data: dict) -> str:
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for file_path in folder_path.rglob('*'):
            if file_path.is_file():
                content = file_path.read_bytes()
                if file_path.name == 'index.html':
                    text = content.decode('utf-8')
                    for key, value in html_data.items():
                        text = text.replace(f"{{{{{key}}}}}", str(value))
                    content = text.encode('utf-8')
                
                arcname = file_path.relative_to(folder_path)
                zip_file.writestr(str(arcname), content)
    
    headers = {
        'Authorization': f'Bearer {NETLIFY_TOKEN}',
        'Content-Type': 'application/zip'
    }
    
    url = "https://api.netlify.com/api/v1/sites"
    response = requests.post(url, headers=headers, data=zip_buffer.getvalue())
    
    if response.status_code in [200, 201]: 
        data = response.json()
        final_url = data.get('ssl_url') or data.get('url')
        if not final_url:
            raise Exception("Netlify создал сайт, но не вернул ссылку на него!")
        return final_url
    else:
        raise Exception(f"Ошибка создания нового сайта на Netlify: {response.text}")

def load_companies() -> dict:
    companies = {}
    if not COMPANIES_DIR.exists(): return companies
    for sub in sorted(COMPANIES_DIR.iterdir()):
        if not sub.is_dir(): continue
        meta = sub / "meta.json"
        if meta.exists():
            try:
                data = json.loads(meta.read_text("utf-8"))
                cid = data.get("id") or sub.name
                data.update({"id": cid, "name": data.get("name", cid), "template_path": str(sub/"template.docx"), "dover_path": str(sub/"dover.docx")})
                companies[cid] = data
            except: continue
    return companies

def load_banks() -> dict:
    banks = {}
    if not BANKS_DIR.exists(): return banks
    for sub in sorted(BANKS_DIR.iterdir()):
        if not sub.is_dir(): continue
        meta = sub / "meta.json"
        if meta.exists():
            try:
                data = json.loads(meta.read_text("utf-8"))
                cid = data.get("id") or sub.name
                data.update({"id": cid, "name": data.get("name", cid), "template_path": str(sub/"statement.docx")})
                banks[cid] = data
            except: continue
    return banks

def load_dovers() -> dict:
    dovers = {}
    if not DOVERS_DIR.exists(): return dovers
    for sub in sorted(DOVERS_DIR.iterdir()):
        if not sub.is_dir(): continue
        meta = sub / "meta.json"
        if meta.exists():
            try:
                data = json.loads(meta.read_text("utf-8"))
                cid = data.get("id") or sub.name
                data.update({"id": cid, "name": data.get("name", cid), "dover_path": str(sub/"dover.docx")})
                dovers[cid] = data
            except: continue
    return dovers

def safe_val(val):
    val = val.strip()
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        val = val[1:-1].strip()
    return json.dumps(val, ensure_ascii=False)

(TOP_MENU, CHOOSING_COMPANY, WAITING_ANSWERS, CHOOSING_CUSTOMS_DOC, WAITING_NEW_CUSTOMS_DATA, CHOOSING_INVOICE_DOC, WAITING_INVOICE_DATA, WAITING_DOVER_DATA, WAITING_PSD_DATA, CHOOSING_QR_CURRENCY, CHOOSING_QR_TYPE, WAITING_QR_DATA, WAITING_SERVICE_DATA, CHOOSING_BANK, WAITING_QUEUE_DATA) = range(15)
(ADMIN_MENU, ADMIN_ADD_ID, ADMIN_ADD_NAME, ADMIN_ADD_QUESTIONS, ADMIN_ADD_TEMPLATE, ADMIN_REMOVE_ID, ADMIN_WL_MENU, ADMIN_WL_ADD, ADMIN_WL_REMOVE, ADMIN_ADD_DOVER) = range(100, 110)
(ADMIN_ADD_BANK_ID, ADMIN_ADD_BANK_NAME, ADMIN_ADD_BANK_TEMPLATE, ADMIN_ADD_DOVER2_ID, ADMIN_ADD_DOVER2_NAME, ADMIN_ADD_DOVER2_TEMPLATE) = range(110, 116)

def generate_util_script(data):
    return f"""#target photoshop
var INN = {safe_val(data.get('inn', ''))};
var KPP = {safe_val(data.get('kpp', ''))};
var OGRN = {safe_val(data.get('ogrn', ''))};
var CALC_DATE = {safe_val(data.get('calc_date', ''))};
var COMPANY = {safe_val(data.get('company', ''))};
var LEAD_ID = {safe_val(data.get('lead_id', ''))};
var SURNAME = {safe_val(data.get('surname', ''))};
var NAME = {safe_val(data.get('name', ''))};
var PATRONYMIC = {safe_val(data.get('patronymic', ''))};
var UTIL_SUM = {safe_val(data.get('util_sum', ''))};
var VIN = {safe_val(data.get('vin', ''))};
var BRAND = {safe_val(data.get('brand', ''))};
var MODEL = {safe_val(data.get('model', ''))};
var CAR_YEAR = {safe_val(data.get('year', ''))};
var ENGINE_VOL = {safe_val(data.get('vol', ''))};
var MASS = {safe_val(data.get('mass', ''))};
var PASSPORT_NUM = {safe_val(data.get('passport_num', ''))};
var PASSPORT_DATE = {safe_val(data.get('passport_date', ''))};

var UTIL_COEFF = "";
var cleanSum = String(UTIL_SUM).replace(/[^0-9.]/g, '');
var sumValue = parseFloat(cleanSum);
if (!isNaN(sumValue) && sumValue > 0) {{
    var result = sumValue / 20000;
    UTIL_COEFF = String(result.toFixed(1)); 
}}

var MAP = {{
    M1: INN, M2: KPP, M3: OGRN, M4: CALC_DATE, M5: COMPANY, M6: SURNAME, M7: NAME, 
    M8: PATRONYMIC, M9: UTIL_SUM, M10: VIN, M11: BRAND, M12: MODEL, M13: BRAND + " " + MODEL, 
    M14: ENGINE_VOL, M15: MASS, M16: PASSPORT_NUM, M17: PASSPORT_DATE, M18: CAR_YEAR, 
    M24: UTIL_COEFF, M25: LEAD_ID        
}};

function canonicalMName(name) {{
    if (!name) return "";
    var name = String(name).replace(/\\s+/g, "").toUpperCase();
    name = name.replace(/М/g, "M").replace(/M0+/g, "M");
    return name;
}}

function walkLayers(layers) {{
    for (var i = 0; i < layers.length; i++) {{
        var layer = layers[i];
        if (layer.typename === "LayerSet") {{ walkLayers(layer.layers); }} 
        else if (layer.kind === LayerKind.TEXT) {{
            var cname = canonicalMName(layer.name);
            if (MAP.hasOwnProperty(cname)) {{
                 if (MAP[cname] !== undefined) {{
                    try {{ layer.textItem.contents = MAP[cname]; }} catch(e) {{}}
                    try {{ layer.textItem.fauxBold = false; }} catch(e) {{}}
                 }}
            }}
        }}
    }}
}}
walkLayers(app.activeDocument.layers);

try {{
    app.activeDocument.saveToOE('jpg');
    alert("✅ Скрипт Утиль выполнен! Отправляю файл в ТГ...");
}} catch(e) {{
    alert("❌ ОШИБКА ОТПРАВКИ!\\n\\nВы открыли Photopea не через синюю кнопку в нашей панели.");
}}
"""

def generate_brief_script(data):
    return f"""#target photoshop
var CAR_YEAR = {safe_val(data.get('year', ''))};
var BRAND = {safe_val(data.get('brand', ''))};
var MODEL = {safe_val(data.get('model', ''))};
var VIN = {safe_val(data.get('vin', ''))};
var BODY_DE = {safe_val(data.get('body', ''))};
var COLOR_DE = {safe_val(data.get('color', ''))};
var ENGINE_CC = {safe_val(data.get('engine_cc', ''))};
var ENGINE_TYPE_DE = {safe_val(data.get('engine_type', ''))};
var TRANSMISSION_DE = {safe_val(data.get('transmission', ''))};
var POWER_KW = {safe_val(data.get('power_kw', ''))};
var MAX_RPM = "5700";
var RIM_SIZE = {safe_val(data.get('rim', ''))};
var ENGINE_CODE = "A25A-FXS";

function padLeft(str, length) {{
    str = String(str);
    while (str.length < length) str = "0" + str;
    return str;
}}

var MAP = {{
    M1: "24.04." + CAR_YEAR, M2: "24.04." + CAR_YEAR, M3: BRAND, M4: MODEL,
    M5: ENGINE_CODE, M6: ENGINE_CODE + " (4)", M7: BRAND + " " + MODEL, M8: BRAND + " (europe)",
    M9: VIN, M10: BODY_DE, M11: COLOR_DE, M12: ENGINE_CC, M13: ENGINE_TYPE_DE,
    M14: "e1-" + CAR_YEAR + "/116*0252*20", M15: POWER_KW + "  /" + MAX_RPM,
    M16: "12.04." + CAR_YEAR, M17: BRAND, M18: "24.04." + CAR_YEAR, M19: "24.04." + CAR_YEAR,
    M20: "24.04." + CAR_YEAR, M21: VIN, M22: BRAND, M23: ENGINE_CODE, M24: ENGINE_CODE + " (4)",
    M25: ENGINE_CODE + "-FE-DOHC", M26: BRAND + " " + MODEL, M27: BRAND + " EUROPE (B)",
    M28: TRANSMISSION_DE, M29: "715/" + CAR_YEAR + "*175/" + CAR_YEAR + "J*", M30: COLOR_DE,
    M31: "15.01." + CAR_YEAR + "*", M32: padLeft(POWER_KW, 3) + "/" + padLeft(MAX_RPM, 5),
    M33: "235/55R" + RIM_SIZE + " 100H\\n235/55R" + RIM_SIZE + " 100H", M34: ENGINE_TYPE_DE,
    M35: "", M36: "15.01." + CAR_YEAR
}};

function canonicalMName(name) {{
    if (!name) return "";
    name = name.replace(/М/g, "M");
    name = name.replace(/\\s+/g, "");
    var match = name.match(/^M0*(\\d+)$/i);
    if (match) return "M" + parseInt(match[1], 10);
    return name;
}}

function walkLayers(layers, callback) {{
    for (var i = 0; i < layers.length; i++) {{
        var layer = layers[i];
        if (layer.typename === "ArtLayer") {{
            callback(layer);
        }} else if (layer.typename === "LayerSet") {{
            walkLayers(layer.layers, callback);
        }}
    }}
}}

var replaced = 0;
walkLayers(app.activeDocument.layers, function(layer) {{
    if (layer.kind === LayerKind.TEXT) {{
        var cname = canonicalMName(layer.name);
        if (MAP.hasOwnProperty(cname)) {{
            layer.textItem.contents = MAP[cname];
            replaced++;
        }}
    }}
}});

try {{
    app.activeDocument.saveToOE('jpg');
    alert("✅ Скрипт БРИФ выполнен! Обновлено слоев: " + replaced + "\\nОтправляю файл в ТГ...");
}} catch(e) {{
    alert("❌ ОШИБКА ОТПРАВКИ!\\n\\nВы открыли Photopea не через синюю кнопку в нашей панели.");
}}
"""

def generate_cv_script(data):
    return f"""#target photopea
(function () {{
    var CAR_NAME    = {safe_val(data.get('car_name', ''))}; 
    var DATE_GEN    = {safe_val(data.get('date_gen', ''))};
    var DATE_VALID  = {safe_val(data.get('date_valid', ''))};
    var YEAR        = {safe_val(data.get('year', ''))};
    var MILEAGE     = {safe_val(data.get('mileage', ''))};
    var PRICE_LOW   = {safe_val(data.get('price_low', ''))};
    var PRICE_AVG   = {safe_val(data.get('price_avg', ''))};
    var PRICE_HIGH  = {safe_val(data.get('price_high', ''))};
    var ENGINE_VOL  = {safe_val(data.get('engine_vol', ''))};
    var CYLINDERS   = {safe_val(data.get('cylinders', ''))};
    var COLOR       = {safe_val(data.get('color', ''))};
    var GEARBOX     = {safe_val(data.get('gearbox', ''))};
    var FUEL        = {safe_val(data.get('fuel', ''))};
    var DRIVE       = {safe_val(data.get('drive', ''))};
    var POWER       = {safe_val(data.get('power', ''))}; 
    var BODY        = {safe_val(data.get('body', ''))};
    var DOORS       = {safe_val(data.get('doors', ''))};
    var VIN         = {safe_val(data.get('vin', ''))};

    var MAP = {{
        M1: CAR_NAME, M2: DATE_GEN, M3: DATE_VALID, M4: YEAR, M5: MILEAGE,
        M6: PRICE_LOW, M7: PRICE_AVG, M8: PRICE_HIGH, M9: VIN, M10: ENGINE_VOL,
        M11: POWER, M12: FUEL, M13: GEARBOX, M14: DRIVE, M15: BODY,
        M16: DOORS, M17: COLOR, M18: CYLINDERS
    }};

    function canonicalMName(name) {{
        if (!name) return "";
        return name.replace(/М|M/g, "M").replace(/\\s+/g, "").replace(/^M0+/, "M");
    }}

    function walkLayers(container, cb) {{
        for (var i = 0; i < container.layers.length; i++) {{
            var layer = container.layers[i];
            cb(layer);
            if (layer.layers && layer.layers.length) walkLayers(layer, cb);
        }}
    }}

    var replaced = [];
    walkLayers(app.activeDocument, function (layer) {{
        if (layer.kind === LayerKind.TEXT) {{
            var cname = canonicalMName(layer.name);
            if (MAP.hasOwnProperty(cname)) {{
                layer.textItem.contents = String(MAP[cname]);
                replaced.push(cname);
            }}
        }}
    }});
    
    try {{
        app.activeDocument.saveToOE('jpg');
        alert("✅ Готово Карвертикал! Заменено: " + replaced.length + "\\nОтправляю в ТГ...");
    }} catch(e) {{
        alert("❌ ОШИБКА ОТПРАВКИ!\\n\\nВы открыли Photopea не через синюю кнопку в нашей панели.");
    }}
}})();
"""

def kb_main(admin):
    btns = [
        [InlineKeyboardButton("📄 Договоры", callback_data="menu:contracts"), InlineKeyboardButton("✍️ Доверенность", callback_data="menu:dover")],
        [InlineKeyboardButton("🛃 Таможня", callback_data="menu:customs"), InlineKeyboardButton("💰 Инвойс", callback_data="menu:invoice")],
        [InlineKeyboardButton("🎨 Утиль", callback_data="menu:psd_util"), InlineKeyboardButton("📝 БРИФ", callback_data="menu:psd_brief")],
        [InlineKeyboardButton("🚗 Карвертикал", callback_data="menu:psd_cv"), InlineKeyboardButton("📱 QR Чек", callback_data="menu:qr")],
        [InlineKeyboardButton("📘 Сервисная книжка", callback_data="menu:service"), InlineKeyboardButton("🔵 Видео-кружок", callback_data="menu:video_note")],
        [InlineKeyboardButton("🚛 На автовозе", callback_data="menu:transporter"), InlineKeyboardButton("🛂 ИИ-Таможня", callback_data="menu:customs_ai")],
        [InlineKeyboardButton("📸 Отзыв", callback_data="menu:review"), InlineKeyboardButton("🖼 Пустая рамка", callback_data="menu:empty_plate")],
        [InlineKeyboardButton("🆔 Блюр номеров", callback_data="menu:blur_video"), InlineKeyboardButton("🎙 ИИ-Озвучка", callback_data="menu:voiceover")],
        [InlineKeyboardButton("🎟 Эл. Очередь (Талон)", callback_data="menu:queue"), InlineKeyboardButton("🏆 Мой Профиль", callback_data="menu:profile")]
    ]
    if admin: btns.append([InlineKeyboardButton("⚙️ Админка", callback_data="menu:admin")])
    return InlineKeyboardMarkup(btns)

def companies_keyboard(companies: dict) -> InlineKeyboardMarkup:
    rows, row = [], []
    for cid, cfg in companies.items():
        row.append(InlineKeyboardButton(text=cfg.get("name", cid), callback_data=f"company:{cid}"))
        if len(row) == 3: rows.append(row); row = []
    if row: rows.append(row)
    rows.append([InlineKeyboardButton("⬅️ Назад", callback_data="menu:back")])
    return InlineKeyboardMarkup(rows or [[InlineKeyboardButton("⬅️ Назад", callback_data="menu:back")]])

def customs_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Полный пакет (4 дока)", callback_data="customs:full")], 
        [InlineKeyboardButton("📦 Пакет (3 дока)", callback_data="customs:pack3")],
        [InlineKeyboardButton("🧮 Только Расчет (Бенякони)", callback_data="customs:calc")], 
        [InlineKeyboardButton("⬅️ Назад", callback_data="menu:back")]
    ])

def invoice_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Сделать всё (14 строк)", callback_data="inv:all")],
        [InlineKeyboardButton("🔴 Красный инвойс (14 строк)", callback_data="inv:red")],
        [InlineKeyboardButton("📊 Табличка (9 строк)", callback_data="inv:table")],
        [InlineKeyboardButton("📝 Выписка (8 строк)", callback_data="inv:statement")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="menu:back")]
    ])

def bank_menu_kb() -> InlineKeyboardMarkup:
    btns = [
        [InlineKeyboardButton("🏦 АЛЬФА", callback_data="bank:alfa"), InlineKeyboardButton("🏦 СБЕР", callback_data="bank:sber")],
        [InlineKeyboardButton("🏦 ВТБ", callback_data="bank:vtb"), InlineKeyboardButton("🏦 Т-БАНК", callback_data="bank:tbank")],
        [InlineKeyboardButton("🏦 РАЙФФАЙЗЕН", callback_data="bank:raiff"), InlineKeyboardButton("🏦 ГПБ", callback_data="bank:gpb")],
        [InlineKeyboardButton("🏦 ПСБ", callback_data="bank:psb"), InlineKeyboardButton("🏦 РСХБ", callback_data="bank:rshb")],
        [InlineKeyboardButton("🏦 РУС. СТАНДАРТ", callback_data="bank:rsb"), InlineKeyboardButton("🏦 УРАЛСИБ", callback_data="bank:uralsib")],
        [InlineKeyboardButton("🏦 ФОРА БАНК", callback_data="bank:fora"), InlineKeyboardButton("🏦 ОЗОН", callback_data="bank:ozon")],
        [InlineKeyboardButton("🏦 ОТП БАНК", callback_data="bank:otp"), InlineKeyboardButton("🏦 СОЛИДАРНОСТЬ", callback_data="bank:solid")]
    ]
    dynamic = []
    for bid, data in load_banks().items():
        dynamic.append(InlineKeyboardButton(f"🏦 {data['name']}", callback_data=f"bank:{bid}"))
    for i in range(0, len(dynamic), 2):
        btns.append(dynamic[i:i+2])
    btns.append([InlineKeyboardButton("⬅️ Назад", callback_data="menu:invoice")])
    return InlineKeyboardMarkup(btns)

def kb_back(to): return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data=to)]])
def success_kb(to): return InlineKeyboardMarkup([[InlineKeyboardButton("✏️ Исправить", callback_data="edit_last"), InlineKeyboardButton("⬅️ В меню", callback_data=to)]])

async def send_log(context, user, title, content):
    if not LOG_CHAT_ID: return
    try:
        u_link = f"@{user.username}" if user.username else user.full_name
        safe_content = str(content).replace('<', '&lt;').replace('>', '&gt;').replace('&', '&amp;')
        msg = f"📝 <b>{title}</b>\n👤 {u_link} (ID: {user.id})\n\n<pre>{safe_content}</pre>"
        await context.bot.send_message(chat_id=LOG_CHAT_ID, text=msg, parse_mode=ParseMode.HTML)
    except Exception as e: 
        logger.error(f"❌ ОШИБКА ОТПРАВКИ ЛОГОВ В КАНАЛ: {e}")

async def start(u, c):
    uid = u.effective_user.id
    if not is_allowed(uid): await u.message.reply_text("⛔ Доступ закрыт."); return ConversationHandler.END
    # Add persistent reply keyboard
    reply_kb = ReplyKeyboardMarkup([["Меню"]], resize_keyboard=True)
    await u.message.reply_text("👋 Привет! Добро пожаловать.", reply_markup=reply_kb)
    await u.message.reply_text("Выберите раздел:", reply_markup=kb_main(is_admin(uid)))
    return TOP_MENU

async def handle_text_menu_button(u, c):
    uid = u.effective_user.id
    await u.message.reply_text("Главное меню:", reply_markup=kb_main(is_admin(uid)))
    return TOP_MENU

async def menu_handler(u, c):
    q = u.callback_query; await q.answer()
    data = q.data; uid = u.effective_user.id
    admin = is_admin(uid)

    if data == "menu:back":
        try:
            await q.edit_message_text("Главное меню:", reply_markup=kb_main(admin))
        except Exception:
            pass
        return TOP_MENU

    if data == "menu:profile":
        stats = load_stats()
        user_data = stats.get(str(uid), {"docs": 0, "achievements": []})
        rank = get_rank(user_data["docs"])
        docs = user_data["docs"]
        achs = user_data["achievements"]
        
        msg = f"👤 <b>ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ</b>\n\n"
        msg += f"🏅 <b>Ранг:</b> {rank}\n"
        msg += f"📂 <b>Документов сделано:</b> {docs}\n\n"
        
        if achs:
            msg += "🏆 <b>Твои Достижения:</b>\n"
            for ach_id in achs:
                if ach_id in ACHIEVEMENTS:
                    a = ACHIEVEMENTS[ach_id]
                    msg += f"{a['icon']} <b>{a['name']}</b> — <i>{a['desc']}</i>\n"
        else:
            msg += "🏆 <b>Достижения:</b> <i>Пока пусто. Сделай свой первый документ!</i>"
            
        await q.edit_message_text(msg, parse_mode=ParseMode.HTML, reply_markup=kb_back("menu:back"))
        return TOP_MENU

    if data == "menu:contracts":
        c.user_data["mode"] = "contract"
        await q.edit_message_text("Выберите компанию:", reply_markup=companies_keyboard(load_companies()))
        return CHOOSING_COMPANY
    
    if data == "menu:dover":
        c.user_data["mode"] = "dover"
        kb = []
        for cid, cfg in load_companies().items():
            kb.append([InlineKeyboardButton(f"🏢 {cfg['name']}", callback_data=f"company:{cid}")])
        for did, cfg in load_dovers().items():
            kb.append([InlineKeyboardButton(f"✍️ {cfg['name']}", callback_data=f"dover:{did}")])
        kb.append([InlineKeyboardButton("⬅️ Назад", callback_data="menu:back")])
        await q.edit_message_text("Выберите компанию или отдельную доверенность:", reply_markup=InlineKeyboardMarkup(kb))
        return CHOOSING_COMPANY

    if data == "menu:customs":
        await q.edit_message_text("🛃 Таможня:", reply_markup=customs_menu_kb()); return CHOOSING_CUSTOMS_DOC
    
    if data == "menu:invoice":
        await q.edit_message_text("💰 Инвойсы:", reply_markup=invoice_menu_kb()); return CHOOSING_INVOICE_DOC

    if data == "menu:service":
        msg = (
            "📲 *Данные для Сервисной книжки (5 строк):*\n\n"
            "1. Марка и модель (Volkswagen Multivan)\n"
            "2. VIN код\n"
            "3. Дата регистрации (12.04.2020)\n"
            "4. Текущий пробег (89314)\n"
            "5. Дата последнего ТО (10.01.2026)"
        )
        await q.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=kb_back("menu:back"))
        return WAITING_SERVICE_DATA

    if data.startswith("menu:psd_"):
        mode = data.split("_")[1]
        c.user_data["psd_mode"] = mode
        
        if mode == "util":
            msg = ("🎨 *Утиль*\nСкопируйте шаблон:\n\n"
                   "ИНН : \nКПП : \nОГРН : \nДата Расчета : \nКомпания : \nНомер Лида : \n"
                   "Фамилия : \nИмя : \nОтчество : \nСумма Утиля : \nВин код машины : \n"
                   "Марка : \nМодель : \nГод выпуска : \nОбъем см3 : \nПолная масса : \n"
                   "Номер паспорта : \nДата выдачи : ")
        elif mode == "brief":
            msg = ("📝 *БРИФ*\nСкопируйте шаблон:\n\n"
                   "Год выпуска: \nМарка, модель: \nVIN: \nТип кузова: \nЦвет: \n"
                   "Объём двигателя (см³): \nТип двигателя: \nКПП: \nКВт: \nРазмер шин: ")
        elif mode == "cv":
            msg = ("🚗 *Карвертикал*\nСкопируйте шаблон:\n\n"
                   "Марка, модель: \nДата Генерации : \nДата действия : \nГод выпуска: \nПробег: \n"
                   "Цена мин в  $ : \nЦена средняя в $ : \nЦена высокая в $ : \nОбъём двигателя (см³): \nКоличество цилиндров : \n"
                   "Цвет : \nКПП: \nТип топлива: \nПривод: \nМощность: \nТип кузова: \n"
                   "Количество дверей : \nVIN: ")
            
        await q.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=kb_back("menu:back"))
        return WAITING_PSD_DATA
    
    if data == "menu:qr":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🇷🇺 РУБ", callback_data="qr_cur:RUB"), InlineKeyboardButton("🇧🇾 BYN", callback_data="qr_cur:BYN")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="menu:back")]
        ])
        await q.edit_message_text("Выберите валюту для чека:", reply_markup=kb)
        return CHOOSING_QR_CURRENCY
    
    if data == "menu:admin":
        if not admin:
            await q.answer("Доступ запрещен", show_alert=True)
            return TOP_MENU
            
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Добавить компанию", callback_data="admin:add_company")],
            [InlineKeyboardButton("➕ Добавить Выписку", callback_data="admin:add_bank"), InlineKeyboardButton("➕ Добавить Доверенность", callback_data="admin:add_dover2")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="menu:back")]
        ])
        await q.edit_message_text("⚙️ Панель администратора:", reply_markup=kb)
        return ADMIN_MENU
    
    if data == "menu:transporter": return await handle_transporter_mode(u, c)
    if data == "menu:customs_ai": return await handle_customs_mode(u, c)
    if data == "menu:empty_plate": return await handle_empty_plate_mode(u, c)
    if data == "menu:blur_video": return await handle_video_blur_mode(u, c)
    if data == "menu:video_note": return await handle_video_note_mode(u, c)
    if data == "menu:review": return await handle_create_review(u, c)
    if data == "menu:voiceover": return await handle_voiceover_mode(u, c)
    if data == "menu:queue":
        msg = ("🎟 *Электронная очередь (Талон)*\nВведите 5 (или 6) строк:\n\n"
               "1. ВРЕМЯ (например 13:40)\n"
               "2. ВРЕМЯ ВЗЯТИЯ ТАЛОНА (например 01.10.2025 15:21)\n"
               "3. МАРКА\n"
               "4. МОДЕЛЬ\n"
               "5. ВИН КОД\n"
               "6. ФИО водителя (необязательно)")
        await q.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=kb_back("menu:back"))
        return WAITING_QUEUE_DATA

    await q.edit_message_text("Раздел в разработке.", reply_markup=kb_main(admin)); return TOP_MENU

async def handle_edit(u, c):
    q = u.callback_query; await q.answer()
    last = c.user_data.get("last_input_text")
    if not last: await q.edit_message_text("Нет данных.", reply_markup=kb_main(False)); return TOP_MENU
    await q.edit_message_text(f"✏️ <b>Исправьте:</b>\n<pre>{last}</pre>", parse_mode=ParseMode.HTML, reply_markup=kb_back("menu:back"))
    return c.user_data.get("last_state", TOP_MENU)

async def handle_company_choice(u, c):
    q = u.callback_query; await q.answer()
    if q.data == "menu:back": return await menu_handler(u,c)
    
    if q.data.startswith("dover:"):
        did = q.data.split(":")[1]; cfg = load_dovers().get(did)
        if not cfg: await q.edit_message_text("Не найдена", reply_markup=kb_back("menu:dover")); return CHOOSING_COMPANY
        c.user_data["company_cfg"] = cfg
        msg = (f"✍️ *Доверенность {cfg['name']}*\n"
               f"Введите 4 строки:\n\n"
               f"1. ФИО / Кому доверяют\n"
               f"2. Номер паспорта\n"
               f"3. Кем выдан паспорт\n"
               f"4. Дата выдачи паспорта")
        await q.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=kb_back("menu:dover")); return WAITING_DOVER_DATA

    cid = q.data.split(":")[1]; cfg = load_companies().get(cid)
    if not cfg: await q.edit_message_text("Не найдена компания", reply_markup=kb_back("menu:contracts")); return CHOOSING_COMPANY
    
    c.user_data["company_cfg"] = cfg
    mode = c.user_data.get("mode")
    
    if mode == "contract":
        qs = cfg.get("questions", []); lines = [f"{i+1}. {x.get('label')}" for i, x in enumerate(qs)]
        await q.edit_message_text(f"📄 *{cfg['name']}*\nВведите ответы:\n\n" + "\n".join(lines), parse_mode=ParseMode.MARKDOWN, reply_markup=kb_back("company:back")); return WAITING_ANSWERS
    else:
        msg = (f"✍️ *Доверенность {cfg['name']}*\n"
               f"Введите 4 строки:\n\n"
               f"1. ФИО / Кому доверяют\n"
               f"2. Номер паспорта\n"
               f"3. Кем выдан паспорт\n"
               f"4. Дата выдачи паспорта")
        await q.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=kb_back("company:back")); return WAITING_DOVER_DATA

async def receive_answers(u, c):
    cfg = c.user_data.get("company_cfg")
    c.user_data["last_input_text"] = u.message.text
    c.user_data["last_state"] = WAITING_ANSWERS
    answers = (u.message.text or "").split("\n")
    qs = cfg.get("questions", [])
    
    if len(answers) != len(qs): 
        await u.message.reply_text(f"Нужно {len(qs)} строк.", reply_markup=kb_back("menu:contracts")); return WAITING_ANSWERS
    
    await send_log(c, u.effective_user, f"📄 Создан договор: {cfg['name']}", u.message.text)
    
    ctx = {q.get("key"): a.strip() for q, a in zip(qs, answers)}
    out = get_client_path(answers[0].strip())
    
    cnt_file = COMPANIES_DIR / cfg["id"] / "counter.txt"
    try: num = int(cnt_file.read_text("utf-8").strip())
    except: num = 120
    num += 1; cnt_file.write_text(str(num), "utf-8")
    ctx["contract_number"] = str(num)
    
    await u.message.chat.send_action(ChatAction.UPLOAD_DOCUMENT)
    try:
        d, p = render_doc(cfg["template_path"], ctx, str(out), f"Doc_{cfg['name']}_{datetime.now().strftime('%H%M%S')}")
        with open(d, "rb") as f: await u.message.reply_document(f)
        if p and Path(p).exists(): 
            with open(p, "rb") as f: await u.message.reply_document(f)
        await track_and_check(c, u.effective_user, "contract", u.message.text)
        await u.message.reply_text("✅ Готово!", reply_markup=success_kb("menu:contracts"))
    except Exception as e: await u.message.reply_text(f"Err: {e}")
    return CHOOSING_COMPANY

async def receive_dover_data(u, c):
    cfg = c.user_data.get("company_cfg")
    c.user_data["last_input_text"] = u.message.text; c.user_data["last_state"] = WAITING_DOVER_DATA
    lines = u.message.text.split("\n")
    if len(lines) < 4: await u.message.reply_text("Нужно 4 строки!", reply_markup=kb_back("company:back")); return WAITING_DOVER_DATA
    
    await send_log(c, u.effective_user, f"✍️ Создана доверенность: {cfg['name']}", u.message.text)

    ctx = {"var1":lines[0],"var2":lines[1],"var3":lines[2],"var4":lines[3]}
    out = get_client_path(lines[0].strip())
    await u.message.chat.send_action(ChatAction.UPLOAD_DOCUMENT)
    try:
        d, _ = render_doc(cfg["dover_path"], ctx, str(out), f"Dover_{datetime.now().strftime('%H%M')}")
        with open(d, "rb") as f: await u.message.reply_document(f)
        await track_and_check(c, u.effective_user, "dover", u.message.text)
        await u.message.reply_text("✅ Готово!", reply_markup=success_kb("menu:dover"))
    except Exception as e: await u.message.reply_text(f"Err: {e}")
    return CHOOSING_COMPANY

async def handle_customs_choice(u, c):
    q = u.callback_query; await q.answer()
    if q.data == "menu:back": return await menu_handler(u,c)
    target = q.data.split(":")[1]
    c.user_data["customs_target"] = target
    
    if target == "full":
        msg = (
            "🚀 *Полный пакет (4 документа):*\n"
            "Введите 25 строк (авто-перевод для ДКП + Евро):\n"
            "(Цены в RUB, бот сам переведет)\n\n"
            "1. ФИО плательщика\n"
            "2. Марка и модель\n"
            "3. VIN\n"
            "4. Стоимость авто (RUB)\n"
            "5. Растаможка ОБЩАЯ (RUB)\n"
            "6. Сбор BYN (120)\n"
            "7. Склад BYN (200)\n"
            "8. ЭПТС BYN (70)\n"
            "9. Дата расчета (для Бенякони)\n"
            "10. Возраст (строка: 3-5 лет)\n"
            "11. Адрес\n"
            "12. Паспорт (серия/номер)\n"
            "13. Кем выдан\n"
            "14. Дата выдачи\n"
            "15. Дата ТПО\n"
            "16. Год выпуска (число)\n"
            "17. Объем (число см³)\n"
            "18. Дата ДКП\n"
            "19. Компания\n"
            "20. Цвет\n"
            "21. Мощность\n"
            "22. Топливо\n"
            "23. Трансмиссия\n"
            "24. Мест\n"
            "25. Пробег"
        )
    elif target == "pack3":
        msg = (
            "📦 *Пакет (3 документа):*\n"
            "Введите 21 строку:\n\n"
            "1. ФИО\n"
            "2. Марка и модель\n"
            "3. VIN\n"
            "4. Пошлина (RUB)\n"
            "5. Дата\n"
            "6. Адрес\n"
            "7. Паспорт (серия/номер)\n"
            "8. Кем выдан\n"
            "9. Дата выдачи\n"
            "10. Дата ТПО\n"
            "11. Год выпуска\n"
            "12. Объем двигателя\n"
            "13. Стоимость авто (RUB)\n"
            "14. Дата ДКП\n"
            "15. Компания\n"
            "16. Цвет\n"
            "17. Мощность\n"
            "18. Топливо\n"
            "19. Трансмиссия\n"
            "20. Мест\n"
            "21. Пробег"
        )
    elif target == "calc":
        msg = (
            "🧮 *Только Расчет (Бенякони):*\n"
            "Введите 11 строк:\n\n"
            "1. Имя клиента (для названия папки)\n"
            "2. Дата расчета\n"
            "3. Тип двигателя (Бензин / Дизель)\n"
            "4. Объем двигателя (см³)\n"
            "5. Год выпуска\n"
            "6. Возраст транспорта (например, 3-5 лет)\n"
            "7. Стоимость авто (RUB)\n"
            "8. Пошлина (RUB)\n"
            "9. Сбор BYN (120)\n"
            "10. Склад BYN (200)\n"
            "11. ЭПТС BYN (70)"
        )
        
    await q.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=kb_back("menu:customs"))
    return WAITING_NEW_CUSTOMS_DATA

async def receive_new_customs_data(u, c):
    c.user_data["last_input_text"] = u.message.text; c.user_data["last_state"] = WAITING_NEW_CUSTOMS_DATA
    target = c.user_data.get("customs_target") 
    lines = (u.message.text or "").split("\n")

    def clean_float(text, fld):
        clean = re.sub(r"[^0-9.]", "", text.strip().replace(" ", "").replace(",", "."))
        try: return float(clean)
        except: raise ValueError(f"Ошибка в поле {fld}")

    calc_ctx = {}; doc_ctx = {}; client_name = "Client"; tasks = []

    try:
        if target == "calc":
            if len(lines) < 11: raise ValueError("Мало строк (нужно 11)")
            p_rub = clean_float(lines[6], "Цена"); d_rub = clean_float(lines[7], "Пошлина")
            sbor = clean_float(lines[8], "Сбор"); sklad = clean_float(lines[9], "Склад"); epts = clean_float(lines[10], "ЭПТС")
            p_eur = p_rub / RUB_TO_EUR_RATE; d_eur = d_rub / RUB_TO_EUR_RATE
            tot_eur = p_eur + d_eur; tot_byn = tot_eur * BYN_TO_EUR_RATE
            customs_byn = d_eur * BYN_TO_EUR_RATE
            calc_ctx = {
                "var1": lines[1].strip(), 
                "var2": f"{lines[2].strip()}, {lines[3].strip()} см3 / {lines[5].strip()}",
                "var3": f"{p_eur:.2f}", "var4": f"{d_eur:.2f}", "var5": f"{sbor:.2f}", 
                "var6": f"{sklad:.2f}", "var7": f"{epts:.2f}", "var8": f"{tot_eur:.2f}", 
                "var9": f"{tot_byn:.2f}", "var10": str(BYN_TO_EUR_RATE),
                "var11": f"{d_rub - 150:.2f}", 
                "var12": f"{d_eur - 150:.2f}",
                "var13": f"{customs_byn - 150:.2f}",
                "calc_engine_type": lines[2].strip(),
                "calc_engine_vol": lines[3].strip(),  
                "calc_year": lines[4].strip(),        
                "calc_age": lines[5].strip()          
            }
            client_name = lines[0].strip(); tasks = ["calc"]

        elif target == "pack3":
            if len(lines) < 21: raise ValueError("Мало строк (нужно 21)")
            raw = {
                "full_name": lines[0], "car_model": lines[1], "vin_code": lines[2], "customs_rub": lines[3],
                "data": lines[4], "address": lines[5], "passport_number": lines[6], "passport_issued_by": lines[7],
                "passport_issued_date": lines[8], "tpo_date": lines[9], "car_release_year": lines[10],
                "engine_volume": lines[11], "price_rub": lines[12], "date": lines[13], "company_name": lines[14],
                "car_color": lines[15], "engine_power_hp": lines[16], "fuel_type": lines[17],
                "transmission": lines[18], "seats_number": lines[19], "mileage": lines[20]
            }
            p_eur = clean_float(raw["price_rub"], "Цена") / RUB_TO_EUR_RATE
            d_rub = clean_float(raw["customs_rub"], "Пошлина")
            d_eur = d_rub / RUB_TO_EUR_RATE
            customs_byn = d_eur * BYN_TO_EUR_RATE
            
            raw.update({
                "price_eur": f"{p_eur:.2f}", 
                "customs_eur_clean": f"{d_eur:.2f}",
                "customs_byn": f"{customs_byn:.2f}",
                "customs_minus_150_rub": f"{d_rub - 150:.2f}", 
                "customs_minus_150_eur": f"{d_eur - 150:.2f}", 
                "customs_minus_150_byn": f"{customs_byn - 150:.2f}" 
            })
            doc_ctx = raw; client_name = lines[0].strip(); tasks = ["tpo", "kvit", "dkp"]

        elif target == "full":
            if len(lines) < 25: raise ValueError("Мало строк (нужно 25)")
            p_rub = clean_float(lines[3], "Цена"); d_rub = clean_float(lines[4], "Пошлина")
            sbor = clean_float(lines[5], "Сбор"); sklad = clean_float(lines[6], "Склад"); epts = clean_float(lines[7], "ЭПТС")
            p_eur = p_rub / RUB_TO_EUR_RATE; d_eur = d_rub / RUB_TO_EUR_RATE
            exp_eur = (sbor + sklad + epts) / BYN_TO_EUR_RATE; clean_d = d_eur - exp_eur
            tot_eur = p_eur + d_eur; tot_byn = tot_eur * BYN_TO_EUR_RATE
            customs_byn = d_eur * BYN_TO_EUR_RATE
            
            calc_ctx = {
                "var1": lines[8].strip(),
                "var2": f"{lines[21].strip()}, {lines[16].strip()} см3 / {lines[9].strip()}",
                "var3": f"{p_eur:.2f}", "var4": f"{d_eur:.2f}", "var5": f"{sbor:.2f}", 
                "var6": f"{sklad:.2f}", "var7": f"{epts:.2f}", "var8": f"{tot_eur:.2f}", 
                "var9": f"{tot_byn:.2f}", "var10": str(BYN_TO_EUR_RATE),
                "var11": f"{d_rub - 150:.2f}", 
                "var12": f"{d_eur - 150:.2f}",
                "var13": f"{customs_byn - 150:.2f}",
                "calc_engine_type": lines[21].strip(), 
                "calc_engine_vol": lines[16].strip(),  
                "calc_year": lines[15].strip(),        
                "calc_age": lines[9].strip()           
            }
            doc_ctx = {
                "full_name": lines[0].strip(), "car_model": lines[1].strip(), "vin_code": lines[2].strip(),
                "price_eur": f"{p_eur:.2f}", "customs_eur_clean": f"{clean_d:.2f}", 
                "customs_byn": f"{customs_byn:.2f}",
                "customs_minus_150_rub": f"{d_rub - 150:.2f}",
                "customs_minus_150_eur": f"{d_eur - 150:.2f}",
                "customs_minus_150_byn": f"{customs_byn - 150:.2f}",
                "address": lines[10].strip(),
                "passport_number": lines[11].strip(), "passport_issued_by": lines[12].strip(),
                "passport_issued_date": lines[13].strip(), "tpo_date": lines[14].strip(),
                "car_release_year": lines[15].strip(), "engine_volume": lines[16].strip(),
                "date": lines[17].strip(), "company_name": lines[18].strip(), "car_color": lines[19].strip(),
                "engine_power_hp": lines[20].strip(), "fuel_type": lines[21].strip(),
                "transmission": lines[22].strip(), "seats_number": lines[23].strip(), "mileage": lines[24].strip()
            }
            client_name = lines[0].strip(); tasks = ["calc", "tpo", "kvit", "dkp"]

    except ValueError as e: await u.message.reply_text(str(e), reply_markup=kb_back("menu:customs")); return WAITING_NEW_CUSTOMS_DATA
    except Exception as e: await u.message.reply_text(f"Err: {e}", reply_markup=kb_back("menu:customs")); return WAITING_NEW_CUSTOMS_DATA

    await send_log(c, u.effective_user, f"🛃 Создана Таможня: {target}", u.message.text)

    out = get_client_path(client_name)
    now = datetime.now()
    await u.message.chat.send_action(ChatAction.UPLOAD_DOCUMENT)

    color_map = {'серый':'Grau', 'серебристый':'Silber', 'белый':'Weiss', 'черный':'Schwarz', 'чёрный':'Schwarz', 'красный':'Rot', 'синий':'Blau', 'зеленый':'Grün', 'зелёный':'Grün', 'коричневый':'Braun', 'желтый':'Gelb'}
    eng_map = {'бензин':'Benzin', 'дизель':'Diesel', 'электро':'Elektro', 'гибрид':'Hybrid', 'плагин-гибрид':'Plug-in Hybrid'}
    trans_map = {'автоматическая':'Automatik', 'автомат':'Automatik', 'акпп':'Automatik', 'механическая':'Schaltgetriebe', 'механика':'Schaltgetriebe', 'мкпп':'Schaltgetriebe'}

    name_parts = lines[0].strip().split()
    if len(name_parts) >= 3: short_name = f"{name_parts[0]} {name_parts[1][0]}.{name_parts[2][0]}."
    elif len(name_parts) == 2: short_name = f"{name_parts[0]} {name_parts[1][0]}."
    else: short_name = lines[0].strip()

    for task in tasks:
        cur_ctx = doc_ctx
        if task == "dkp":
            cur_ctx = doc_ctx.copy()
            if "car_color" in cur_ctx: cur_ctx["car_color"] = color_map.get(cur_ctx["car_color"].strip().lower(), cur_ctx["car_color"]).capitalize()
            if "fuel_type" in cur_ctx: cur_ctx["fuel_type"] = eng_map.get(cur_ctx["fuel_type"].strip().lower(), cur_ctx["fuel_type"].capitalize())
            if "transmission" in cur_ctx: cur_ctx["transmission"] = trans_map.get(cur_ctx["transmission"].strip().lower(), cur_ctx["transmission"]).capitalize()
            if "address" in cur_ctx: cur_ctx["address_de"] = translit_to_german(cur_ctx["address"])
            if "company_name" in cur_ctx: cur_ctx["company_name"] = translit_to_german(cur_ctx["company_name"])
            if "full_name" in cur_ctx: cur_ctx["full_name_de"] = translit_to_german(cur_ctx["full_name"])
            if "price_eur" in cur_ctx:
                base_eur = float(cur_ctx["price_eur"].replace(" ", ""))
                cur_ctx["commission_eur"] = f"{DKP_COMMISSION:.2f}"
                cur_ctx["total_eur"] = f"{base_eur + DKP_COMMISSION:.2f}"
            if "engine_power_hp" in cur_ctx:
                try: cur_ctx["power_kw"] = str(int(clean_float(cur_ctx["engine_power_hp"],"") / 1.36))
                except: cur_ctx["power_kw"] = cur_ctx["engine_power_hp"]
        elif task == "calc": 
            cur_ctx = calc_ctx

        try:
            fname = f"ДКП-{short_name}" if task == "dkp" else (f"CALC_{now.strftime('%H%M')}" if task == "calc" else f"{task.upper()}_{now.strftime('%H%M')}")
            tmpl = CALC_TEMPLATES_DIR/"calc.docx" if task == "calc" else CUSTOMS_TEMPLATES_DIR/f"{task}.docx"
            p = out / f"{fname}.docx"
            render_doc(str(tmpl), cur_ctx, str(out), fname)
            
            if task == "dkp":
                pdf_path = out / f"{fname}.pdf"
                try:
                    from docx2pdf import convert
                    convert(str(p), str(pdf_path)) 
                    with open(p, "rb") as f_docx, open(pdf_path, "rb") as f_pdf:
                        await u.message.reply_document(f_docx)
                        await u.message.reply_document(f_pdf)
                except Exception as e:
                    with open(p, "rb") as f: await u.message.reply_document(f)
            else:
                with open(p, "rb") as f: await u.message.reply_document(f)
                
        except Exception as e: print(f"Err gen {task}: {e}")

    await track_and_check(c, u.effective_user, f"customs_{target}", u.message.text)
    await u.message.reply_text(f"✅ Готово! Архив: {client_name}", reply_markup=success_kb("menu:customs"))
    return CHOOSING_CUSTOMS_DOC

async def handle_invoice_choice(u, c):
    q = u.callback_query; await q.answer()
    if q.data == "menu:back": return await menu_handler(u,c)
    target = q.data.split(":")[1]
    c.user_data["invoice_target"] = target
    
    if target in ["statement", "all"]:
        await q.edit_message_text("🏦 Выберите банк для выписки:", reply_markup=bank_menu_kb())
        return CHOOSING_BANK
        
    elif target == "table":
        msg = (
            "📊 *Табличка (9 строк)*\n"
            "Введите 9 строк:\n\n"
            "1. ФИО получателя\n"
            "2. ИНН получателя\n"
            "3. Банк получателя\n"
            "4. ИНН банка\n"
            "5. КПП банка\n"
            "6. БИК банка\n"
            "7. Корр. счет\n"
            "8. Счет получателя\n"
            "9. Сумма (числом)"
        )
    elif target == "red":
        msg = (
            "🔴 *Красный инвойс*\n"
            "Введите 14 строк:\n\n"
            "1. Получатель\n"
            "2. Банк получателя\n"
            "3. ИНН\n"
            "4. КПП\n"
            "5. ИНН банка\n"
            "6. БИК\n"
            "7. Корр. счет\n"
            "8. Счет получателя\n"
            "9. Номер инвойса\n"
            "10. Дата инвойса\n"
            "11. ФИО Заказчика (для архива)\n"
            "12. Номер договора\n"
            "13. Дата договора\n"
            "14. Итоговая сумма (числом)"
        )
        
    await q.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=kb_back("menu:invoice"))
    return WAITING_INVOICE_DATA

async def handle_bank_choice(u, c):
    q = u.callback_query; await q.answer()
    bank = q.data.split(":")[1]
    c.user_data["selected_bank"] = bank
    target = c.user_data.get("invoice_target")
    
    if target == "statement":
        msg = (
            f"📝 *Выписка ({bank.upper()}) - 8 строк*\n"
            "Введите 8 строк:\n\n"
            "1. ФИО получателя\n"
            "2. ИНН\n"
            "3. КПП\n"
            "4. ИНН банка\n"
            "5. БИК банка\n"
            "6. Корреспондентский счет\n"
            "7. Счет получателя\n"
            "8. Дата выписки"
        )
    elif target == "all":
        msg = (
            f"🚀 *Сделать всё ({bank.upper()}) - 14 строк*\n"
            "Введите 14 строк:\n\n"
            "1. Получатель\n"
            "2. Банк получателя\n"
            "3. ИНН\n"
            "4. КПП\n"
            "5. ИНН банка\n"
            "6. БИК\n"
            "7. Корр. счет\n"
            "8. Счет получателя\n"
            "9. Номер инвойса\n"
            "10. Дата инвойса\n"
            "11. ФИО Заказчика (для архива)\n"
            "12. Номер договора\n"
            "13. Дата договора\n"
            "14. Итоговая сумма (числом)"
        )
        
    await q.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=kb_back("menu:invoice"))
    return WAITING_INVOICE_DATA

async def receive_invoice_data(u, c):
    import calendar 
    
    c.user_data["last_input_text"] = u.message.text; c.user_data["last_state"] = WAITING_INVOICE_DATA
    target = c.user_data.get("invoice_target")
    bank = c.user_data.get("selected_bank", "alfa")
    lines = [l.strip() for l in (u.message.text or "").split("\n")]
    client_name = "Unk"

    tasks_to_run = []
    
    bank_files = {
        "alfa": "alfa.docx", "sber": "sber.docx", "vtb": "vtb.docx", "tbank": "tbank.docx",
        "raiff": "raiff.docx", "gpb": "gpb.docx", "psb": "psb.docx", "rshb": "rshb.docx",
        "rsb": "rsb.docx", "uralsib": "uralsib.docx", "fora": "fora.docx", "ozon": "ozon.docx",
        "otp": "otp.docx", "solid": "solid.docx"
    }
    stmt_filename = bank_files.get(bank, "alfa.docx")

    def get_next_month(date_str):
        try:
            dt = datetime.strptime(date_str.strip(), "%d.%m.%Y")
            new_month = dt.month + 1
            new_year = dt.year
            if new_month > 12:
                new_month = 1; new_year += 1
            new_day = min(dt.day, calendar.monthrange(new_year, new_month)[1])
            return dt.replace(year=new_year, month=new_month, day=new_day).strftime("%d.%m.%Y")
        except:
            return date_str

    if target == "statement":
        if len(lines) < 8: 
            await u.message.reply_text("Надо 8 строк", reply_markup=kb_back("menu:invoice"))
            return WAITING_INVOICE_DATA
        date_next_month = get_next_month(lines[7]) 
        ctx = {"var1":lines[0], "var3":lines[1], "var4":lines[2], "var15":lines[3], "var5":lines[4], "var6":lines[5], "var7":lines[6], "var9":lines[7], "var16": date_next_month}
        client_name = lines[0]
        acc = lines[6].strip(); acc_last4 = acc[-4:] if len(acc) >= 4 else acc
        date_fmt = lines[7].strip().replace(".", "_").replace("/", "_")
        stmt_name = f"Общая_информация_по_счёту_№40817_{acc_last4}_на_{date_fmt}"
        tasks_to_run.append((stmt_filename, stmt_name, ctx))

    elif target == "table":
        if len(lines) < 9: 
            await u.message.reply_text("Надо 9 строк", reply_markup=kb_back("menu:invoice"))
            return WAITING_INVOICE_DATA
        ctx = {"var2":lines[0],"var3":lines[1],"var4":lines[2],"var5":lines[3],"var6":lines[4],"var7":lines[5],"var8":lines[6],"var9":lines[7],"var13":lines[8]}
        client_name = lines[0]
        table_name = f"Инвойс_{random.randint(1000, 9999)}"
        tasks_to_run.append(("invoice_table.docx", table_name, ctx))

    elif target in ["all", "red"]:
        if len(lines) < 14: 
            await u.message.reply_text("Надо 14 строк", reply_markup=kb_back("menu:invoice"))
            return WAITING_INVOICE_DATA
        client_name = lines[10] 
        date_next_month = get_next_month(lines[9]) 
        ctx_red = {"var1": lines[0], "var2": lines[1], "var3": lines[2], "var4": lines[3], "var15": lines[4], "var5": lines[5], "var6": lines[6], "var7": lines[7], "var8": lines[8], "var9": lines[9], "var10": lines[10], "var11": lines[11], "var12": lines[12], "var13": lines[13], "var16": date_next_month}
        tasks_to_run.append(("invoice_red.docx", "Red", ctx_red))

        if target == "all":
            ctx_table = {"var2": lines[0], "var3": lines[2], "var4": lines[1], "var5": lines[4], "var6": lines[3], "var7": lines[5], "var8": lines[6], "var9": lines[7], "var13": lines[13]}
            table_name = f"Инвойс_{random.randint(1000, 9999)}"
            tasks_to_run.append(("invoice_table.docx", table_name, ctx_table))
            ctx_stmt = {"var1": lines[0], "var3": lines[2], "var4": lines[3], "var15": lines[4], "var5": lines[5], "var6": lines[6], "var7": lines[7], "var9": lines[9], "var16": date_next_month}
            acc = lines[7].strip(); acc_last4 = acc[-4:] if len(acc) >= 4 else acc
            date_fmt = lines[9].strip().replace(".", "_").replace("/", "_") 
            stmt_name = f"Общая_информация_по_счёту_№40817_{acc_last4}_на_{date_fmt}"
            tasks_to_run.append((stmt_filename, stmt_name, ctx_stmt))

    await send_log(c, u.effective_user, f"💰 Создан Инвойс: {target}", u.message.text)

    out = get_client_path(client_name); now = datetime.now()
    await u.message.chat.send_action(ChatAction.UPLOAD_DOCUMENT)
    
    for name, pref, ctx in tasks_to_run:
        if "var13" in ctx and num2words:
            try: ctx["var14"] = num2words(float(ctx["var13"].replace(" ","").replace(",",".")), lang='ru', to='currency', currency='RUB').capitalize()
            except: ctx["var14"] = ctx["var13"]

        tmpl = INVOICE_TEMPLATES_DIR / name
        if tmpl.exists():
            if pref.startswith("Общая_информация_по_счёту") or pref.startswith("Инвойс_"):
                fpath = out / f"{pref}.docx"
            else:
                fpath = out / f"{pref}_{now.strftime('%H%M')}.docx"
                
            render_doc(str(tmpl), ctx, str(out), fpath.stem)
            
            if pref.startswith("Общая_информация_по_счёту") or pref.startswith("Инвойс_"):
                pdf_path = out / f"{fpath.stem}.pdf"
                try:
                    from docx2pdf import convert
                    convert(str(fpath), str(pdf_path))
                    with open(fpath, "rb") as f_docx, open(pdf_path, "rb") as f_pdf:
                        await u.message.reply_document(f_docx)
                        await u.message.reply_document(f_pdf)
                except Exception as e:
                    with open(fpath, "rb") as f_docx: await u.message.reply_document(f_docx)
            else:
                with open(fpath, "rb") as f: await u.message.reply_document(f)
            
    await track_and_check(c, u.effective_user, f"invoice_{target}", u.message.text)
    await u.message.reply_text("✅ Готово!", reply_markup=success_kb("menu:invoice"))
    return CHOOSING_INVOICE_DOC

def parse_regex(pattern, text):
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(1).strip() if m else ""

async def receive_psd_data(u, c):
    text = u.message.text
    mode = c.user_data.get("psd_mode", "util")
    data = {}
    js_code = ""
    psd_link = ""

    if mode == "util":
        keys = {'инн':'inn','кпп':'kpp','огрн':'ogrn','дата расчета':'calc_date','компания':'company','номер лида':'lead_id','фамилия':'surname','имя':'name','отчество':'patronymic','сумма утиля':'util_sum','вин':'vin','марка':'brand','модель':'model','год':'year','объем':'vol','масса':'mass','номер паспорта':'passport_num','дата выдачи':'passport_date'}
        for line in text.split('\n'):
            if ':' in line:
                k, v = line.split(':', 1)
                for rus, eng in keys.items():
                    if rus in k.strip().lower(): data[eng] = v.strip()
        js_code = generate_util_script(data)
        psd_link = URL_UTIL

    elif mode == "brief":
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        if not any(":" in line for line in lines) and len(lines) >= 10:
            data['year'] = lines[0]; brand_model = lines[1]; data['vin'] = lines[2].upper()
            body_raw = lines[3].strip().lower(); color_raw = lines[4].strip().lower()
            data['engine_cc'] = re.sub(r'[^0-9]', '', lines[5].split('(')[0])
            eng_raw = lines[6].strip().lower(); trans_raw = lines[7].strip().lower()
            data['power_kw'] = re.sub(r'[^0-9]', '', lines[8])
            data['rim'] = re.sub(r'[^0-9]', '', lines[9])
        else:
            data['year'] = parse_regex(r'Год выпуска:\s*(.*)', text); brand_model = parse_regex(r'Марка, модель:\s*(.*)', text)
            data['vin'] = parse_regex(r'VIN:\s*(.*)', text).upper(); body_raw = parse_regex(r'Тип кузова:\s*(.*)', text).strip().lower()
            color_raw = parse_regex(r'Цвет:\s*(.*)', text).strip().lower()
            data['engine_cc'] = parse_regex(r'Объём двигателя.*?:\s*(.*)', text)
            eng_raw = parse_regex(r'Тип двигателя:\s*(.*)', text).strip().lower()
            trans_raw = parse_regex(r'КПП:\s*(.*)', text).strip().lower()
            data['power_kw'] = parse_regex(r'КВт:\s*(.*)', text)
            data['rim'] = parse_regex(r'Размер шин:\s*(.*)', text).replace('R','').replace('r','')

        parts = brand_model.split(' ', 1)
        data['brand'] = parts[0] if parts else ""
        data['model'] = parts[1] if len(parts)>1 else ""
        
        body_map = {'кроссовер':'GELÄNDEWAGEN', 'внедорожник':'GELÄNDEWAGEN', 'седан':'LIMOUSINE', 'универсал':'KOMBI', 'хэтчбек':'SCHRÄGHECK', 'минивэн':'VAN', 'купе':'COUPE'}
        color_map = {'серый':'GRAU', 'темно-серый':'GRAU', 'тёмно-серый':'GRAU', 'светло-серый':'SILBER', 'серебристый':'SILBER', 'белый':'WEISS', 'черный':'SCHWARZ', 'чёрный':'SCHWARZ', 'красный':'ROT', 'синий':'BLAU', 'зеленый':'GRÜN', 'зелёный':'GRÜN', 'коричневый':'BRAUN', 'желтый':'GELB'}
        eng_map = {'бензин':'BENZIN', 'дизель':'DIESEL', 'электро':'ELEKTRO', 'гибрид':'HYBRID', 'плагин-гибрид':'PLUG-IN HYBRID'}
        trans_map = {'автоматическая':'AUTOMATIK', 'автомат':'AUTOMATIK', 'акпп':'AUTOMATIK', 'механическая':'SCHALTGETRIEBE', 'механика':'SCHALTGETRIEBE', 'мкпп':'SCHALTGETRIEBE'}

        data['body'] = body_map.get(body_raw, body_raw).upper()
        data['color'] = color_map.get(color_raw, color_raw).upper()
        data['engine_type'] = eng_map.get(eng_raw, eng_raw).upper()
        data['transmission'] = trans_map.get(trans_raw, trans_raw).upper()
        
        js_code = generate_brief_script(data)
        psd_link = URL_BRIEF

    elif mode == "cv":
        data['car_name'] = parse_regex(r'Марка, модель:\s*(.*)', text)
        data['date_gen'] = parse_regex(r'Дата Генерации\s*:\s*(.*)', text); data['date_valid'] = parse_regex(r'Дата действия\s*:\s*(.*)', text)
        data['year'] = parse_regex(r'Год выпуска:\s*(.*)', text); data['mileage'] = parse_regex(r'Пробег:\s*(.*)', text)
        prices = re.findall(r'Цена.*?:\s*(.*)', text, re.IGNORECASE)
        data['price_low'] = prices[0].strip() if len(prices) > 0 else ""
        data['price_avg'] = prices[1].strip() if len(prices) > 1 else ""
        data['price_high'] = prices[2].strip() if len(prices) > 2 else ""
        data['engine_vol'] = parse_regex(r'Объём двигателя.*?:\s*(.*)', text)
        data['cylinders'] = parse_regex(r'Количество цилиндров\s*:\s*(.*)', text)
        data['color'] = parse_regex(r'Цвет\s*:\s*(.*)', text); data['gearbox'] = parse_regex(r'КПП:\s*(.*)', text)
        data['fuel'] = parse_regex(r'Тип топлива:\s*(.*)', text); data['drive'] = parse_regex(r'Привод:\s*(.*)', text)
        data['power'] = parse_regex(r'Мощность:\s*(.*)', text); data['body'] = parse_regex(r'Тип кузова:\s*(.*)', text)
        data['doors'] = parse_regex(r'Количество дверей\s*:\s*(.*)', text); data['vin'] = parse_regex(r'VIN:\s*(.*)', text)
        js_code = generate_cv_script(data)
        psd_link = URL_CV

    if not data:
        await u.message.reply_text("⚠️ Не удалось распознать данные. Проверьте формат.", reply_markup=kb_back("menu:back"))
        return WAITING_PSD_DATA

    await send_log(c, u.effective_user, f"🎨 Сгенерирован код Photopea: {mode.upper()}", u.message.text)
    await track_and_check(c, u.effective_user, f"psd_{mode}", u.message.text)

    chat_id = str(u.effective_chat.id)
    USER_SCRIPTS[chat_id] = js_code
    USER_SCRIPTS[f"{chat_id}_link"] = psd_link
    
    tool_url = f"{BASE_WEBHOOK_URL}/tools/{chat_id}?ngrok-skip-browser-warning=true"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🛠 ОТКРЫТЬ ПАНЕЛЬ КОПИРОВАНИЯ", url=tool_url)],
                               [InlineKeyboardButton("⬅️ Назад", callback_data="menu:back")]])
    
    msg = (
        "✅ **Скрипт успешно сгенерирован!**\n\n"
        "Нажми кнопку **«ОТКРЫТЬ ПАНЕЛЬ КОПИРОВАНИЯ»**.\n"
        "Она откроет веб-страницу, где ты сможешь скопировать скрипт в один клик и безопасно перейти в Photopea."
    )
    await u.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    return WAITING_PSD_DATA

async def handle_qr_currency(u, c):
    q = u.callback_query; await q.answer()
    if q.data == "menu:back": return await menu_handler(u,c)
    
    c.user_data["qr_currency"] = q.data.split(":")[1]
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Стандарт", callback_data="qr_type:Standart")],
        [InlineKeyboardButton("Утиль", callback_data="qr_type:Util")],
        [InlineKeyboardButton("Залог", callback_data="qr_type:Zalog")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="menu:qr")]
    ])
    await q.edit_message_text("Выберите тип чека:", reply_markup=kb)
    return CHOOSING_QR_TYPE

async def handle_qr_type(u, c):
    q = u.callback_query; await q.answer()
    if q.data == "menu:qr": return await menu_handler(u,c)
    if q.data == "menu:back": return await menu_handler(u,c)
    
    c.user_data["qr_type"] = q.data.split(":")[1]
    
    msg = (
        "📲 *Отправь данные для чека (7 строк):*\n\n"
        "1. Марка и модель (BMW X4)\n"
        "2. ФИО (Иванов Павел Иванович)\n"
        "3. VIN\n"
        "4. Сумма (22584.23)\n"
        "5. Дата (02.02.2026)\n"
        "6. Время (15:12)\n"
        "7. Номер счета (66 13 710349)"
    )
    await q.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=kb_back("menu:qr"))
    return WAITING_QR_DATA

async def receive_qr_data(u, c):
    lines = [line.strip() for line in (u.message.text or "").split('\n') if line.strip()]
    if len(lines) < 7:
        await u.message.reply_text("Нужно 7 строк! Проверь формат.", reply_markup=kb_back("menu:qr"))
        return WAITING_QR_DATA

    currency = c.user_data.get("qr_currency", "RUB")
    qr_type = c.user_data.get("qr_type", "Standart")
    
    await u.message.chat.send_action(ChatAction.UPLOAD_DOCUMENT)
    
    try:
        amount_str = lines[3]; amount_text = amount_str 
        
        if num2words:
            try:
                clean_amount = float(amount_str.replace(" ", "").replace(",", "."))
                amount_text = num2words(clean_amount, lang='ru', to='currency', currency='RUB').capitalize()
                if currency == "BYN": amount_text = amount_text.replace("рублей", "белорусских рублей").replace("рубль", "белорусский рубль").replace("рубля", "белорусских рубля")
            except Exception as e: logger.error(f"Ошибка конвертации суммы: {e}")

        html_data = {
            "CAR": lines[0], "NAME": lines[1], "VIN": lines[2],
            "AMOUNT": f"{lines[3]} {currency}", "DATE": lines[4], 
            "TIME": lines[5], "ACCOUNT": lines[6], "AMOUNT_TEXT": amount_text  
        }
        
        type_folders = {"Standart": "Стандартный", "Util": "Утиль", "Zalog": "Залоговый"}
        folder_name = type_folders.get(qr_type, "Стандартный")
        template_folder = PROJECT_DIR / "QR" / currency / folder_name / "HTML tam"
        
        if not template_folder.exists():
            await u.message.reply_text(f"❌ Ошибка: Папка {template_folder} не найдена!", reply_markup=kb_back("menu:back"))
            return WAITING_QR_DATA
            
        site_url = deploy_to_netlify(template_folder, html_data)
        docx_ctx = {"var1": lines[0], "var2": lines[1], "var3": lines[2], "var4": f"{lines[3]} {currency}", "var5": lines[4], "var6": lines[5], "var7": lines[6], "var8": amount_text}
        
        client_name = lines[1].strip()
        out_dir = get_client_path(client_name)
        docx_template = BASE_DIR.parent / "templates_qr" / "receipt.docx"
        
        if not docx_template.exists():
            docx_template.parent.mkdir(parents=True, exist_ok=True)
            await u.message.reply_text(f"❌ Создай папку templates_qr и положи туда шаблон receipt.docx", reply_markup=kb_back("menu:back"))
            return WAITING_QR_DATA
        
        generated_docx, _ = render_doc(str(docx_template), docx_ctx, str(out_dir), f"Receipt_{datetime.now().strftime('%H%M')}")
        
        if site_url:
            encoded_url = urllib.parse.quote(str(site_url), safe='')
            qr_api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={encoded_url}"
            qr_image_path = str(out_dir / "qr.png")
            urllib.request.urlretrieve(qr_api_url, qr_image_path)
            
            doc = Document(generated_docx)
            doc.add_picture(qr_image_path, width=Inches(2.0))
            doc.save(generated_docx)
            valid_url = site_url if site_url.startswith("http") else f"https://{site_url}"

        with open(generated_docx, "rb") as f:
            await u.message.reply_document(document=f)
            
        await track_and_check(c, u.effective_user, "qr", u.message.text)
        
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🌐 Посмотреть сайт-чек", url=valid_url)],
            [InlineKeyboardButton("⬅️ В меню", callback_data="menu:back")]
        ])
        await u.message.reply_text("✅ Чек и сайт успешно созданы!", reply_markup=kb)

    except Exception as e:
        await u.message.reply_text(f"❌ Ошибка генерации: {e}", reply_markup=kb_back("menu:back"))
        
    return WAITING_QR_DATA

# === ЛОГИКА СЕРВИСНОЙ КНИЖКИ ===
async def receive_service_data(u, c):
    c.user_data["last_input_text"] = u.message.text; c.user_data["last_state"] = WAITING_SERVICE_DATA

    lines = [l.strip() for l in (u.message.text or "").split('\n') if l.strip()]
    if len(lines) < 5:
        await u.message.reply_text("❌ Нужно 5 строк данных!", reply_markup=kb_back("menu:back"))
        return WAITING_SERVICE_DATA

    car_full, vin, ez, mileage_str, date_str = lines
    parts = car_full.split(' ', 1); brand = parts[0]; model = parts[1] if len(parts) > 1 else ""
    
    try:
        mileage = int(re.sub(r'\D', '', mileage_str))
        current_date = datetime.strptime(date_str, "%d.%m.%Y")
        try: ez_dt = datetime.strptime(ez.strip(), "%d.%m.%Y")
        except ValueError: ez_dt = datetime.strptime(f"01.07.{ez.strip()}", "%d.%m.%Y")
    except Exception as e:
        await u.message.reply_text("❌ Ошибка! Проверь, что пробег — это число, а даты в формате ДД.ММ.ГГГГ", reply_markup=kb_back("menu:back"))
        return WAITING_SERVICE_DATA
    
    oil_spec, oil_visc = OIL_DB.get(brand.lower(), ("VW 504 00", "5W-30"))
    total_days = (current_date - ez_dt).days
    if total_days < 100: total_days = 365 
    
    services_count = max(1, mileage // 12000)
    base_step_days = total_days // services_count
    if base_step_days < 15: base_step_days = 15 

    main_rep_nr = 10
    ctx = {
        "car": car_full, "brand": brand, "model": model, "vin": vin, "ez": ez,
        "last_date": date_str, "last_mileage": f"{mileage:,}".replace(',', ' '),
        "rep_nr": str(main_rep_nr), "order_nr": str(random.randint(830000, 839999)),
        "oil_spec": oil_spec, "oil_visc": oil_visc, "rest_days": str(random.randint(11, 20)), 
        "rest_km": str(random.randint(8300, 8700)), "logo": "{{logo}}"
    }

    temp_mileage = mileage; temp_date = current_date; temp_rep_nr = main_rep_nr

    for i in range(1, 11):
        temp_mileage -= 12000
        prefix = f"d{i}_"
        if temp_mileage < 0:
            for key in ["brand", "model", "rep_nr", "date", "mileage", "order_nr", "oil_spec", "oil_visc", "rest_days", "rest_km", "check_date"]:
                ctx[f"{prefix}{key}"] = " "
            continue

        step = random.randint(int(base_step_days * 0.8), int(base_step_days * 1.2))
        temp_date -= timedelta(days=step)
        if temp_date <= ez_dt: temp_date = ez_dt + timedelta(days=random.randint(10, 30))
        
        temp_rep_nr -= 1
        ctx[f"{prefix}brand"] = brand; ctx[f"{prefix}model"] = model; ctx[f"{prefix}rep_nr"] = str(temp_rep_nr)
        ctx[f"{prefix}date"] = temp_date.strftime("%d.%m.%Y"); ctx[f"{prefix}mileage"] = f"{temp_mileage:,}".replace(',', ' ')
        ctx[f"{prefix}order_nr"] = str(random.randint(830000, 839999)); ctx[f"{prefix}oil_spec"] = oil_spec
        ctx[f"{prefix}oil_visc"] = oil_visc; ctx[f"{prefix}rest_days"] = str(random.randint(11, 20))
        ctx[f"{prefix}rest_km"] = str(random.randint(8300, 8700)); ctx[f"{prefix}check_date"] = temp_date.strftime("%d.%m.%Y")

    await send_log(c, u.effective_user, f"📘 Создана Сервисная книжка: {car_full}", u.message.text)
    
    client_name = brand + "_" + str(random.randint(100, 999))
    out_dir = get_client_path(client_name)
    
    SERVICE_TEMPLATE = PROJECT_DIR / "templates_service" / "service_template.docx"
    if not SERVICE_TEMPLATE.exists():
        SERVICE_TEMPLATE.parent.mkdir(parents=True, exist_ok=True)
        await u.message.reply_text("❌ Нет шаблона service_template.docx в папке templates_service!", reply_markup=kb_back("menu:back"))
        return WAITING_SERVICE_DATA

    await u.message.chat.send_action(ChatAction.UPLOAD_DOCUMENT)
    
    try:
        generated_docx, _ = render_doc(str(SERVICE_TEMPLATE), ctx, str(out_dir), f"Service_{brand}")
        
        doc = Document(generated_docx)
        logo_path = PROJECT_DIR / "brand_logos" / f"{brand.lower()}.png"
        if not logo_path.exists(): logo_path = PROJECT_DIR / "brand_logos" / f"{brand.lower()}.jpg"
            
        def replace_content(doc_obj, context, img_path):
            for p in doc_obj.paragraphs:
                for key, val in context.items():
                    if f"{{{{{key}}}}}" in p.text: p.text = p.text.replace(f"{{{{{key}}}}}", str(val))
                if '{{logo}}' in p.text:
                    p.text = p.text.replace('{{logo}}', '')
                    if img_path and img_path.exists(): p.add_run().add_picture(str(img_path), width=Inches(1.5))
            for table in doc_obj.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for p in cell.paragraphs:
                            for key, val in context.items():
                                if f"{{{{{key}}}}}" in p.text: p.text = p.text.replace(f"{{{{{key}}}}}", str(val))
                            if '{{logo}}' in p.text:
                                p.text = p.text.replace('{{logo}}', '')
                                if img_path and img_path.exists(): p.add_run().add_picture(str(img_path), width=Inches(1.2))

        replace_content(doc, ctx, logo_path)
        doc.save(generated_docx)

        with open(generated_docx, "rb") as f:
            await u.message.reply_document(document=f)
            
        await track_and_check(c, u.effective_user, "service", u.message.text)
        await u.message.reply_text("✅ Сервисная книжка с историей готова!", reply_markup=success_kb("menu:back"))
            
    except Exception as e:
        await u.message.reply_text(f"❌ Ошибка генерации: {e}", reply_markup=kb_back("menu:back"))

    return WAITING_SERVICE_DATA

async def admin_callback(u, c):
    q = u.callback_query; await q.answer()
    if q.data == "admin:add_company":
        await q.edit_message_text("Введи ID (название папки) новой компании на английском:", reply_markup=kb_back("menu:admin"))
        return ADMIN_ADD_ID
    if q.data == "admin:add_bank":
        await q.edit_message_text("Введи ID (название файла, англ) для нового банка выписки:", reply_markup=kb_back("menu:admin"))
        return ADMIN_ADD_BANK_ID
    if q.data == "admin:add_dover2":
        await q.edit_message_text("Введи ID (название файла, англ) для новой доверенности:", reply_markup=kb_back("menu:admin"))
        return ADMIN_ADD_DOVER2_ID
    return ADMIN_MENU

async def admin_receive_id(u, c):
    c.user_data['new_comp_id'] = u.message.text.strip()
    await u.message.reply_text("Введи отображаемое ИМЯ компании:")
    return ADMIN_ADD_NAME

async def admin_receive_name(u, c):
    c.user_data['new_comp_name'] = u.message.text.strip()
    await u.message.reply_text("Отправь файл шаблона ДОГОВОРА (строго в формате .docx):")
    return ADMIN_ADD_TEMPLATE

async def admin_receive_template(u, c):
    doc = u.message.document
    if not doc or not doc.file_name.endswith('.docx'):
        await u.message.reply_text("❌ Ошибка! Отправь файл .docx")
        return ADMIN_ADD_TEMPLATE
    
    c.user_data['new_comp_template'] = doc.file_id
    await u.message.reply_text("Отправь файл шаблона ДОВЕРЕННОСТИ (dover.docx) или напиши /skip")
    return ADMIN_ADD_DOVER

async def admin_receive_dover(u, c):
    if u.message.text == '/skip':
        c.user_data['new_comp_dover'] = None
    else:
        doc = u.message.document
        if not doc or not doc.file_name.endswith('.docx'):
            await u.message.reply_text("❌ Ошибка! Отправь .docx файл или напиши /skip")
            return ADMIN_ADD_DOVER
        c.user_data['new_comp_dover'] = doc.file_id

    msg = ("Отправь список ВОПРОСОВ для бота.\nКаждый вопрос с новой строки.")
    await u.message.reply_text(msg)
    return ADMIN_ADD_QUESTIONS

async def admin_receive_questions(u, c):
    questions_text = u.message.text.strip().split('\n')
    questions_list = [{"key": f"var{i+1}", "label": q.strip()} for i, q in enumerate(questions_text) if q.strip()]
    
    comp_id = c.user_data['new_comp_id']
    comp_name = c.user_data['new_comp_name']
    
    comp_dir = COMPANIES_DIR / comp_id
    comp_dir.mkdir(parents=True, exist_ok=True)
    
    tmpl_file = await c.bot.get_file(c.user_data['new_comp_template'])
    await tmpl_file.download_to_drive(comp_dir / "template.docx")
    
    if c.user_data.get('new_comp_dover'):
        dover_file = await c.bot.get_file(c.user_data['new_comp_dover'])
        await dover_file.download_to_drive(comp_dir / "dover.docx")
        
    (comp_dir / "counter.txt").write_text("1", "utf-8")
    
    meta = {"id": comp_id, "name": comp_name, "questions": questions_list}
    (comp_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=4), "utf-8")
    
    await u.message.reply_text(f"✅ Компания *{comp_name}* успешно добавлена в базу!", parse_mode=ParseMode.MARKDOWN, reply_markup=kb_main(is_admin(u.effective_user.id)))
    return TOP_MENU

async def admin_receive_bank_id(u, c):
    c.user_data['new_bank_id'] = u.message.text.strip()
    await u.message.reply_text("Введи отображаемое ИМЯ банка:")
    return ADMIN_ADD_BANK_NAME

async def admin_receive_bank_name(u, c):
    c.user_data['new_bank_name'] = u.message.text.strip()
    await u.message.reply_text("Отправь файл шаблона ВЫПИСКИ (строго в формате .docx):")
    return ADMIN_ADD_BANK_TEMPLATE

async def admin_receive_bank_template(u, c):
    doc = u.message.document
    if not doc or not doc.file_name.endswith('.docx'):
        await u.message.reply_text("❌ Ошибка! Отправь файл .docx")
        return ADMIN_ADD_BANK_TEMPLATE
    bank_dir = BANKS_DIR / c.user_data['new_bank_id']
    bank_dir.mkdir(parents=True, exist_ok=True)
    tmpl_file = await c.bot.get_file(doc.file_id)
    await tmpl_file.download_to_drive(bank_dir / "statement.docx")
    meta = {"id": c.user_data['new_bank_id'], "name": c.user_data['new_bank_name']}
    (bank_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=4), "utf-8")
    await u.message.reply_text(f"✅ Банк выписки *{c.user_data['new_bank_name']}* успешно добавлен!", parse_mode=ParseMode.MARKDOWN, reply_markup=kb_main(is_admin(u.effective_user.id)))
    return TOP_MENU

async def admin_receive_dover2_id(u, c):
    c.user_data['new_dov_id'] = u.message.text.strip()
    await u.message.reply_text("Введи отображаемое ИМЯ доверенности:")
    return ADMIN_ADD_DOVER2_NAME

async def admin_receive_dover2_name(u, c):
    c.user_data['new_dov_name'] = u.message.text.strip()
    await u.message.reply_text("Отправь файл шаблона ДОВЕРЕННОСТИ (строго в формате .docx):")
    return ADMIN_ADD_DOVER2_TEMPLATE

async def admin_receive_dover2_template(u, c):
    doc = u.message.document
    if not doc or not doc.file_name.endswith('.docx'):
        await u.message.reply_text("❌ Ошибка! Отправь файл .docx")
        return ADMIN_ADD_DOVER2_TEMPLATE
    dov_dir = DOVERS_DIR / c.user_data['new_dov_id']
    dov_dir.mkdir(parents=True, exist_ok=True)
    tmpl_file = await c.bot.get_file(doc.file_id)
    await tmpl_file.download_to_drive(dov_dir / "dover.docx")
    meta = {"id": c.user_data['new_dov_id'], "name": c.user_data['new_dov_name']}
    (dov_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=4), "utf-8")
    await u.message.reply_text(f"✅ Доверенность *{c.user_data['new_dov_name']}* успешно добавлена!", parse_mode=ParseMode.MARKDOWN, reply_markup=kb_main(is_admin(u.effective_user.id)))
    return TOP_MENU


@flask_app.route('/webhook/<chat_id>', methods=['POST'])
def webhook(chat_id):
    logger.info(f"📥 WEBHOOK для ID: {chat_id}")
    raw = request.stream.read()
    if len(raw) < 2000: return "Err", 400
    
    image_bytes = raw[2000:]
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                      data={'chat_id': chat_id, 'caption': '✅ Документ готов!'},
                      files={'photo': ('res.jpg', image_bytes)},
                      timeout=30)
    except Exception as e: logger.error(f"❌ Telegram Error: {e}")
    
    resp = jsonify({"script": "app.activeDocument.close();"})
    resp.headers.add("Access-Control-Allow-Origin", "*")
    return resp

@flask_app.route('/webapp/<path:filename>')
def serve_webapp_file(filename):
    return send_file(PROJECT_DIR / "bot" / "webapp" / filename)

@flask_app.route('/webapp')
@flask_app.route('/webapp/')
def serve_webapp_index():
    return send_file(PROJECT_DIR / "bot" / "webapp" / "index.html")

@flask_app.route('/upload', methods=['POST'])
def handle_upload():
    if 'video' not in request.files:
        return jsonify({'status': 'error', 'message': 'No video file'})
    file = request.files['video']
    user_id = request.form.get('user_id')
    bg_type = request.form.get('bg_type', 'standard')
    
    if file and user_id:
        import os
        os.makedirs("temp", exist_ok=True)
        temp_path = f"temp/webapp_{user_id}_{file.filename}"
        file.save(temp_path)
        
        def process_video_task():
            import asyncio
            from services.media_api import make_video_note
            result = asyncio.run(make_video_note(temp_path, bg_type))
            if result and os.path.exists(result):
                with open(result, 'rb') as f:
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideoNote",
                                  data={'chat_id': user_id}, files={'video_note': f}, timeout=120)
                os.remove(result)
            else:
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                              data={'chat_id': user_id, 'text': '❌ Ошибка при создании кружка.'})
            if os.path.exists(temp_path): os.remove(temp_path)
            
        import threading
        threading.Thread(target=process_video_task).start()
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                     data={'chat_id': user_id, 'text': 'Видео получено через WebApp! Открывать окно больше не нужно, кружок скоро придет сюда... ⏳'})
        return jsonify({'status': 'ok'})
    return jsonify({'status': 'error', 'message': 'Missing data'})

async def receive_queue_data(u, c):
    import random, urllib.parse, qrcode, io
    c.user_data["last_input_text"] = u.message.text; c.user_data["last_state"] = WAITING_QUEUE_DATA
    lines = [x.strip() for x in u.message.text.split("\n") if x.strip()]
    if len(lines) < 5:
        await u.message.reply_text("❌ Нужно минимум 5 строк!", reply_markup=kb_back("menu:back"))
        return WAITING_QUEUE_DATA
    time_str, reg_time, brand, model, vin = lines[:5]
    fio = lines[5] if len(lines) > 5 else ""
    qnum = random.randint(1, 50); bnum = qnum - 1 if qnum > 1 else 0
    params = urllib.parse.urlencode({'queue_num': qnum, 'before_num': bnum, 'time': time_str, 'registered_time': reg_time, 'brand': brand, 'model': model, 'vin_code': vin, 'fio': fio})
    msg_wait = await u.message.reply_text("⏳ *Генерация талона...*\nПодготавливаю вебсайт и DOCX с QR-кодом...", parse_mode=ParseMode.MARKDOWN)
    try:
        base_url = deploy_to_netlify(QUEUE_TEMPLATES_DIR / "webapp_template", {})
        final_url = (base_url + "/" if not base_url.endswith("/") else base_url) + "?" + params
        qr = qrcode.make(final_url, border=1); buf = io.BytesIO(); qr.save(buf, format='PNG'); buf.seek(0)
        ctx = {"queue_num": str(qnum), "before_num": str(bnum), "time": time_str, "registered_time": reg_time, "brand": brand, "model": model, "vin_code": vin, "fio": fio}
        output_dir = get_client_path(brand)
        d, _ = render_doc(str(QUEUE_TEMPLATES_DIR / "template.docx"), ctx, str(output_dir), f"Talon_{brand}_{model}_{datetime.now().strftime('%H%M%S')}", images={"qr_image": {"stream": buf, "width_mm": 45}})
        await c.bot.delete_message(chat_id=u.effective_chat.id, message_id=msg_wait.message_id)
        
        safe_url = final_url.replace('&', '&amp;')
        cap = f"✅ <b>Ваш талон готов!</b>\n\nЭлектронная ссылка на сайт:\n<a href='{safe_url}'>Открыть талон в браузере</a>\n\nПолная ссылка:\n<code>{safe_url}</code>"
        
        with open(d, "rb") as f: 
            await u.message.reply_document(f, caption=cap, parse_mode=ParseMode.HTML)
            
        await send_log(c, u.effective_user, f"🎟 Очередь: {brand} {model}", final_url)
        await track_and_check(c, u.effective_user, "queue", u.message.text)
        await u.message.reply_text("✅ Выполнено!", reply_markup=success_kb("menu:back"))
    except Exception as e:
        await u.message.reply_text(f"❌ Ошибка: {e}")
    return TOP_MENU

def run_flask(): flask_app.run(port=8000, use_reloader=False)

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    
    app = ApplicationBuilder().token(BOT_TOKEN).read_timeout(30).write_timeout(30).build()
    load_whitelist_store()
    
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(menu_handler, pattern=r"^menu:")],
        states={
            TOP_MENU: [CallbackQueryHandler(menu_handler, pattern=r"^menu:")],
            CHOOSING_COMPANY: [CallbackQueryHandler(handle_company_choice, pattern="^(company|dover):"), CallbackQueryHandler(menu_handler, pattern=r"^menu:")],
            WAITING_ANSWERS: [MessageHandler(filters.TEXT, receive_answers), CallbackQueryHandler(menu_handler, pattern=r"^menu:")],
            WAITING_DOVER_DATA: [MessageHandler(filters.TEXT, receive_dover_data), CallbackQueryHandler(menu_handler, pattern=r"^menu:")],
            CHOOSING_CUSTOMS_DOC: [CallbackQueryHandler(handle_customs_choice, pattern="^customs:"), CallbackQueryHandler(menu_handler, pattern=r"^menu:")],
            WAITING_NEW_CUSTOMS_DATA: [MessageHandler(filters.TEXT, receive_new_customs_data), CallbackQueryHandler(menu_handler, pattern=r"^menu:")],
            WAITING_QUEUE_DATA: [MessageHandler(filters.TEXT, receive_queue_data), CallbackQueryHandler(menu_handler, pattern=r"^menu:")],
            CHOOSING_INVOICE_DOC: [CallbackQueryHandler(handle_invoice_choice, pattern="^inv:"), CallbackQueryHandler(menu_handler, pattern=r"^menu:")],
            WAITING_INVOICE_DATA: [MessageHandler(filters.TEXT, receive_invoice_data), CallbackQueryHandler(menu_handler, pattern=r"^menu:")],
            WAITING_PSD_DATA: [MessageHandler(filters.TEXT, receive_psd_data), CallbackQueryHandler(menu_handler, pattern=r"^menu:")],
            CHOOSING_QR_CURRENCY: [CallbackQueryHandler(handle_qr_currency, pattern="^qr_cur:"), CallbackQueryHandler(menu_handler, pattern=r"^menu:")],
            CHOOSING_QR_TYPE: [CallbackQueryHandler(handle_qr_type, pattern="^qr_type:"), CallbackQueryHandler(menu_handler, pattern=r"^menu:")],
            WAITING_QR_DATA: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_qr_data), CallbackQueryHandler(menu_handler, pattern=r"^menu:")],
            WAITING_SERVICE_DATA: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_service_data), CallbackQueryHandler(menu_handler, pattern=r"^menu:")],
            CHOOSING_BANK: [CallbackQueryHandler(handle_bank_choice, pattern=r"^bank:"), CallbackQueryHandler(menu_handler, pattern=r"^menu:")],
            ADMIN_MENU: [CallbackQueryHandler(admin_callback, pattern=r"^admin:"), CallbackQueryHandler(menu_handler, pattern=r"^menu:")], 
            ADMIN_ADD_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_receive_id)],
            ADMIN_ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_receive_name)],
            ADMIN_ADD_TEMPLATE: [MessageHandler(filters.Document.ALL, admin_receive_template)],
            ADMIN_ADD_DOVER: [MessageHandler(filters.Document.ALL | filters.TEXT, admin_receive_dover)],
            ADMIN_ADD_QUESTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_receive_questions)],
            ADMIN_ADD_BANK_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_receive_bank_id)],
            ADMIN_ADD_BANK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_receive_bank_name)],
            ADMIN_ADD_BANK_TEMPLATE: [MessageHandler(filters.Document.ALL, admin_receive_bank_template)],
            ADMIN_ADD_DOVER2_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_receive_dover2_id)],
            ADMIN_ADD_DOVER2_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_receive_dover2_name)],
            ADMIN_ADD_DOVER2_TEMPLATE: [MessageHandler(filters.Document.ALL, admin_receive_dover2_template)],
            WAITING_MEDIA_PHOTO: [MessageHandler(filters.PHOTO | filters.Document.ALL | filters.VIDEO, receive_media_photo), CallbackQueryHandler(menu_handler, pattern=r"^menu:")],
            WAITING_MEDIA_VIDEO_NOTE: [MessageHandler(filters.VIDEO | filters.Document.ALL, receive_video_note), CallbackQueryHandler(menu_handler, pattern=r"^menu:")],
            WAITING_REVIEW_SEASON: [CallbackQueryHandler(handle_review_season, pattern=r"^rev_s:"), CallbackQueryHandler(menu_handler, pattern=r"^menu:")],
            WAITING_REVIEW_WEATHER: [CallbackQueryHandler(handle_review_weather, pattern=r"^rev_w:"), CallbackQueryHandler(menu_handler, pattern=r"^menu:")],
            WAITING_REVIEW_PERSON: [CallbackQueryHandler(handle_review_person, pattern=r"^rev_p:"), CallbackQueryHandler(menu_handler, pattern=r"^menu:")],
            WAITING_REVIEW_LOCATION: [CallbackQueryHandler(handle_review_location, pattern=r"^rev_l:"), CallbackQueryHandler(menu_handler, pattern=r"^menu:")],
            WAITING_REVIEW_PHOTO: [MessageHandler(filters.PHOTO | filters.Document.ALL, receive_review_photo), CallbackQueryHandler(menu_handler, pattern=r"^menu:")],
            WAITING_VOICE_SELECTION: [CallbackQueryHandler(handle_voice_selection, pattern=r"^voice:"), CallbackQueryHandler(menu_handler, pattern=r"^menu:")],
            WAITING_VOICE_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_voice_text), CallbackQueryHandler(menu_handler, pattern=r"^menu:")],
            WAITING_VOICE_STABILITY: [CallbackQueryHandler(handle_voice_stability, pattern=r"^stab:"), CallbackQueryHandler(menu_handler, pattern=r"^menu:")],
            WAITING_VOICE_DELAY: [CallbackQueryHandler(handle_voice_delay, pattern=r"^delay:"), CallbackQueryHandler(menu_handler, pattern=r"^menu:")],
            WAITING_VOICE_VIDEO: [MessageHandler(filters.VIDEO | filters.Document.ALL, receive_voice_video), CallbackQueryHandler(menu_handler, pattern=r"^menu:")],
        },
        fallbacks=[
            MessageHandler(filters.Regex("^(Меню|Главное меню|/start|start)$"), handle_text_menu_button),
            CallbackQueryHandler(menu_handler, pattern=r"^menu:"),
            CallbackQueryHandler(handle_edit, pattern=r"^edit_last"),
            CallbackQueryHandler(handle_media_regen, pattern=r"^media_regen:"),
            CallbackQueryHandler(handle_voice_regen, pattern=r"^voice_regen:")
        ],
        allow_reentry=True
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    
    print("BOT STARTED SUCCESSFULLY! Waiting for commands...")
    app.run_polling()

if __name__ == "__main__":
    main()