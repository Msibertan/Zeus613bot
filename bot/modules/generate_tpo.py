from docxtpl import DocxTemplate
from .calculations import convert_prices_v2
from datetime import datetime

def generate_tpo_doc(data: dict, template_path: str, output_path: str):
    # Преобразуем данные и удаляем пробелы и запятые
    price_rub = float(str(data.get("price_rub", "0")).replace(" ", "").replace(",", "."))
    customs_rub = float(str(data.get("customs_rub", "0")).replace(" ", "").replace(",", "."))

    prices = convert_prices_v2(price_rub=price_rub, customs_rub=customs_rub)

    # Обработка года выпуска
    car_release_year = data.get("car_release_year", "")
    if not car_release_year:
        car_release_year = datetime.now().year

    # Обработка даты оформления
    tpo_date = data.get("tpo_date", "")
    if not tpo_date:
        tpo_date = datetime.now().strftime("%d-%m-%Y")

    # Дата без точек
    tpo_date_nodots = tpo_date.replace(".", "")

    # Получение евро-цены
    price_eur = prices.get("price_eur", 0)

    # Подготовка шаблонных данных
    context = {
        "full_name": data.get("full_name", ""),
        "address": data.get("address", ""),
        "passport_number": data.get("passport_number", ""),
        "passport_issued_by": data.get("passport_issued_by", ""),
        "passport_issued_date": data.get("passport_issued_date", ""),
        "car_model": data.get("car_model", ""),
        "vin_code": data.get("vin_code", ""),
        "customs_amount": prices["customs_rub"],
        "tpo_date": tpo_date,
        "car_release_year": car_release_year,
        "engine_volume": data.get("engine_volume", ""),
        "price_rub": data.get("price_rub", ""),
        "passport_series": data.get("passport_series", ""),

        "price_eur": price_eur,
        "price_byn": prices.get("price_byn", 0),
        "price_usd": prices.get("price_usd", 0),
        "customs_percent": prices.get("customs_percent", 0),
        "customs_byn": prices.get("customs_byn", 0),
        "customs_usd": prices.get("customs_usd", 0),
        "tpo_date_nodots": tpo_date_nodots
    }

    doc = DocxTemplate(template_path)
    doc.render(context)
    doc.save(output_path)
