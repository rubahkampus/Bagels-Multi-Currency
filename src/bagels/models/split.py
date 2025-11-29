from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship, validates

from bagels.config import CONFIG

from .database.db import Base


class Split(Base):
    __tablename__ = "split"

    createdAt = Column(DateTime, nullable=False, default=datetime.now)
    updatedAt = Column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )

    id = Column(Integer, primary_key=True, index=True)
    recordId = Column(
        Integer, ForeignKey("record.id", ondelete="CASCADE"), nullable=False
    )
    amount = Column(Float, nullable=False)
    personId = Column(Integer, ForeignKey("person.id"), nullable=False)
    isPaid = Column(Boolean, nullable=False, default=False)
    paidDate = Column(DateTime, nullable=True)
    accountId = Column(Integer, ForeignKey("account.id"), nullable=True)

    record = relationship("Record", foreign_keys=[recordId], back_populates="splits")
    person = relationship("Person", foreign_keys=[personId], back_populates="splits")
    account = relationship("Account", foreign_keys=[accountId], back_populates="splits")
    
    # NEW: optional per-split currency; if None, use record.currencyCode
    currencyCode = Column(String(3), nullable=True)

    @validates("amount")
    def validate_amount(self, key, value):
        if value is not None:
            return round(value, CONFIG.defaults.round_decimals)
        return value
    
    @validates("currencyCode")
    def validate_currency_code(self, key, value):
        """
        Normalise per-split currency codes:
        - None / empty -> None
        - strip + uppercase 3-letter code
        """
        if not value:
            return None
        value = value.strip().upper()
        if len(value) != 3:
            raise ValueError(f"Invalid currency code: {value!r}")
        return value
