import os
import random
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaVideo, WebAppInfo
from telegram.constants import ParseMode, ChatAction
from telegram.ext import ContextTypes

from services.media_api import generate_image, process_blurit_video, make_video_note
from modules.media_prompts import (
    PROMPT_TRANSPORTER, TRANSPORTER_ANGLES, PROMPT_CUSTOMS, PROMPT_EMPTY_PLATE,
    BASE_STYLE, REVIEW_PEOPLE, REVIEW_CLOTHES, REVIEW_POSES, REVIEW_LOCATIONS
)
from config import BOT_TOKEN, ELEVENLABS_API_KEY, WEBAPP_URL
import httpx

logger = logging.getLogger(__name__)

(
    WAITING_MEDIA_PHOTO, WAITING_MEDIA_VIDEO_NOTE, 
    WAITING_VOICE_SELECTION, WAITING_VOICE_TEXT, WAITING_VOICE_STABILITY, WAITING_VOICE_DELAY, WAITING_VOICE_VIDEO,
    WAITING_REVIEW_SEASON, WAITING_REVIEW_WEATHER, WAITING_REVIEW_PERSON, WAITING_REVIEW_LOCATION, WAITING_REVIEW_PHOTO
) = range(20, 32)


async def kb_back(callback_data="menu:back"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data=callback_data)]])

# ---- Media Handlers ----

async def handle_transporter_mode(u: Update, c: ContextTypes.DEFAULT_TYPE):
    c.user_data['media_mode'] = 'transporter'
    await u.callback_query.edit_message_text("Режим: Автовоз (генерация 1 фото). Отправьте фото машины.", reply_markup=await kb_back())
    return WAITING_MEDIA_PHOTO

async def handle_empty_plate_mode(u: Update, c: ContextTypes.DEFAULT_TYPE):
    c.user_data['media_mode'] = 'empty_plate'
    await u.callback_query.edit_message_text("Режим: Пустая рамка. Отправьте фото машины, и я заменю номер на пустую пластиковую рамку.", reply_markup=await kb_back())
    return WAITING_MEDIA_PHOTO

async def handle_customs_mode(u: Update, c: ContextTypes.DEFAULT_TYPE):
    c.user_data['media_mode'] = 'customs'
    await u.callback_query.edit_message_text("Режим: Таможня (генерация 1 фото). Отправьте фото машины.", reply_markup=await kb_back())
    return WAITING_MEDIA_PHOTO

async def handle_video_blur_mode(u: Update, c: ContextTypes.DEFAULT_TYPE):
    c.user_data['media_mode'] = 'blur_video'
    await u.callback_query.edit_message_text("Режим: Блюр номеров. Отправьте видео машины (размер до 20 МБ).", reply_markup=await kb_back())
    return WAITING_MEDIA_PHOTO

async def handle_video_note_mode(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await u.callback_query.edit_message_text("Отправь мне видео (до 60 секунд), и я превращу его в круглый видео-кружок. 🔵", reply_markup=await kb_back())
    return WAITING_MEDIA_VIDEO_NOTE

async def receive_media_photo(u: Update, c: ContextTypes.DEFAULT_TYPE):
    mode = c.user_data.get('media_mode')
    if not mode:
        await u.message.reply_text("Режим не выбран.", reply_markup=await kb_back())
        return WAITING_MEDIA_PHOTO

    if mode == 'blur_video':
        if not u.message.video:
            await u.message.reply_text("Пожалуйста, отправьте видео для замазывания номеров.")
            return WAITING_MEDIA_PHOTO
            
        if u.message.video.file_size > 20 * 1024 * 1024:
            await u.message.reply_text("❌ Видео слишком большое! Максимум 20 МБ.")
            return WAITING_MEDIA_PHOTO

        wait_msg = await u.message.reply_text("Скачиваю видео и отправляю в Blurit. Идет обработка... ⏳")
        os.makedirs("temp", exist_ok=True)
        temp_file = f"temp/{u.message.video.file_id}.mp4"
        
        try:
            file = await c.bot.get_file(u.message.video.file_id)
            await file.download_to_drive(temp_file)
            result_path = await process_blurit_video(temp_file)
            
            if result_path and os.path.exists(result_path):
                with open(result_path, "rb") as f:
                    await u.message.reply_video(f, caption="✅ Номера замазаны!")
                from main import track_and_check
                await track_and_check(c, u.effective_user, "media_blur", "")
                os.remove(result_path)
            else:
                await wait_msg.edit_text("❌ Произошла ошибка при обработке видео.")
        finally:
            if os.path.exists(temp_file): os.remove(temp_file)
        return -1 # Return to Main Menu or predefined fallback

    else:
        # Photo rendering modes
        photo = u.message.photo[-1] if u.message.photo else None
        document = u.message.document
        
        file_id = None
        if photo: file_id = photo.file_id
        elif document and document.mime_type.startswith('image/'): file_id = document.file_id
        
        if not file_id:
            await u.message.reply_text("Пожалуйста, отправьте изображение.")
            return WAITING_MEDIA_PHOTO
            
        c.user_data['last_file_id'] = file_id
        c.user_data['last_mode'] = mode
        
        await generate_and_send_media(u.message.chat_id, u.effective_user, file_id, mode, c)
        if mode == 'empty_plate':
            return -1
        return WAITING_MEDIA_PHOTO

async def generate_and_send_media(chat_id: int, user, file_id: str, mode: str, c: ContextTypes.DEFAULT_TYPE, regen_strength=0.75):
    try:
        file = await c.bot.get_file(file_id)
        image_url = file.file_path
    except Exception as e:
        logger.error(f"Failed to get file: {e}")
        await c.bot.send_message(chat_id, "❌ Ошибка получения фото.")
        return

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Перегенерировать", callback_data=f"media_regen:{regen_strength}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="menu:back")]
    ])

    if mode == 'transporter':
        await c.bot.send_message(chat_id, "Машина грузится на автовоз... ⏳")
        angle = random.choice(TRANSPORTER_ANGLES)
        result_url = await generate_image(image_url, f"{PROMPT_TRANSPORTER} {angle}", image_strength=regen_strength)
        caption = f"🚛 На автовозе\nРакурс:\n{angle}"
    elif mode == 'empty_plate':
        await c.bot.send_message(chat_id, "Заменяю номер на пустую рамку... ⏳")
        result_url = await generate_image(image_url, PROMPT_EMPTY_PLATE, image_strength=0.75)
        caption = "🔲 Номер заменен на пустую рамку"
    else:
        await c.bot.send_message(chat_id, "Автомобиль на таможне... ⏳")
        result_url = await generate_image(image_url, PROMPT_CUSTOMS, image_strength=regen_strength)
        caption = "🛂 Автомобиль на таможне"

    if result_url:
        await c.bot.send_document(chat_id, document=result_url, filename="result.jpg", caption=caption, reply_markup=markup)
        c.user_data['source_image_url'] = image_url
        from main import track_and_check
        t_map = {'transporter': 'media_transporter', 'empty_plate': 'media_empty', 'customs': 'media_customs'}
        if mode in t_map:
            await track_and_check(c, user, t_map[mode], "")
    else:
        await c.bot.send_message(chat_id, "❌ Возникла ошибка при генерации.")

async def handle_media_regen(u: Update, c: ContextTypes.DEFAULT_TYPE):
    q = u.callback_query; await q.answer()
    strength = float(q.data.split(":")[1])
    
    file_id = c.user_data.get('last_file_id')
    mode = c.user_data.get('last_mode')
    
    if not file_id or not mode:
        await q.edit_message_text("⏳ Данные устарели. Пожалуйста, отправьте фото заново.")
        return WAITING_MEDIA_PHOTO
        
    await c.bot.send_message(u.effective_chat.id, "🔄 Запускаю повторную генерацию...")
    if mode == 'review':
        await generate_and_send_review(u.effective_chat.id, u.effective_user, file_id, c, regen_strength=strength)
        return WAITING_REVIEW_PHOTO
    else:
        await generate_and_send_media(u.effective_chat.id, u.effective_user, file_id, mode, c, regen_strength=strength)
        return WAITING_MEDIA_PHOTO

async def receive_video_note(u: Update, c: ContextTypes.DEFAULT_TYPE):
    video = u.message.video or u.message.document
    if not video or (u.message.document and not u.message.document.mime_type.startswith('video/')):
        await u.message.reply_text("Пожалуйста, отправьте видео файл.")
        return WAITING_MEDIA_VIDEO_NOTE
        
    if video.file_size > 20 * 1024 * 1024:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("Открыть загрузчик (до 150 МБ)", web_app=WebAppInfo(url=f"{WEBAPP_URL}/webapp"))]])
        await u.message.reply_text("Файл слишком большой (>20МБ) для отправки в чат.\nПожалуйста, загрузите его через кнопку ниже:", reply_markup=kb)
        return WAITING_MEDIA_VIDEO_NOTE
        
    wait_msg = await u.message.reply_text("⏳ Нарезаю кружок...")
    os.makedirs("temp", exist_ok=True)
    temp_path = f"temp/to_note_{video.file_id}.mp4"
    
    try:
        file = await c.bot.get_file(video.file_id)
        await file.download_to_drive(temp_path)
        
        note_path = await make_video_note(temp_path)
        if note_path and os.path.exists(note_path):
            with open(note_path, "rb") as f:
                await u.message.reply_video_note(f)
            from main import track_and_check
            await track_and_check(c, u.effective_user, "media_note", "")
            os.remove(note_path)
            await wait_msg.delete()
        else:
            await wait_msg.edit_text("❌ Произошла ошибка при создании кружка.")
    finally:
        if os.path.exists(temp_path): os.remove(temp_path)
    return -1

# ---- Smart Review Generators ----
async def handle_create_review(u: Update, c: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("❄️ Зима", callback_data="rev_s:winter"), InlineKeyboardButton("🌸 Весна", callback_data="rev_s:spring")],
        [InlineKeyboardButton("☀️ Лето", callback_data="rev_s:summer"), InlineKeyboardButton("🍂 Осень", callback_data="rev_s:autumn")]
    ])
    await u.callback_query.edit_message_text("📸 Шаг 1: Выберите время года:", reply_markup=kb)
    return WAITING_REVIEW_SEASON

async def handle_review_season(u: Update, c: ContextTypes.DEFAULT_TYPE):
    q = u.callback_query; await q.answer()
    choice = q.data.split(":")[1]
    maps = {'winter':'winter season', 'spring':'spring season', 'summer':'summer season', 'autumn':'autumn season'}
    c.user_data['review_season'] = maps.get(choice, 'season')
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("☀️ Ясно", callback_data="rev_w:w1"), InlineKeyboardButton("⛅ Облачно", callback_data="rev_w:w2")],
        [InlineKeyboardButton("☁️ Пасмурно", callback_data="rev_w:w3"), InlineKeyboardButton("🌧 Дождь", callback_data="rev_w:w4")],
        [InlineKeyboardButton("🌦 После дождя", callback_data="rev_w:w5"), InlineKeyboardButton("🌫 Туман", callback_data="rev_w:w6")],
        [InlineKeyboardButton("🌅 Рассвет", callback_data="rev_w:w7"), InlineKeyboardButton("🌇 Закат", callback_data="rev_w:w8")],
        [InlineKeyboardButton("🌃 Ночь", callback_data="rev_w:w9"), InlineKeyboardButton("💨 Ветрено", callback_data="rev_w:w10")]
    ])
    await q.edit_message_text("Шаг 2: Выберите погоду:", reply_markup=kb)
    return WAITING_REVIEW_WEATHER

async def handle_review_weather(u: Update, c: ContextTypes.DEFAULT_TYPE):
    q = u.callback_query; await q.answer()
    choice = q.data.split(":")[1]
    maps = {
        'w1':'sunny weather, bright clear sky', 'w2':'partly cloudy sky, pleasant lighting',
        'w3':'overcast, gray cloudy sky, soft diffused lighting', 'w4':'rainy weather, wet roads',
        'w5':'after rain, bright reflections on wet asphalt', 'w6':'dense fog, moody low visibility atmosphere',
        'w7':'golden hour sunrise, early morning atmospheric lighting', 'w8':'golden hour sunset, warm cinematic evening lighting',
        'w9':'night time, illuminated by warm street lights', 'w10':'windy moody weather, dynamic lighting'
    }
    c.user_data['review_weather'] = maps.get(choice, 'weather')
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("👨 Муж 20-30", callback_data="rev_p:man_20"), InlineKeyboardButton("👨 Муж 30-40", callback_data="rev_p:man_30")],
        [InlineKeyboardButton("👨 Муж 40+", callback_data="rev_p:man_40"), InlineKeyboardButton("👩 Дев 20-30", callback_data="rev_p:woman_20")],
        [InlineKeyboardButton("👩 Жен 30-40", callback_data="rev_p:woman_30"), InlineKeyboardButton("👩 Жен 40+", callback_data="rev_p:woman_40")],
        [InlineKeyboardButton("👫 Мол. пара", callback_data="rev_p:couple_young"), InlineKeyboardButton("👫 Взр. пара", callback_data="rev_p:couple_adult")],
        [InlineKeyboardButton("👨‍👩‍👦 Семья", callback_data="rev_p:family_1"), InlineKeyboardButton("👨‍👩‍👧‍👦 Бол. семья", callback_data="rev_p:family_2")],
        [InlineKeyboardButton("🎲 Случайный выбор", callback_data="rev_p:random")]
    ])
    await q.edit_message_text("Шаг 3: Кто будет на фото?", reply_markup=kb)
    return WAITING_REVIEW_PERSON

async def handle_review_person(u: Update, c: ContextTypes.DEFAULT_TYPE):
    q = u.callback_query; await q.answer()
    c.user_data['review_person'] = q.data.split(":")[1]
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏙 Центр", callback_data="rev_l:city_center"), InlineKeyboardButton("🏘 Нов. район", callback_data="rev_l:residential_new")],
        [InlineKeyboardButton("🏡 Ст. дворы", callback_data="rev_l:residential_old"), InlineKeyboardButton("🏭 Промзона", callback_data="rev_l:industrial")],
        [InlineKeyboardButton("🏢 БЦ", callback_data="rev_l:business"), InlineKeyboardButton("🛣 Трасса (лес)", callback_data="rev_l:highway_forest")],
        [InlineKeyboardButton("🏜 Трасса (поле)", callback_data="rev_l:highway_field"), InlineKeyboardButton("⛽ Заправка", callback_data="rev_l:gas_station")],
        [InlineKeyboardButton("🏪 Кафе/Мак", callback_data="rev_l:cafe"), InlineKeyboardButton("🛒 ТЦ", callback_data="rev_l:mall")],
        [InlineKeyboardButton("🅿️ Подземка", callback_data="rev_l:underground"), InlineKeyboardButton("🌲 Парк", callback_data="rev_l:park")],
        [InlineKeyboardButton("🌊 Набережная", callback_data="rev_l:waterfront"), InlineKeyboardButton("🏖 Пляж", callback_data="rev_l:beach")],
        [InlineKeyboardButton("🏔 Горы", callback_data="rev_l:mountain"), InlineKeyboardButton("🏡 Дача", callback_data="rev_l:dacha")],
        [InlineKeyboardButton("🏰 Коттедж", callback_data="rev_l:cottage"), InlineKeyboardButton("🛤 ЖД", callback_data="rev_l:railway")],
        [InlineKeyboardButton("🌉 Мост", callback_data="rev_l:bridge"), InlineKeyboardButton("🏛 Площадь", callback_data="rev_l:square")],
        [InlineKeyboardButton("🎲 Случайная локация", callback_data="rev_l:random")]
    ])
    await q.edit_message_text("Шаг 4: Выберите локацию:", reply_markup=kb)
    return WAITING_REVIEW_LOCATION

async def handle_review_location(u: Update, c: ContextTypes.DEFAULT_TYPE):
    q = u.callback_query; await q.answer()
    c.user_data['review_location'] = q.data.split(":")[1]
    await q.edit_message_text("Шаг 5: Всё готово! 🚗 Отправьте фото машины.")
    return WAITING_REVIEW_PHOTO

async def receive_review_photo(u: Update, c: ContextTypes.DEFAULT_TYPE):
    photo = u.message.photo[-1] if u.message.photo else None
    if not photo:
        await u.message.reply_text("Пожалуйста, отправьте фото.")
        return WAITING_REVIEW_PHOTO
    
    file_id = photo.file_id
    c.user_data['last_file_id'] = file_id
    
    await generate_and_send_review(u.message.chat_id, u.effective_user, file_id, c)
    return WAITING_REVIEW_PHOTO

async def generate_and_send_review(chat_id: int, user, file_id: str, c: ContextTypes.DEFAULT_TYPE, regen_strength=0.8):
    wait_msg = await c.bot.send_message(chat_id, "Генерирую уникальный отзыв, это займет около минуты... ⏳")
    
    season = c.user_data.get('review_season', '')
    weather = c.user_data.get('review_weather', '')
    person = c.user_data.get('review_person', 'random')
    loc = c.user_data.get('review_location', 'random')
    
    p_text = random.choice(REVIEW_PEOPLE[random.choice(list(REVIEW_PEOPLE.keys()))]) if person == 'random' else random.choice(REVIEW_PEOPLE[person])
    l_text = random.choice(REVIEW_LOCATIONS[random.choice(list(REVIEW_LOCATIONS.keys()))]) if loc == 'random' else random.choice(REVIEW_LOCATIONS[loc])
    c_text = random.choice(REVIEW_CLOTHES)
    pose_text = random.choice(REVIEW_POSES)
    
    prompt = f"{BASE_STYLE}, {season}, {weather}, {p_text}, {c_text}, {pose_text}, {l_text}"
    
    try:
        file = await c.bot.get_file(file_id)
        source_url = file.file_path
        c.user_data['source_image_url'] = source_url
        c.user_data['last_mode'] = 'review'
        
        result_url = await generate_image(source_url, prompt, aspect_ratio=None, image_strength=regen_strength)
        
        if result_url:
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Перегенерировать", callback_data=f"media_regen:{regen_strength}")], [InlineKeyboardButton("⬅️ Главное меню", callback_data="menu:back")]])
            await c.bot.send_document(chat_id, document=result_url, filename="review.jpg", caption="📸 Уникальный фотоотзыв готов!", reply_markup=kb)
            from main import track_and_check
            await track_and_check(c, user, "media_review", "")
        else:
            await c.bot.send_message(chat_id, "❌ Ошибка при генерации отзыва.")
    except Exception as e:
        logger.error(f"Error review: {e}")
        await c.bot.send_message(chat_id, "❌ Ошибка при обращении к серверу.")
    finally:
        await wait_msg.delete()

# ---- ElevenLabs Voiceover ----
async def handle_voiceover_mode(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not ELEVENLABS_API_KEY:
        await u.callback_query.edit_message_text("❌ Ключ API ElevenLabs не настроен.")
        return -1
        
    await u.callback_query.edit_message_text("Получаю список доступных голосов... ⏳")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get("https://api.elevenlabs.io/v1/voices", headers={"xi-api-key": ELEVENLABS_API_KEY})
            resp.raise_for_status()
            voices = resp.json().get("voices", [])
            custom = [v for v in voices if v.get("category") in ["cloned", "generated", "professional"]]
            
            if not custom:
                await u.callback_query.edit_message_text("❌ Нет доступных кастомных голосов.")
                return -1
                
            kb = []
            for i in range(0, len(custom), 2):
                row = [InlineKeyboardButton(v["name"], callback_data=f"voice:{v['voice_id']}") for v in custom[i:i+2]]
                kb.append(row)
            
            await u.callback_query.edit_message_text("Выберите голос для озвучки:", reply_markup=InlineKeyboardMarkup(kb))
            return WAITING_VOICE_SELECTION
    except Exception as e:
        await u.callback_query.edit_message_text("❌ Ошибка при загрузке голосов.")
        return -1

async def handle_voice_selection(u: Update, c: ContextTypes.DEFAULT_TYPE):
    q = u.callback_query; await q.answer()
    c.user_data['voice_id'] = q.data.split(":")[1]
    await q.edit_message_text("Голос выбран! Теперь отправьте текст для озвучки:")
    return WAITING_VOICE_TEXT

async def receive_voice_text(u: Update, c: ContextTypes.DEFAULT_TYPE):
    c.user_data['voice_text'] = u.message.text
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🎨 Творческий", callback_data="stab:0.25"), InlineKeyboardButton("🗣 Естественный", callback_data="stab:0.5"), InlineKeyboardButton("🤖 Крепкий", callback_data="stab:0.85")]])
    await u.message.reply_text("Настройте выразительность (Стабильность) голоса:", reply_markup=kb)
    return WAITING_VOICE_STABILITY

async def handle_voice_stability(u: Update, c: ContextTypes.DEFAULT_TYPE):
    q = u.callback_query; await q.answer()
    c.user_data['voice_stability'] = float(q.data.split(":")[1])
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"{i} сек", callback_data=f"delay:{i}") for i in range(3)], [InlineKeyboardButton(f"{i} сек", callback_data=f"delay:{i}") for i in [3, 5]]])
    await q.edit_message_text("Отлично. Выберите задержку перед началом голоса:", reply_markup=kb)
    return WAITING_VOICE_DELAY

async def handle_voice_delay(u: Update, c: ContextTypes.DEFAULT_TYPE):
    q = u.callback_query; await q.answer()
    delay = int(q.data.split(":")[1])
    c.user_data['voice_delay'] = delay
    await q.edit_message_text(f"Задержка установлена: {delay} сек. 🎬 Теперь отправьте видео (до 20 МБ).")
    return WAITING_VOICE_VIDEO

async def receive_voice_video(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not u.message.video or u.message.video.file_size > 20 * 1024 * 1024:
        await u.message.reply_text("Отправьте видео до 20 МБ.")
        return WAITING_VOICE_VIDEO
        
    c.user_data['video_file_id'] = u.message.video.file_id
    await generate_and_send_voice_video(u.message.chat_id, u.effective_user, c)
    return WAITING_VOICE_VIDEO

async def generate_and_send_voice_video(chat_id: int, user, c: ContextTypes.DEFAULT_TYPE, regen_stab=None):
    wait_msg = await c.bot.send_message(chat_id, "Скачиваю видео и генерирую голос... ⏳")
    
    vid = c.user_data.get('voice_id')
    vtext = c.user_data.get('voice_text')
    vstab = regen_stab or c.user_data.get('voice_stability', 0.5)
    vdelay = c.user_data.get('voice_delay', 0)
    vfile = c.user_data.get('video_file_id')
    
    os.makedirs("temp", exist_ok=True)
    temp_vid = f"temp/to_voice_{vfile}.mp4"
    temp_aud = f"temp/to_voice_{vfile}.mp3"
    result_vid = f"temp/result_{vfile}.mp4"
    
    try:
        file = await c.bot.get_file(vfile)
        await file.download_to_drive(temp_vid)
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{vid}",
                headers={"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"},
                json={"text": vtext, "model_id": "eleven_v3", "voice_settings": {"stability": vstab, "similarity_boost": 0.75}}
            )
            resp.raise_for_status()
            with open(temp_aud, "wb") as f: f.write(resp.content)
            
        await wait_msg.edit_text("Свожу звук и видео... ⏳")
        from moviepy import VideoFileClip, AudioFileClip, CompositeAudioClip
        
        vc = VideoFileClip(temp_vid)
        ac = AudioFileClip(temp_aud)
        if vdelay > 0:
            ac = ac.with_start(vdelay)
            vc = vc.with_audio(CompositeAudioClip([ac]))
        else:
            vc = vc.with_audio(ac)
            
        vc.write_videofile(result_vid, codec="libx264", audio_codec="aac", logger=None)
        vc.close()
        ac.close()
        
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🎨 Творческий", callback_data="voice_regen:0.25"), InlineKeyboardButton("🗣 Естественный", callback_data="voice_regen:0.5"), InlineKeyboardButton("🤖 Крепкий", callback_data="voice_regen:0.85")], [InlineKeyboardButton("⬅️ В главное меню", callback_data="menu:back")]])
        with open(result_vid, "rb") as f:
            await c.bot.send_video(chat_id, video=f, caption="✅ ИИ-Озвучка наложена!", reply_markup=kb)
        from main import track_and_check
        await track_and_check(c, user, "media_voiceover", "")
            
    except Exception as e:
        logger.error(f"Voiceover eval error: {e}")
        await c.bot.send_message(chat_id, "❌ Произошла ошибка.")
    finally:
        for p in [temp_vid, temp_aud, result_vid]:
            if os.path.exists(p): os.remove(p)
        await wait_msg.delete()

async def handle_voice_regen(u: Update, c: ContextTypes.DEFAULT_TYPE):
    q = u.callback_query; await q.answer()
    stab = float(q.data.split(":")[1])
    await generate_and_send_voice_video(u.effective_chat.id, u.effective_user, c, regen_stab=stab)
    return WAITING_VOICE_VIDEO
