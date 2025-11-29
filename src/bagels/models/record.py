from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship, validates

from bagels.config import CONFIG

from .database.db import Base


class Record(Base):
    __tablename__ = "record"

    createdAt = Column(DateTime, nullable=False, default=datetime.now)
    updatedAt = Column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )

    id = Column(Integer, primary_key=True, index=True)
    label = Column(String, nullable=False)
    amount = Column(Float, CheckConstraint("amount > 0"), nullable=False)
    
    # NEW: ISO-like currency code for this record, e.g. "USD", "EUR", "IDR"
    currencyCode = Column(String(3), nullable=True)
    
    date = Column(DateTime, nullable=False, default=datetime.now)
    accountId = Column(Integer, ForeignKey("account.id"), nullable=False)
    categoryId = Column(Integer, ForeignKey("category.id"), nullable=True)

    tags = Column(String, nullable=True)  # unimplemented
    isInProgress = Column(Boolean, nullable=False, default=False)  # unimplemented

    # if record adds money to account
    isIncome = Column(Boolean, nullable=False, default=False)
    # if record is transfer to this account
    isTransfer = Column(
        Boolean,
        CheckConstraint("(isTransfer = FALSE) OR (isIncome = FALSE)"),
        nullable=False,
        default=False,
    )
    transferToAccountId = Column(Integer, ForeignKey("account.id"), nullable=True)

    account = relationship(
        "Account", foreign_keys=[accountId], back_populates="records"
    )
    category = relationship("Category", back_populates="records")
    transferToAccount = relationship(
        "Account",
        foreign_keys=[transferToAccountId],
        back_populates="transferFromRecords",
    )
    splits = relationship(
        "Split", back_populates="record", cascade="all, delete-orphan"
    )

    @validates("amount")
    def validate_amount(self, key, value):
        if value is not None:
            return round(value, CONFIG.defaults.round_decimals)
        return value
    
    @validates("currencyCode")
    def validate_currency_code(self, key, value):
        """
        Normalise currency codes:
        - empty / None -> None
        - strip + uppercase
        No hard validation against CONFIG here to avoid surprises if config changes.
        """
        if not value:
            return None
        value = value.strip().upper()
        if len(value) != 3:
            # Be forgiving: either raise or just keep as-is.
            # For demo & stability I'd keep it strict:
            raise ValueError(f"Invalid currency code: {value!r}")
        return value

