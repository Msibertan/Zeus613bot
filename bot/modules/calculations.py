
def get_currency_rates():
    return {
        "EUR": 92.93,
        "USD": 79.81,
        "BYN": 27.01
    }

def convert_prices_v2(price_rub: float, customs_rub: float):
    rates = get_currency_rates()

    def fmt(amount: float) -> str:
        return f"{amount:,.2f}".replace(",", " ").replace(".", ",")

    price_byn = price_rub / rates["BYN"] if price_rub else 0
    customs_byn = customs_rub / rates["BYN"]
    customs_percent = (customs_byn / price_byn * 100) if price_byn else 0.0

    return {
        "price_rub": fmt(price_rub),
        "price_eur": fmt(price_rub / rates["EUR"]) if price_rub else "",
        "price_byn": fmt(price_byn) if price_rub else "",
        "price_usd": fmt(price_rub / rates["USD"]) if price_rub else "",
        "price_original": fmt(price_rub / rates["USD"]) if price_rub else "",
        "original_currency": "USD",
        "customs_rub": fmt(customs_rub),
        "customs_byn": fmt(customs_byn),
        "customs_usd": fmt(customs_rub / rates["USD"]),
        "customs_percent": fmt(customs_percent) + " %"
    }
