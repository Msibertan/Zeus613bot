import os
import json
import tempfile
import base64
from openai import OpenAI
from aiogram import Bot

async def extract_fields_from_file(
    bot: Bot,
    document,
    template_fields: list,
    api_key: str,
    model: str = "gpt-3.5-turbo"
) -> dict:
    """
    Скачиваем PDF/DOCX/изображение через bot, кодируем в Base64
    и шлём в ChatGPT. GPT сам выполнит OCR/парсинг формата и вернёт JSON.
    """

    # 1) Скачиваем файл
    tmp_dir = tempfile.gettempdir()
    filename = getattr(document, "file_name", f"{document.file_id}.bin")
    tmp_path = os.path.join(tmp_dir, filename)

    info = await bot.get_file(document.file_id)
    await bot.download_file(info.file_path, destination=tmp_path)

    # 2) Кодируем в Base64
    with open(tmp_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    # 3) Формируем prompt
    mapping = "\n".join(f"{f['name']} — «{f['label']}»" for f in template_fields)
    system_prompt = (
        "Ты — экспертный парсер документов и изображений. "
        "Я пришлю Base64-файл. Твоя задача:\n"
        " 1. Декодировать Base64.\n"
        " 2. Если PDF/DOCX — распознать текст, "
        "если изображение — выполнить OCR.\n"
        " 3. По списку полей ниже извлечь их значения.\n"
        " 4. Вернуть строго JSON-объект mapping internal names → values.\n\n"
        "Список полей:\n" + mapping + "\n\n"
        "Файл (Base64):"
    )

    # 4) Вызываем OpenAI
    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system",  "content": system_prompt},
            {"role": "user",    "content": b64}
        ],
        temperature=0
    )
    text = resp.choices[0].message.content.strip()

    # 5) Парсим JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        raise ValueError(f"❌ Невалидный JSON от GPT:\n{text}")
