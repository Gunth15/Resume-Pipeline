import json
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import (
    Header,
    Footer,
    TextArea,
    Static,
    Button,
    RichLog,
)
from editor import Editor


class ResumePipelineApp(App):
    CSS = """
    Screen {
        layout: vertical;
    }

    #description {
        height: 1fr;
        border: round $primary;
    }

    #output {
        height: 1fr;
        border: round $success;
        padding: 1;
        overflow-y: auto;
    }

    #run {
        width: 100%;
        margin: 1 0;
    }
    """

    BINDINGS = [
        ("ctrl+r", "run_editor", "Run"),
        ("ctrl+q", "quit", "Quit"),
    ]

    def __init__(self):
        self.editor = Editor("qwen3.5:4b")
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Header()

        with Vertical():
            yield Static("Job Description")

            yield TextArea(
                "Developed scalable Python applications.\n"
                "Managed Linux servers.\n"
                "Implemented automated data validation.\n"
                "Experience with machine learning.",
                id="description",
            )

            yield Button(
                "Find Key Phrases",
                id="run",
                variant="primary",
            )

            yield RichLog(
                id="output",
                wrap=True,
                markup=False,
            )

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "run":
            self.action_run_editor()

    def action_run_editor(self) -> None:
        description = self.query_one(
            "#description",
            TextArea,
        ).text

        output = self.query_one("#output", RichLog)
        output.clear()

        try:
            result = self.editor.find_key_phrases(description)

            pretty_json = json.dumps(
                result,
                indent=2,
                ensure_ascii=False,
            )

            output.write(pretty_json)
            output.scroll_end()

        except Exception as e:
            output.write(f"Error: {e}")
            output.scroll_end()


if __name__ == "__main__":
    app = ResumePipelineApp()
    app.run()
