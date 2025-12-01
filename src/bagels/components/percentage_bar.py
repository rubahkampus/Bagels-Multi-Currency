from pydantic import BaseModel
from rich.color import Color as RichColor
from textual.app import ComposeResult
from textual.color import Color
from textual.containers import Container
from textual.widgets import Label, Static

from bagels.utils.currency import format_amount_default


class PercentageBarItem(BaseModel):
    name: str
    count: int
    color: str


class PercentageBar(Static):
    DEFAULT_CSS = """
    PercentageBar {
        layout: vertical;
        width: 1fr;
        height: auto;
    }
    
    PercentageBar > .bar-container {
        layout: horizontal;
        height: 1;
        width: 1fr;
        
        .bar {
            layout: horizontal;
            height: 1;
            width: 1fr;
            
            .empty-bar {
                hatch: right $panel-lighten-2;
                align-horizontal: center;
                
                Label {
                    padding: 0 1 0 1;
                }
            }
        }
    }
    
    
    PercentageBar > .labels-container {
        layout: vertical;
        height: auto;
        margin-top: 1;
        
        .bar-label {
            layout: horizontal;
            height: 1;
        }
        
        .bar-label > .percentage {
            margin-left: 2;
            color: $primary-background-lighten-3;
        }
    }
    
    """

    items: list[PercentageBarItem] = []
    total: int = 0

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.rounded = False

    def on_mount(self) -> None:
        self.rebuild()

    def set_total(self, total: int, rebuild: bool = False) -> None:
        self.total = total
        if rebuild:
            self.rebuild()

    def set_items(self, items: list[PercentageBarItem]) -> None:
        self.items = items
        self.rebuild()

    #  50%  50% 
    # ^-----======^
    def rebuild(self) -> None:
        # we first remove all existing items and labels
        for item in self.query(".bar-item"):
            item.remove()
        labels = self.query(".bar-label")
        labels_count = len(labels)
        items_count = len(self.items)

        prev_empty_bar = self.bar.query(".empty-bar")
        if len(self.items) == 0:
            if self.rounded:
                self.bar_start.styles.display = "none"
                self.bar_end.styles.display = "none"
            if len(prev_empty_bar) == 0:
                empty_bar = Container(Label("No data to display"), classes="empty-bar")
                self.bar.mount(empty_bar)
        else:
            if self.rounded:
                self.bar_start.styles.display = "block"
                self.bar_end.styles.display = "block"
            if len(prev_empty_bar) > 0:
                prev_empty_bar[0].remove()

        to_remove_count = labels_count - items_count
        if to_remove_count > 0:
            for i in range(to_remove_count):
                labels[i + items_count].remove()
        # we calculate the appropriate width for each item, with last item taking remaining space
        for i, item in enumerate(self.items):
            item_widget = Static(" ", classes="bar-item")
            color = item.color
            background_color = Color.from_rich_color(RichColor.parse(item.color)).hex
            # assign start and end colors
            if self.rounded:
                if i == 0:
                    self.bar_start.styles.color = background_color
                if i == len(self.items) - 1:
                    self.bar_end.styles.color = background_color
            # calculate percentage
            percentage = round((item.count / self.total) * 100)
            if (
                i + 1 > labels_count
            ):  # if we have more items than labels, we create a new label
                label_widget = Container(
                    Label(f"[{color}]●[/{color}] {item.name}", classes="name"),
                    Label(f"{percentage}% ({format_amount_default(item.count)})", classes="percentage"),
                    classes="bar-label",
                )
                self.labels_container.mount(label_widget)
            else:
                label = labels[i]
                label.query_one(".name").update(f"[{color}]●[/{color}] {item.name}")
                label.query_one(".percentage").update(f"{percentage}% ({item.count})")

            width = f"{percentage}%"
            if i == len(self.items) - 1:
                # Last item takes remaining space
                width = "1fr"

            item_widget.styles.width = width
            if self.rounded:
                item_widget.background = background_color
                if i > 0:
                    prev_background_color = Color.from_rich_color(
                        RichColor.parse(self.items[i - 1].color)
                    ).hex
                    item_widget.update(
                        f"[{prev_background_color} on {background_color}][/{prev_background_color} on {background_color}]"
                    )
            else:
                item_widget.styles.hatch = (
                    "/",
                    background_color,
                )

            self.bar.mount(item_widget)

    def compose(self) -> ComposeResult:
        self.bar_start = Label("", classes="bar-start")
        self.bar = Container(classes="bar")
        self.bar_end = Label("", classes="bar-end")
        self.labels_container = Container(classes="labels-container")
        with Container(classes="bar-container"):
            if self.rounded:
                yield self.bar_start
            yield self.bar
            if self.rounded:
                yield self.bar_end
        yield self.labels_container
