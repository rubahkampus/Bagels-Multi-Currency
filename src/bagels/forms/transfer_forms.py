import copy
from datetime import datetime

from rich.text import Text

from bagels.forms.form import Form, FormField, Option, Options
from bagels.managers.record_templates import get_transfer_templates
from bagels.models.record import Record
from bagels.config import CONFIG  # NEW


class TransferForm:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    # ------------ Blueprints ------------ #

    FORM = Form(
        fields=[
            FormField(
                placeholder="Label",
                title="Label / Template name",
                key="label",
                type="autocomplete",
                options=Options(),
                autocomplete_selector=False,
                is_required=True,
            ),
            FormField(
                title="Amount",
                key="amount",
                type="number",
                placeholder="0.00",
                min=0,
                is_required=True,
            ),
            FormField(
                title="Currency",
                key="currencyCode",
                type="autocomplete",
                options=Options(),
                is_required=False,
                placeholder="Leave empty for default currency",
            ),
            FormField(
                title="Date",
                key="date",
                type="dateAutoDay",
                placeholder="dd (mm) (yy)",
            ),
        ]
    )


    TEMPLATE_FORM = Form(
        fields=[
            FormField(
                title="Label",
                key="label",
                type="string",
                placeholder="Label",
                is_required=True,
            ),
            FormField(
                title="Amount",
                key="amount",
                type="number",
                placeholder="0.00",
                min=0,
                is_required=True,
            ),
            FormField(
                title="Currency",
                key="currencyCode",
                type="autocomplete",
                options=Options(),
                is_required=False,
                placeholder="Leave empty for default currency",
            ),
        ]
    )

    # ----------------- - ---------------- #

    def __init__(self, isTemplate: bool = False, defaultDate: str = None):
        self.isTemplate = isTemplate
        self.defaultDate = defaultDate
        self._populate_form_options()
        self._populate_currency_options()  # NEW

    # region Helpers
    # -------------- Helpers ------------- #

    def _populate_form_options(self):
        templates = get_transfer_templates()
        default_code = CONFIG.defaults.default_currency
        self.FORM.fields[0].options = Options(
            items=[
                Option(
                    text=template.label,
                    value=template.id,
                    postfix=Text(
                        f"{getattr(template, 'currencyCode', None) or default_code} {template.amount}",
                        style="yellow",
                    ),
                )
                for template in templates
            ]
        )
        # date is now index 3
        self.FORM.fields[3].default_value = self.defaultDate

        
    def _populate_currency_options(self):
        currencies_cfg = getattr(CONFIG, "currencies", None)
        if not currencies_cfg or not getattr(currencies_cfg, "supported", None):
            return

        def fill_for(form: Form):
            field = next(
                (f for f in form.fields if f.key == "currencyCode"),
                None,
            )
            if field is None:
                return

            items: list[Option] = []
            for cur in currencies_cfg.supported:
                label = f"{cur.code} ({cur.symbol})"
                items.append(Option(text=label, value=cur.code))

            field.options = Options(items=items)
            default_code = getattr(CONFIG.defaults, "default_currency", None)
            if default_code:
                field.default_value = default_code
                for opt in items:
                    if opt.value == default_code:
                        field.default_value_text = opt.text
                        break

        fill_for(self.FORM)
        fill_for(self.TEMPLATE_FORM)

    # region Builders
    # ------------- Builders ------------- #

    def get_filled_form(self, record: Record) -> Form:
        """Return a copy of the form with values from the record"""
        filled_form = copy.deepcopy(
            self.FORM if not self.isTemplate else self.TEMPLATE_FORM
        )

        if not record.isTransfer:
            return filled_form, []

        for field in filled_form.fields:
            fieldKey = field.key
            value = getattr(record, fieldKey)

            match fieldKey:
                case "date":
                    # if value is this month, simply set %d, else set %d %m %y
                    if value.month == datetime.now().month:
                        field.default_value = value.strftime("%d")
                    else:
                        field.default_value = value.strftime("%d %m %y")
                case "label":
                    field.default_value = str(value) if value is not None else ""
                    field.type = "string"  # disable autocomplete
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

    def get_form(self, hidden_fields: dict = {}):
        """Return the base form with default values"""
        form = copy.deepcopy(self.FORM if not self.isTemplate else self.TEMPLATE_FORM)
        for field in form.fields:
            key = field.key
            if key in hidden_fields:
                field.type = "hidden"
                if isinstance(hidden_fields[key], dict):
                    field.default_value = hidden_fields[key]["default_value"]
                    field.default_value_text = hidden_fields[key]["default_value_text"]
                else:
                    field.default_value = hidden_fields[key]
        return form
