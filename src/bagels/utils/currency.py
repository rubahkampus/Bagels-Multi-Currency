# src/bagels/utils/currency.py

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from bagels.config import CONFIG

from bagels.managers.currency_rates import convert  # NEW


def _normalize_code(code: Optional[str]) -> str:
    """
    Normalize a currency code:
    - if None → use default_currency
    - uppercase otherwise
    """
    if not code:
        return CONFIG.defaults.default_currency.upper()
    return code.upper()


def get_currency(code: Optional[str]) -> Optional[object]:
    """
    Return the CurrencyConfig for a given code, or None if not found.
    Falls back to the default currency if possible.
    """
    norm = _normalize_code(code)

    # First pass: exact match
    for c in CONFIG.currencies.supported:
        if c.code.upper() == norm:
            return c

    # If requested code not found, try default currency
    default_code = CONFIG.defaults.default_currency.upper()
    if norm != default_code:
        for c in CONFIG.currencies.supported:
            if c.code.upper() == default_code:
                return c

    return None


def get_symbol(code: Optional[str]) -> str:
    """
    Return symbol for the given currency code, or empty string if unknown.
    """
    cur = get_currency(code)
    return cur.symbol if cur else ""


def get_decimals(code: Optional[str]) -> int:
    """
    Return decimals for the given currency code.
    If unknown, fall back to CONFIG.defaults.round_decimals.
    """
    cur = get_currency(code)
    if cur is not None:
        return cur.decimals
    return getattr(CONFIG.defaults, "round_decimals", 2)

def format_amount(amount: float | Decimal, code: Optional[str]) -> str:
    """
    Format an amount with currency symbol and correct decimals.

    Examples (with default_currency=USD):
    - format_amount(123.456, "USD") -> "$123.46"
    - format_amount(-5000, "IDR")   -> "-Rp5000"
    - format_amount(10, None)       -> defaults to CONFIG.defaults.default_currency
    """
    cur = get_currency(code)
    if cur is None:
        # Fallback: just numeric with default decimals, no symbol
        decimals = get_decimals(None)
        q = Decimal(str(amount)).quantize(
            Decimal("1") if decimals == 0 else Decimal("1." + "0" * decimals),
            rounding=ROUND_HALF_UP,
        )
        if decimals == 0:
            return str(int(q))
        return f"{q:.{decimals}f}"

    symbol = cur.symbol
    decimals = cur.decimals

    # Keep sign separate so we don't get weird "$-123.45" vs "-$123.45" surprises.
    sign = "-" if amount < 0 else ""
    abs_amount = abs(Decimal(str(amount)))

    quant = Decimal("1") if decimals == 0 else Decimal("1." + "0" * decimals)
    rounded = abs_amount.quantize(quant, rounding=ROUND_HALF_UP)

    if decimals == 0:
        number_str = str(int(rounded))
    else:
        # fixed number of decimal places
        number_str = f"{rounded:.{decimals}f}"

    # choose convention: -Rp5000 or -$123.45
    return f"{sign}{symbol}{number_str}"

def format_record_amount(record, show_default_equiv: bool = True) -> str:
    """
    Format a Record.amount with:
    - per-record currency symbol/decimals
    - optional equivalent in default currency

    Example: "€10.00 (≈ $11.20)".
    """
    code = getattr(record, "currencyCode", None) or CONFIG.defaults.default_currency
    base_str = format_amount(record.amount, code)

    if not show_default_equiv:
        return base_str

    default_code = CONFIG.defaults.default_currency
    if code == default_code:
        # Already in default currency, nothing extra to show
        return base_str

    equiv = convert(record.amount, code, default_code)
    if equiv is None:
        # No rate available → still show base, mark as such
        return f"{base_str} (no rate for {default_code} ↔ {code})"

    equiv_str = format_amount(equiv, default_code)
    return f"{base_str} (≈ {equiv_str})"

def format_amount_default(amount) -> str:
    """
    Format an amount in the default currency.
    """
    
    code = CONFIG.defaults.default_currency
    base_str = format_amount(amount, code)
    
    return f"{base_str}"
