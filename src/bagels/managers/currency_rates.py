# src/bagels/managers/currency_rates.py

from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from sqlalchemy.orm import sessionmaker

from bagels.models.currency_rate import CurrencyRate
from bagels.models.database.app import db_engine

Session = sessionmaker(bind=db_engine)


def list_rates() -> List[CurrencyRate]:
    """Return all non-deleted rates, sorted for nicer display."""
    session = Session()
    try:
        return (
            session.query(CurrencyRate)
            .filter(CurrencyRate.deletedAt.is_(None))
            .order_by(CurrencyRate.fromCode, CurrencyRate.toCode)
            .all()
        )
    finally:
        session.close()


def get_rate(from_code: str, to_code: str) -> Optional[float]:
    """
    Get an exchange rate between two currencies.

    1 from_code = rate * to_code.

    If only reverse pair exists (to_code → from_code),
    return its inverse. If nothing found, return None.
    """
    from_code = from_code.upper()
    to_code = to_code.upper()

    if from_code == to_code:
        return 1.0

    session = Session()
    try:
        # Direct rate
        direct: CurrencyRate | None = (
            session.query(CurrencyRate)
            .filter(
                CurrencyRate.fromCode == from_code,
                CurrencyRate.toCode == to_code,
                CurrencyRate.deletedAt.is_(None),
            )
            .one_or_none()
        )
        if direct is not None:
            return direct.rate

        # Reverse rate (invert)
        reverse: CurrencyRate | None = (
            session.query(CurrencyRate)
            .filter(
                CurrencyRate.fromCode == to_code,
                CurrencyRate.toCode == from_code,
                CurrencyRate.deletedAt.is_(None),
            )
            .one_or_none()
        )
        if reverse is not None and reverse.rate not in (None, 0):
            return 1.0 / reverse.rate

        return None
    finally:
        session.close()


def set_rate(
    from_code: str,
    to_code: str,
    rate: float,
    is_manual: bool = True,
) -> None:
    """
    Upsert a rate into the currency_rate table.

    Invariant:
        For any distinct currencies A,B:
            1 A = r * B
            1 B = (1 / r) * A

    We enforce this by always updating/creating BOTH directions
    as exact inverses of each other. The last call wins.
    """
    from_code = from_code.upper()
    to_code = to_code.upper()

    if from_code == to_code:
        raise ValueError("from_code and to_code must be different.")

    session = Session()
    try:
        now = datetime.now()

        # --- direct row: from_code -> to_code ---
        direct: CurrencyRate | None = (
            session.query(CurrencyRate)
            .filter(
                CurrencyRate.fromCode == from_code,
                CurrencyRate.toCode == to_code,
                CurrencyRate.deletedAt.is_(None),
            )
            .one_or_none()
        )

        if direct is None:
            direct = CurrencyRate(
                fromCode=from_code,
                toCode=to_code,
                rate=rate,
                isManual=is_manual,
            )
            direct.updatedAt = now
            session.add(direct)
        else:
            direct.rate = rate
            direct.isManual = is_manual
            direct.updatedAt = now

        # --- keep reverse consistent (unless same currency) ---
        if from_code != to_code and rate not in (None, 0):
            inverse = 1.0 / rate

            reverse: CurrencyRate | None = (
                session.query(CurrencyRate)
                .filter(
                    CurrencyRate.fromCode == to_code,
                    CurrencyRate.toCode == from_code,
                    CurrencyRate.deletedAt.is_(None),
                )
                .one_or_none()
            )

            if reverse is None:
                reverse = CurrencyRate(
                    fromCode=to_code,
                    toCode=from_code,
                    rate=inverse,
                    isManual=is_manual,
                )
                reverse.updatedAt = now
                session.add(reverse)
            else:
                reverse.rate = inverse
                reverse.isManual = is_manual
                reverse.updatedAt = now

        session.commit()
    finally:
        session.close()



def convert(amount: float, from_code: str, to_code: str) -> Optional[float]:
    """
    Convert amount from from_code to to_code using stored rates.

    Returns None if no rate is available.
    """
    rate = get_rate(from_code, to_code)
    if rate is None:
        return None
    return amount * rate
