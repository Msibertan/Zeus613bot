from docxtpl import DocxTemplate
from transliterate import translit

def translit_safe(text):
    return translit(text, 'ru', reversed=True) if text else ""

def fuel_type_to_de(value):
    mapping = {
        "бензин": "Benzin",
        "дизель": "Diesel",
        "гибрид": "Hybrid",
        "электро": "Elektro",
        "газ": "Gas"
    }
    return mapping.get(value.strip().lower(), value)

def color_to_de(value):
    mapping = {
        "синий": "Blau",
        "черный": "Schwarz",
        "белый": "Weiß",
        "серый": "Grau",
        "красный": "Rot",
        "зеленый": "Grün",
        "желтый": "Gelb",
        "коричневый": "Braun"
    }
    return mapping.get(value.strip().lower(), value)

def transmission_to_de(value):
    mapping = {
        "автоматическая": "Automatikgetriebe",
        "механическая": "Schaltgetriebe",
        "вариатор": "CVT-Getriebe",
        "роботизированная": "Automatisiertes Getriebe"
    }
    return mapping.get(value.strip().lower(), value)

def generate_dkp_doc(data: dict, template_path: str, output_path: str):
    # Обработка и конвертация чисел с пробелами и запятыми
    raw_price_eur = str(data.get("price_eur", "0")).replace(" ", "").replace(",", ".")
    try:
        price_eur = float(raw_price_eur)
    except ValueError:
        price_eur = 0.0

    vereinbarter_preis = price_eur - 50
    restbetrag = price_eur

    try:
        engine_power_hp = int(str(data.get("engine_power_hp", "0")).replace(" ", ""))
    except ValueError:
        engine_power_hp = 0

    engine_power_kw = round(engine_power_hp * 0.7355)

    buyer_name_translit = translit_safe(data.get("full_name", ""))
    address_de = translit_safe(data.get("address", ""))
    company_name = translit_safe(data.get("company_name", ""))

    context = {
        "date": data.get("date", ""),
        "buyer_name_translit": buyer_name_translit,
        "passport_number": data.get("passport_number", ""),
        "address_de": address_de,
        "company_name": company_name,
        "car_model": data.get("car_model", ""),
        "car_release_year": data.get("car_release_year", ""),
        "vin_code": data.get("vin_code", ""),
        "car_color": color_to_de(data.get("car_color", "")),
        "engine_volume": data.get("engine_volume", ""),
        "engine_power_hp": engine_power_hp,
        "engine_power_kw": engine_power_kw,
        "fuel_type": fuel_type_to_de(data.get("fuel_type", "")),
        "transmission": transmission_to_de(data.get("transmission", "")),
        "seats_number": data.get("seats_number", ""),
        "mileage": data.get("mileage", ""),
        "vereinbarter_preis_int": f"{int(vereinbarter_preis):,}".replace(",", " "),
        "kaution_int": f"{int(vereinbarter_preis):,}".replace(",", " "),
        "restbetrag_int": f"{int(restbetrag):,}".replace(",", " "),
        "vereinbarter_preis": f"{vereinbarter_preis:,.2f}".replace(",", " ").replace(".", ","),
        "kaution": f"{vereinbarter_preis:,.2f}".replace(",", " ").replace(".", ","),
        "other_fees": "50,00",
        "restbetrag": f"{restbetrag:,.2f}".replace(",", " ").replace(".", ",")
    }

    doc = DocxTemplate(template_path)
    doc.render(context)
    doc.save(output_path)
