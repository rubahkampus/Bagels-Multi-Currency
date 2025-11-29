import copy
from rich.text import Text

from bagels.managers.accounts import get_all_accounts_with_balance
from bagels.managers.categories import get_all_categories_by_freq
from bagels.managers.record_templates import get_template_by_id
from bagels.forms.form import Form, FormField, Option, Options

from bagels.config import CONFIG  # NEW


class RecordTemplateForm:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    # ------------ Blueprints ------------ #

    FORM = Form(
        fields=[
            FormField(
                placeholder="Template label",
                title="Label",
                key="label",
                type="string",
                is_required=True,
            ),
            FormField(
                title="Category",
                key="categoryId",
                type="autocomplete",
                options=Options(),
                is_required=True,
                placeholder="Select Category",
            ),
            FormField(
                placeholder="0.00",
                title="Amount",
                key="amount",
                type="number",
                min=0,
                is_required=True,
            ),
            # NEW: template currency (optional)
            FormField(
                title="Currency",
                key="currencyCode",
                type="autocomplete",
                options=Options(),
                is_required=False,
                placeholder="Leave empty for default currency",
            ),
            FormField(
                title="Account",
                key="accountId",
                type="autocomplete",
                options=Options(),
                is_required=True,
                placeholder="Select Account",
            ),
            FormField(
                title="Type",
                key="isIncome",
                type="boolean",
                labels=["Expense", "Income"],
                default_value=False,
            ),
        ]
    )

    # ----------------- - ---------------- #

    def __init__(self):
        self._populate_form_options()
        self._populate_currency_options()  # NEW

    # -------------- Helpers ------------- #

    def _populate_form_options(self):
        accounts = get_all_accounts_with_balance()
        self.FORM.fields[4].options = Options(
            items=[
                Option(
                    text=account.name,
                    value=account.id,
                    postfix=Text(f"{account.balance}", style="yellow"),
                )
                for account in accounts
            ]
        )

        categories = get_all_categories_by_freq()
        self.FORM.fields[1].options = Options(
            items=[
                Option(
                    text=category.name,
                    value=category.id,
                    prefix=Text("●", style=category.color),
                    postfix=(
                        Text(
                            (
                                f"↪ {category.parentCategory.name}"
                                if category.parentCategory
                                else ""
                            ),
                            style=category.parentCategory.color,
                        )
                        if category.parentCategory
                        else ""
                    ),
                )
                for category, _ in categories
            ]
        )
        
    def _populate_currency_options(self):
        currencies_cfg = getattr(CONFIG, "currencies", None)
        if not currencies_cfg or not getattr(currencies_cfg, "supported", None):
            return

        currency_field = next(
            (f for f in self.FORM.fields if f.key == "currencyCode"),
            None,
        )
        if currency_field is None:
            return

        items: list[Option] = []
        for cur in currencies_cfg.supported:
            label = f"{cur.code} ({cur.symbol})"
            items.append(
                Option(
                    text=label,
                    value=cur.code,
                )
            )

        currency_field.options = Options(items=items)

        default_code = getattr(CONFIG.defaults, "default_currency", None)
        if default_code:
            currency_field.default_value = default_code
            for opt in items:
                if opt.value == default_code:
                    currency_field.default_value_text = opt.text
                    break

    # ------------- Builders ------------- #

    def get_filled_form(self, templateId: int) -> list:
        """Return a copy of the form with values from the record"""
        filled_form = copy.deepcopy(self.FORM)
        template = get_template_by_id(templateId)

        for field in filled_form.fields:
            fieldKey = field.key
            value = getattr(template, fieldKey)

            match fieldKey:
                case "isIncome":
                    field.default_value = value
                case "categoryId":
                    field.default_value = template.category.id
                    field.default_value_text = template.category.name
                case "accountId":
                    field.default_value = template.account.id
                    field.default_value_text = template.account.name
                case "currencyCode":
                    code = value or CONFIG.defaults.default_currency
                    field.default_value = code
                    opts = field.options.items if field.options else []
                    for opt in opts:
                        if opt.value == code:
                            field.default_value_text = opt.text
                            break
                case _:
                    field.default_value = str(value) if value is not None else ""

        return filled_form

    def get_form(self):
        """Return the base form with default values"""
        form = copy.deepcopy(self.FORM)
        return form
