import json

from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import (
    Header,
    Footer,
    TextArea,
    Static,
    Button,
    RichLog,
)

from editor import Editor


class ProfileSchemaScreen(Screen):
    BINDINGS = [
        ("escape", "go_back", "Back"),
    ]

    CSS = """
    #schema {
        height: 1fr;
        border: round $primary;
    }

    #back {
        width: 100%;
        margin: 1 0;
    }
    """

    def __init__(self, schema: dict):
        super().__init__()
        self.schema = schema

    def compose(self) -> ComposeResult:
        yield Header()

        yield TextArea(
            json.dumps(
                self.schema,
                indent=2,
                ensure_ascii=False,
            ),
            id="schema",
            read_only=True,
        )

        yield Button(
            "Back",
            id="back",
            variant="primary",
        )

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.action_go_back()

    def action_go_back(self) -> None:
        self.app.pop_screen()


class ResumeGenerationScreen(Screen):
    BINDINGS = [
        ("escape", "go_back", "Back"),
    ]

    CSS = """
    #resume {
        height: 1fr;
        border: round $success;
        padding: 1;
        overflow-y: auto;
    }

    #generate, #back {
        width: 100%;
        margin: 1 0;
    }
    """

    def __init__(self, editor: Editor):
        super().__init__()
        self.editor = editor

    def compose(self) -> ComposeResult:
        yield Header()

        yield Static("Generated Resume")

        yield RichLog(
            id="resume",
            wrap=True,
            markup=False,
        )

        yield Button(
            "Generate Resume",
            id="generate",
            variant="success",
        )

        yield Button(
            "Back",
            id="back",
            variant="primary",
        )

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "generate":
            self.action_generate_resume()

        elif event.button.id == "back":
            self.action_go_back()

    def action_generate_resume(self) -> None:
        output = self.query_one("#resume", RichLog)
        output.clear()

        if not getattr(self.editor, "key_phrases", None):
            output.write("Extract key phrases from a job description first.")
            return

        try:
            result = self.editor.generate_resume()

            if isinstance(result, str):
                result = json.loads(result)

            output.write(
                json.dumps(
                    result,
                    indent=2,
                    ensure_ascii=False,
                )
            )

            output.scroll_end()

        except Exception as e:
            output.write(f"Error generating resume: {e}")
            output.scroll_end()

    def action_go_back(self) -> None:
        self.app.pop_screen()


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

    #run, #schema, #resume {
        width: 100%;
        margin: 1 0;
    }
    """

    BINDINGS = [
        ("ctrl+r", "run_editor", "Extract Key Phrases"),
        ("ctrl+s", "show_schema", "Profile Schema"),
        ("ctrl+g", "show_resume", "Generate Resume"),
        ("ctrl+q", "quit", "Quit"),
    ]

    def __init__(
        self,
        model: str = "gemma4:e4b",
        profile_path: str = "master.yaml",
    ):
        self.editor = Editor(
            model,
            profile=profile_path,
        )

        self.profile_path = profile_path

        super().__init__()

    def compose(self) -> ComposeResult:
        yield Header()

        with Vertical():
            yield Static("Job Description")

            yield TextArea(
                "Paste the job description here...",
                id="description",
            )

            yield Button(
                "Find Key Phrases",
                id="run",
                variant="primary",
            )

            yield Button(
                "View Profile Schema",
                id="schema",
                variant="default",
            )

            yield Button(
                "Generate Resume",
                id="resume",
                variant="success",
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

        elif event.button.id == "schema":
            self.action_show_schema()

        elif event.button.id == "resume":
            self.action_show_resume()

    def action_run_editor(self) -> None:
        description = self.query_one(
            "#description",
            TextArea,
        ).text

        output = self.query_one("#output", RichLog)
        output.clear()

        try:
            result = self.editor.find_key_phrases(description)

            output.write(
                json.dumps(
                    result,
                    indent=2,
                    ensure_ascii=False,
                )
            )

            output.scroll_end()

        except Exception as e:
            output.write(f"Error extracting key phrases: {e}")

            output.scroll_end()

    def action_show_schema(self) -> None:
        try:
            self.push_screen(ProfileSchemaScreen(self.editor.profile_schema))

        except Exception as e:
            output = self.query_one(
                "#output",
                RichLog,
            )

            output.write(f"Error loading profile schema: {e}")

            output.scroll_end()

    def action_show_resume(self) -> None:
        if not getattr(
            self.editor,
            "key_phrases",
            None,
        ):
            output = self.query_one(
                "#output",
                RichLog,
            )

            output.write("Please extract key phrases from a job description first.")

            output.scroll_end()
            return

        self.push_screen(ResumeGenerationScreen(self.editor))


if __name__ == "__main__":
    app = ResumePipelineApp()
    app.run()
