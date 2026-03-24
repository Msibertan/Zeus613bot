from datetime import datetime, date
from docxtpl import DocxTemplate
from typing import Any, Dict, Iterable, Optional

def _first(d: Dict[str, Any], keys: Iterable[str]) -> Optional[Any]:
    for k in keys:
        v = d.get(k)
        if v not in (None, "", []):
            return v
    return None

def _fmt_byn(x: Any) -> str:
    if x is None:
        return ""
    try:
        s = str(x).replace(" ", "").replace(",", ".")
        return f"{float(s):.2f}"
    except Exception:
        return str(x)

def _fmt_date(val: Any) -> str:
    if isinstance(val, (date, datetime)):
        dt = val if isinstance(val, datetime) else datetime.combine(val, datetime.min.time())
        return dt.strftime("%d.%m.%Y")
    if isinstance(val, str):
        txt = val.strip()
        try:
            datetime.strptime(txt, "%d.%m.%Y")
            return txt
        except Exception:
            pass
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(txt, fmt).strftime("%d.%m.%Y")
            except Exception:
                continue
        return txt
    return datetime.today().strftime("%d.%m.%Y")

def generate_kvit_doc(data: dict, template_path: str, output_path: str):
    """
    Плейсхолдеры шаблона: {{ full_name }}, {{ car_model }}, {{ vin_code }}, {{ customs_byn }}, {{ data }}
    """
    full_name = _first(data, ["full_name", "fio", "payer_name"]) or ""
    car_model = _first(data, ["car_model", "model", "auto_model", "vehicle_model", "car"]) or ""

    # принимаем и vin_code, и vin — на входе может прийти любой; в шаблон кладём ТОЛЬКО vin_code
    vin_code = _first(data, ["vin_code", "vin", "VIN", "Vin"]) or ""
    vin_code = str(vin_code).strip().upper()

    customs_byn = _fmt_byn(_first(
        data,
        ["customs_byn", "customs_byn_amount", "customs_amount_byn", "sum_byn", "amount_byn", "customs"]
    ))
    data_str = _fmt_date(_first(data, ["data", "date", "kvit_date"]) or datetime.today())

    context = {
        "full_name": full_name,
        "car_model": car_model,
        "vin_code": vin_code,  # ← единый ключ для всех шаблонов
        "customs_byn": customs_byn,
        "data": data_str,
        "date": data_str,      # обратная совместимость, если где-то используется
    }

    # опциональные (на будущее — если добавишь в шаблон)
    context.update({
        "payer_address": _first(data, ["payer_address", "address"]) or "",
        "passport_sn": _first(data, ["passport_sn", "passport_series_number"]) or "",
        "passport_issued_by": _first(data, ["passport_issued_by", "passport_issuer"]) or "",
        "passport_issue_date": _fmt_date(_first(data, ["passport_issue_date", "passport_date"]) or data_str),
    })

    doc = DocxTemplate(template_path)
    doc.render(context)
    doc.save(output_path)
