# src/bagels/modals/currency_rate.py

import copy
from typing import Optional

from textual.app import ComposeResult
from textual.widgets import Label

from bagels.components.fields import Fields
from bagels.config import CONFIG
from bagels.forms.form import Form, FormField, Option, Options
from bagels.modals.base_widget import ModalContainer
from bagels.modals.input import InputModal
from bagels.utils.validation import validateForm


class CurrencyRateForm:
    FORM = Form(
        fields=[
            FormField(
                title="From currency",
                key="fromCode",
                type="autocomplete",
                options=Options(),
                is_required=True,
                placeholder="Select base currency",
            ),
            FormField(
                title="To currency",
                key="toCode",
                type="autocomplete",
                options=Options(),
                is_required=True,
                placeholder="Select quote currency",
            ),
            FormField(
                title="Rate (1 FROM = ... TO)",
                key="rate",
                type="number",
                is_required=True,
                placeholder="Example: 1 USD = 15000 IDR → enter 15000",
            ),
        ]
    )

    @classmethod
    def _populate_currency_options(
        cls, form: Form, default_values: Optional[dict] = None
    ) -> None:
        """
        Fill fromCode/toCode options from CONFIG.currencies.supported.

        - Text:  "USD ($)" or "JPY" if symbol missing
        - Value: "USD"
        - Uses default_values['fromCode'/'toCode'] if provided, else
          defaults 'toCode' to CONFIG.defaults.default_currency.
        """
        default_values = default_values or {}

        currencies_cfg = getattr(CONFIG, "currencies", None)
        if not currencies_cfg or not getattr(currencies_cfg, "supported", None):
            return

        # Build a base list of options once
        base_items: list[Option] = []
        for cur in currencies_cfg.supported:
            symbol = getattr(cur, "symbol", None) or ""
            label = f"{cur.code} ({symbol})" if symbol else cur.code
            base_items.append(Option(text=label, value=cur.code))

        default_code = getattr(CONFIG.defaults, "default_currency", None)

        for field in form.fields:
            if field.key not in ("fromCode", "toCode"):
                continue

            # Give each field its own Options instance to avoid shared mutation
            field.options = Options(items=list(base_items))

            # Decide which code should be selected for this field
            code = default_values.get(field.key)
            if code:
                code = str(code).upper()
            elif field.key == "toCode" and default_code:
                code = default_code

            if not code:
                continue

            field.default_value = code
            # Also set default_value_text so the label appears instead of raw code
            for opt in field.options.items:
                if opt.value == code:
                    field.default_value_text = opt.text
                    break

    @classmethod
    def get_form(cls, default_values: dict | None = None) -> Form:
        """
        Build a form instance, applying optional default_values.

        default_values may contain:
            - fromCode: str
            - toCode: str
            - rate: float|str
        """
        form = copy.deepcopy(cls.FORM)
        default_values = default_values or {}

        for field in form.fields:
            if field.key not in default_values:
                continue
            raw = default_values[field.key]
            if raw is None:
                continue

            # Textual inputs expect strings; convert numerics
            if field.key == "rate":
                field.default_value = str(raw)
            else:
                field.default_value = str(raw)

        cls._populate_currency_options(form, default_values)
        return form


class CurrencyRateModal(InputModal):
    def __init__(
        self,
        title: str = "Set manual exchange rate",
        default_values: dict | None = None,
        current_rate_text: str | None = None,
        *args,
        **kwargs,
    ):
        self.current_rate_text = current_rate_text
        form = CurrencyRateForm.get_form(default_values=default_values)
        super().__init__(title=title, form=form, *args, **kwargs)

    def action_submit(self) -> None:
        # Same pattern as InputModal, with extra same-currency guard
        resultForm, errors, isValid = validateForm(self, self.form)

        if isValid:
            from_code = (resultForm.get("fromCode") or "").strip().upper()
            to_code = (resultForm.get("toCode") or "").strip().upper()

            if from_code == to_code:
                isValid = False
                errors["toCode"] = "From and To currencies must be different."

        if isValid:
            # Normalize codes to uppercase before returning
            resultForm["fromCode"] = (resultForm.get("fromCode") or "").strip().upper()
            resultForm["toCode"] = (resultForm.get("toCode") or "").strip().upper()
            self.dismiss(resultForm)
            return

        # show errors
        previousErrors = self.query(".error")
        for error in previousErrors:
            error.remove()
        for key, value in errors.items():
            field = self.query_one(f"#row-field-{key}")
            field.mount(Label(value, classes="error"))

    def compose(self) -> ComposeResult:
        """
        Same structure as InputModal.compose, but with an optional
        'Current: 1 XXX ≈ YYY' hint below the fields.
        """
        fields_widget = Fields(self.form)

        if self.current_rate_text:
            footer = Label(self.current_rate_text, classes="current-rate-hint")
            yield ModalContainer(fields_widget, footer)
        else:
            yield ModalContainer(fields_widget)