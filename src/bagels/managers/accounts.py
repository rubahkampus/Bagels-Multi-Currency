from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from bagels.config import CONFIG
from bagels.models.account import Account
from bagels.models.database.app import db_engine
from bagels.models.record import Record
from bagels.models.split import Split

from bagels.managers.currency_rates import convert as convert_currency


Session = sessionmaker(bind=db_engine)


# region Create


def create_account(data):
    session = Session()
    try:
        new_account = Account(**data)
        session.add(new_account)
        session.commit()
        session.refresh(new_account)
        session.expunge(new_account)
        return new_account
    finally:
        session.close()


# region Read


def get_account_balance(accountId, session=None):
    """Returns the net balance of an account.

    Rules:
    - Consider all record "account" and split "account"
    - Records with isTransfer should consider both "account" and "transferToAccount"
    - Records and splits should be considered separately, unlike net figures which consider records and splits together.

    Args:
        accountId (int): The ID of the account to get the balance
        session (Session, optional): SQLAlchemy session to use. If None, creates a new session.
    """
    if session is None:
        session = Session()
        should_close = True
    else:
        should_close = False
        
    default_code = CONFIG.defaults.default_currency

    try:
        # Initialize balance
        balance = (
            session.query(Account)
            .filter(Account.id == accountId)
            .first()
            .beginningBalance
        )

        # Get all records for this account
        records = session.query(Record).filter(Record.accountId == accountId).all()

        # Calculate balance from records
        for record in records:
            # record.amount in record's currency; convert to default currency
            code = getattr(record, "currencyCode", None) or default_code
            if code == default_code:
                amount_default = record.amount
            else:
                amount_default = convert_currency(record.amount, code, default_code)
                if amount_default is None:
                    # can't convert → skip for balance
                    continue

            if record.isTransfer:
                balance -= amount_default
            elif record.isIncome:
                balance += amount_default
            else:
                balance -= amount_default

        # Get all records where this account is the transfer destination
        transfer_to_records = (
            session.query(Record)
            .filter(Record.transferToAccountId == accountId, Record.isTransfer == True)  # noqa
            .all()
        )

        # Add transfers into this account
        for record in transfer_to_records:
            code = getattr(record, "currencyCode", None) or default_code
            if code == default_code:
                amount_default = record.amount
            else:
                amount_default = convert_currency(record.amount, code, default_code)
                if amount_default is None:
                    continue
            balance += amount_default


        # Get all splits where this account is specified
        splits = session.query(Split).filter(Split.accountId == accountId).all()

        # Add paid splits (they represent money coming into this account)
        for split in splits:
            if not split.isPaid:
                continue

            # choose best currency for this split
            code = (
                getattr(split, "currencyCode", None)
                or getattr(split.record, "currencyCode", None)
                or default_code
            )

            if code == default_code:
                amount_default = split.amount
            else:
                amount_default = convert_currency(split.amount, code, default_code)
                if amount_default is None:
                    continue

            if split.record.isIncome:
                balance -= amount_default
            else:
                balance += amount_default


        return round(balance, CONFIG.defaults.round_decimals)
    finally:
        if should_close:
            session.close()


def _get_base_accounts_query(get_hidden=False):
    stmt = select(Account).filter(Account.deletedAt.is_(None))
    if not get_hidden:
        stmt = stmt.filter(Account.hidden.is_(False))
    else:
        stmt = stmt.order_by(Account.hidden)
    return stmt


def get_all_accounts(get_hidden=False):
    session = Session()
    try:
        stmt = _get_base_accounts_query(get_hidden)
        return session.scalars(stmt).all()
    finally:
        session.close()


def get_accounts_count(get_hidden=False):
    session = Session()
    try:
        stmt = _get_base_accounts_query(get_hidden)
        return len(session.scalars(stmt).all())
    finally:
        session.close()


def get_all_accounts_with_balance(get_hidden=False):
    session = Session()
    try:
        stmt = _get_base_accounts_query(get_hidden)
        accounts = session.scalars(stmt).all()
        for account in accounts:
            account.balance = get_account_balance(account.id, session)
        return accounts
    finally:
        session.close()


def get_account_balance_by_id(account_id):
    session = Session()
    try:
        return get_account_balance(account_id, session)
    finally:
        session.close()


def get_account_by_id(account_id):
    session = Session()
    try:
        return session.get(Account, account_id)
    finally:
        session.close()


# region Update


def update_account(account_id, data):
    session = Session()
    try:
        account = session.get(Account, account_id)
        if account:
            for key, value in data.items():
                setattr(account, key, value)
            session.commit()
            session.refresh(account)
            session.expunge(account)
        return account
    finally:
        session.close()


# region Delete


def delete_account(account_id):
    session = Session()
    try:
        account = session.get(Account, account_id)
        if account:
            account.deletedAt = datetime.now()
            session.commit()
            return True
        return False
    finally:
        session.close()
