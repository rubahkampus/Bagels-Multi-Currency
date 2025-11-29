from datetime import datetime

from sqlalchemy.orm import validates

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, UniqueConstraint

from .database.db import Base


class CurrencyRate(Base):
    __tablename__ = "currency_rate"
    __table_args__ = (
        UniqueConstraint("fromCode", "toCode", name="uq_currency_rate_from_to"),
    )

    createdAt = Column(DateTime, nullable=False, default=datetime.now)
    updatedAt = Column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )
    deletedAt = Column(DateTime, nullable=True)

    id = Column(Integer, primary_key=True, index=True)

    # e.g. "USD", "IDR"
    fromCode = Column(String(3), nullable=False)

    # e.g. "IDR", "USD"
    toCode = Column(String(3), nullable=False)

    # 1 fromCode = rate * toCode (you decide convention, just be consistent)
    rate = Column(Float, nullable=False)

    # True if user entered manually, False if imported / auto-fetched
    isManual = Column(Boolean, nullable=False, default=True)
    
    @validates("fromCode", "toCode")
    def validate_codes(self, key, value):
        """
        Normalise FX currency codes:
        - strip + uppercase
        - optional 3-letter guard
        """
        if not value:
            raise ValueError(f"{key} cannot be empty")
        value = value.strip().upper()
        if len(value) != 3:
            raise ValueError(f"Invalid {key} value: {value!r}")
        return value
