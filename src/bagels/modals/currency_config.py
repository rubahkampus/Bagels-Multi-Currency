# src/bagels/modals/currency_config.py

from __future__ import annotations

import copy
from typing import Optional

from bagels.config import CONFIG
from bagels.forms.form import Form, FormField, Option, Options
from bagels.modals.input import InputModal


class AddCurrencyForm:
    """Simple form for adding/updating a supported currency."""

    FORM = Form(
        fields=[
            FormField(
                title="Currency code",
                key="code",
                type="string",
                is_required=True,
                placeholder="e.g. USD",
            ),
            FormField(
                title="Symbol",
                key="symbol",
                type="string",
                is_required=False,
                placeholder="e.g. $ (optional)",
            ),
            FormField(
                title="Decimals",
                key="decimals",
                type="number",
                is_required=True,
                placeholder="e.g. 2",
                default_value="2",
            ),
        ]
    )

    @classmethod
    def get_form(cls, default_values: Optional[dict] = None) -> Form:
        form = copy.deepcopy(cls.FORM)
        if default_values:
            for field in form.fields:
                if field.key in default_values:
                    field.default_value = default_values[field.key]
        return form


class AddCurrencyModal(InputModal):
    """
    Modal: collects code / symbol / decimals.

    The actual write to config.yaml is done by the caller via a callback.
    """

    def __init__(
        self,
        title: str = "Add / update currency",
        default_values: Optional[dict] = None,
        *args,
        **kwargs,
    ):
        form = AddCurrencyForm.get_form(default_values=default_values)
        super().__init__(title=title, form=form, *args, **kwargs)


class DefaultCurrencyForm:
    """Form that lets the user pick the default from supported currencies."""

    @classmethod
    def get_form(cls) -> Form:
        items: list[Option] = []

        default_code = CONFIG.defaults.default_currency
        currencies = getattr(CONFIG, "currencies", None)
        supported = getattr(currencies, "supported", []) if currencies else []

        for c in supported:
            label = c.code
            if getattr(c, "symbol", None):
                label = f"{c.code} ({c.symbol})"
            items.append(Option(text=label, value=c.code))

        return Form(
            fields=[
                FormField(
                    title="Default currency",
                    key="code",
                    type="autocomplete",
                    is_required=True,
                    placeholder="Select default currency",
                    options=Options(items=items),
                    default_value=default_code,
                    default_value_text=default_code,
                )
            ]
        )


class DefaultCurrencyModal(InputModal):
    """
    Modal: lets the user choose default currency via autocomplete.

    Caller applies the selection via set_default_currency().
    """

    def __init__(self, title: str = "Change default currency", *args, **kwargs):
        form = DefaultCurrencyForm.get_form()
        super().__init__(title=title, form=form, *args, **kwargs)
