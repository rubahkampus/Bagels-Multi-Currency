from datetime import datetime

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import (
    Label,
)

from bagels.components.autocomplete import AutoComplete, Dropdown, DropdownItem
from bagels.components.fields import Field, Fields
from bagels.config import CONFIG
from bagels.forms.form import Form, Option
from bagels.forms.record_forms import RecordForm
from bagels.managers.accounts import get_all_accounts_with_balance
from bagels.managers.persons import create_person, get_all_persons
from bagels.managers.record_templates import get_template_by_id
from bagels.modals.base_widget import ModalContainer
from bagels.modals.input import InputModal
from bagels.utils.validation import validateForm


class RecordModal(InputModal):
    isEditing = False

    BINDINGS = [
        Binding(
            CONFIG.hotkeys.record_modal.new_split,
            "add_split",
            "+split",
            priority=True,
        ),
        Binding(
            CONFIG.hotkeys.record_modal.new_paid_split,
            "add_paid_split",
            "+paid split",
            priority=True,
        ),
        Binding(
            CONFIG.hotkeys.record_modal.delete_last_split,
            "delete_last_split",
            "-last split",
            priority=True,
        ),
        Binding(
            CONFIG.hotkeys.record_modal.submit_and_template,
            "submit_and_template",
            "Submit & Template",
            priority=True,
        ),
    ]

    def __init__(
        self,
        title: str,
        form: Form = Form(),
        splitForm: Form = Form(),
        isEditing: bool = False,
        date: datetime = datetime.now(),
        *args,
        **kwargs,
    ):
        super().__init__(title, form, *args, **kwargs)
        self.record_form = RecordForm()
        self.splitForm = splitForm
        self.isEditing = isEditing
        if isEditing:
            self._bindings.key_to_bindings.clear()
            self.refresh_bindings()
        self.splitFormOneLength = len(self.record_form.get_split_form(0, False))
        self.splitCount = int(len(splitForm) / self.splitFormOneLength)
        self.persons = get_all_persons()
        self.accounts = get_all_accounts_with_balance()
        self.date = date
        self.shift_pressed = False

    # -------------- Helpers ------------- #

    def _get_splits_from_result(self, resultForm: dict):
        splits = []
        for i in range(0, self.splitCount):
            splits.append(
                {
                    "personId": resultForm[f"personId-{i}"],
                    "amount": resultForm[f"amount-{i}"],
                    "isPaid": resultForm[f"isPaid-{i}"],
                    "accountId": resultForm[f"accountId-{i}"],
                    "paidDate": resultForm[f"paidDate-{i}"],
                }
            )
        return splits

    def _get_split_widget(self, index: int, fields: Form, isPaid: bool):
        widget = Container(Fields(fields), id=f"split-{index}", classes="split")
        widget.border_title = "> Paid split <" if isPaid else "> Split <"
        return widget

    def _get_init_split_widgets(self):
        widgets = []
        for i in range(0, self.splitCount):
            oneSplitForm = Form(
                fields=self.splitForm.fields[
                    i * self.splitFormOneLength : (i + 1) * self.splitFormOneLength
                ]
            )
            # Find the isPaid field in the form fields for this split
            isPaid = False
            for field in oneSplitForm.fields:
                if field.key == f"isPaid-{i}":
                    isPaid = field.default_value
                    break
            widgets.append(self._get_split_widget(i, oneSplitForm, isPaid))
        return widgets

    def _update_errors(self, errors: dict):
        previousErrors = self.query(".error")
        for error in previousErrors:
            error.remove()
        for key, value in errors.items():
            field = self.query_one(f"#row-field-{key}")
            field.mount(Label(value, classes="error"))

    def on_auto_complete_created(self, event: AutoComplete.Created) -> None:
        name = event.item.create_option_text
        person = create_person({"name": name})
        for field in self.splitForm.fields:
            if field.key.startswith("personId"):
                field.options.items.append(Option(text=person.name, value=person.id))
        # update all person dropdowns with the new person
        for i in range(0, self.splitCount):
            dropdown: Dropdown = self.query_one(f"#dropdown-personId-{i}")
            dropdown.items.append(DropdownItem(person.name, "", ""))
        # set heldValue for the AutoComplete's input
        event.input.heldValue = person.id

    def on_auto_complete_selected(self, event: AutoComplete.Selected) -> None:
        if "field-label" in event.input.id:  # if the autocompleted field is the label field
            template = get_template_by_id(event.input.heldValue)  # get the template specified

            for field in self.form.fields:
                # never overwrite label or date from the template
                if field.key in ("label", "date"):
                    continue

                has_heldValue = field.type in ["autocomplete"]
                fieldWidget = self.query_one(f"#field-{field.key}")

                if not has_heldValue:
                    if field.type == "boolean":
                        fieldWidget.value = getattr(template, field.key)
                    else:
                        fieldWidget.value = str(getattr(template, field.key, "") or "")
                else:
                    template_value = getattr(template, field.key, None)
                    fieldWidget.heldValue = template_value

                    # For xxxId fields, show the related object's name
                    if "Id" in field.key and template_value is not None:
                        related_obj = getattr(
                            template,
                            field.key.replace("Id", ""),
                            None,
                        )
                        if related_obj is not None:
                            fieldWidget.value = str(getattr(related_obj, "name", ""))

                    # For autocomplete fields, also drive the controller so any side-effects fire
                    controller: Field = self.query_one(f"#field-{field.key}-controller")
                    if field.options and field.options.items:
                        for index, option in enumerate(field.options.items):
                            if option.value == template_value:
                                controller.handle_select_index(index)
                                break

            self.app.notify(
                title="Success",
                message="Template applied",
                severity="information",
                timeout=3,
            )

    # ------------- Callbacks ------------ #

    def action_add_paid_split(self):
        self.action_add_split(paid=True)

    def action_add_split(self, paid: bool = False):
        splits_container = self.query_one("#splits-container", Container)
        current_split_index = self.splitCount
        new_split_form = self.record_form.get_split_form(
            current_split_index, paid, defaultPaidDate=self.date
        )
        for field in new_split_form.fields:
            self.splitForm.fields.append(field)
        splits_container.mount(
            self._get_split_widget(current_split_index, new_split_form, paid)
        )
        # Use call_after_refresh to ensure the mount is complete
        splits_container.call_after_refresh(
            lambda: self.query_one(f"#field-personId-{current_split_index}").focus()
        )
        self.splitCount += 1

    def action_delete_last_split(self):
        if self.splitCount > 0:
            self.query_one(f"#split-{self.splitCount - 1}").remove()
            self.query_one(
                f"#dropdown-personId-{self.splitCount - 1}"
            ).remove()  # idk why this is needed
            dropdown_accountId = self.query(
                f"#dropdown-accountId-{self.splitCount - 1}"
            )
            if dropdown_accountId:
                dropdown_accountId[0].remove()
            for i in range(self.splitFormOneLength):
                self.splitForm.fields.pop()
            self.splitCount -= 1

    def action_submit_and_template(self) -> None:
        self.shift_pressed = True
        self.action_submit()

    def action_submit(self):
        resultRecordForm, errors, isValid = validateForm(self, self.form)
        resultSplitForm, errorsSplit, isValidSplit = validateForm(self, self.splitForm)
        if isValid and isValidSplit:
            resultSplits = self._get_splits_from_result(resultSplitForm)
            self.dismiss(
                {
                    "record": resultRecordForm,
                    "splits": resultSplits,
                    "createTemplate": self.shift_pressed,
                }
            )
            return
        self._update_errors({**errors, **errorsSplit})

    # -------------- Compose ------------- #

    def compose(self) -> ComposeResult:
        yield ModalContainer(
            Fields(self.form),
            Container(*self._get_init_split_widgets(), id="splits-container"),
        )
