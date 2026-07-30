import re
from typing import Dict, Any, Tuple, Optional

# Standard exchange rates relative to 1 USD (Updated reference rates with fallback)
DEFAULT_FX_RATES = {
    "USD": 1.0,
    "EUR": 0.92,
    "GBP": 0.79,
    "INR": 83.2,
    "CAD": 1.35,
    "AUD": 1.52,
    "JPY": 155.0,
    "SGD": 1.35,
    "AED": 3.67,
    "CHF": 0.88
}

CURRENCY_SYMBOLS = {
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
    "₹": "INR",
    "¥": "JPY",
    "A$": "AUD",
    "C$": "CAD",
    "AED": "AED",
    "CHF": "CHF",
    "SGD": "SGD"
}

class CurrencyNormalizationEngine:
    """
    Real-time multi-currency normalization & compensation parsing engine.
    Converts local salary representations into normalized USD & INR_LPA equivalents.
    """
    def __init__(self, fx_rates: Optional[Dict[str, float]] = None):
        self.fx_rates = fx_rates or DEFAULT_FX_RATES

    def detect_currency(self, text: str) -> str:
        t_clean = text.strip()
        for symbol, code in CURRENCY_SYMBOLS.items():
            if symbol in t_clean:
                return code
        
        t_upper = text.upper()
        for code in DEFAULT_FX_RATES.keys():
            if code in t_upper:
                return code
                
        if "LPA" in t_upper or "LAKH" in t_upper or "RUPEES" in t_upper:
            return "INR"
        return "USD"

    def parse_salary_string(self, salary_str: str) -> Dict[str, Any]:
        result = {
            "raw_string": salary_str,
            "currency": "USD",
            "min_annual_local": 0.0,
            "max_annual_local": 0.0,
            "min_usd": 0.0,
            "max_usd": 0.0,
            "normalized_lpa": 0.0,
            "has_equity": False,
            "is_specified": True
        }

        if not salary_str or "not specified" in salary_str.lower() or "undisclosed" in salary_str.lower():
            result["is_specified"] = False
            return result

        sal_lower = salary_str.lower()
        currency = self.detect_currency(salary_str)
        result["currency"] = currency

        # Equity / Bonus Detection
        if any(term in sal_lower for term in ["equity", "rsu", "stock", "options", "bonus"]):
            result["has_equity"] = True

        # Extract numerical values
        sal_clean = re.sub(r'[^0-9.\-\s]', ' ', sal_lower)
        numbers = [float(n) for n in re.findall(r'\d+(?:\.\d+)?', sal_clean)]

        if not numbers:
            result["is_specified"] = False
            return result

        is_k = "k" in sal_lower
        is_lpa = "lpa" in sal_lower or "lakh" in sal_lower or "l" in sal_lower or currency == "INR"
        is_monthly = "month" in sal_lower or "/mo" in sal_lower or "pm" in sal_lower

        min_val = numbers[0]
        max_val = numbers[1] if len(numbers) > 1 else min_val

        # Scale value to annual local currency
        if is_lpa:
            min_annual = min_val * 100000.0
            max_annual = max_val * 100000.0
        elif is_k:
            min_annual = min_val * 1000.0
            max_annual = max_val * 1000.0
        elif is_monthly:
            min_annual = min_val * 12.0
            max_annual = max_val * 12.0
        else:
            if min_val < 200.0 and currency == "INR":
                min_annual = min_val * 100000.0
                max_annual = max_val * 100000.0
            elif min_val < 300.0:
                # Assume thousands if small number without suffix
                min_annual = min_val * 1000.0
                max_annual = max_val * 1000.0
            else:
                min_annual = min_val
                max_annual = max_val

        fx_rate = self.fx_rates.get(currency, 1.0)
        min_usd = min_annual / fx_rate
        max_usd = max_annual / fx_rate

        inr_fx = self.fx_rates.get("INR", 83.2)
        min_lpa = (min_usd * inr_fx) / 100000.0
        max_lpa = (max_usd * inr_fx) / 100000.0

        result["min_annual_local"] = round(min_annual, 2)
        result["max_annual_local"] = round(max_annual, 2)
        result["min_usd"] = round(min_usd, 2)
        result["max_usd"] = round(max_usd, 2)
        result["normalized_lpa"] = round((min_lpa + max_lpa) / 2.0, 2)

        return result

global_currency_engine = CurrencyNormalizationEngine()
