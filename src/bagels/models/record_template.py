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
    event,
    func,
    select,
)
from sqlalchemy.orm import relationship, validates

from bagels.config import CONFIG

from .database.db import Base


class RecordTemplate(Base):
    __tablename__ = "record_template"

    createdAt = Column(DateTime, nullable=False, default=datetime.now)
    updatedAt = Column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )

    id = Column(Integer, primary_key=True, index=True)
    label = Column(String, nullable=False)
    amount = Column(Float, CheckConstraint("amount > 0"), nullable=False)
    
    # NEW: ISO-like currency code for this template, e.g. "USD", "EUR", "IDR"
    currencyCode = Column(String(3), nullable=True)
    
    accountId = Column(Integer, ForeignKey("account.id"), nullable=False)
    categoryId = Column(Integer, ForeignKey("category.id"), nullable=True)

    order = Column(Integer, nullable=False, unique=True)

    isIncome = Column(Boolean, nullable=False, default=False)
    isTransfer = Column(
        Boolean,
        CheckConstraint("(isTransfer = FALSE) OR (isIncome = FALSE)"),
        nullable=False,
        default=False,
    )
    transferToAccountId = Column(Integer, ForeignKey("account.id"), nullable=True)

    account = relationship("Account", foreign_keys=[accountId])
    category = relationship("Category", foreign_keys=[categoryId])
    transferToAccount = relationship("Account", foreign_keys=[transferToAccountId])

    def to_dict(self) -> dict:
        """Creates a dictionary object to feed into create_record."""
        return {
            "label": self.label,
            "amount": self.amount,
            "accountId": self.accountId,
            "categoryId": self.categoryId,
            "isIncome": self.isIncome,
            "isTransfer": self.isTransfer,
            "transferToAccountId": self.transferToAccountId,
            # NEW:
            "currencyCode": self.currencyCode,
        }

    @validates("order")
    def validate_order(self, key, order):
        if order is None:
            raise ValueError("Order cannot be null.")
        return order

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


@event.listens_for(RecordTemplate, "before_insert")
def receive_before_insert(mapper, connection, target):
    max_order = connection.execute(
        select(func.max(RecordTemplate.order))
    ).scalar_one_or_none()
    target.order = (max_order or 0) + 1
