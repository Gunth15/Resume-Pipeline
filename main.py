import json

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.theme import Theme
from textual.widgets import (
    Button,
    ContentSwitcher,
    Footer,
    Header,
    Markdown,
    Static,
    TextArea,
)

from editor import Editor

PORTAL2_THEME = Theme(
    name="portal2",
    primary="#ff8c1a",
    secondary="#35b6ff",
    warning="#ffb347",
    error="#e05a4f",
    success="#35b6ff",
    accent="#35b6ff",
    foreground="#cfd3d8",
    background="#0c0d0f",
    surface="#1b1e23",
    panel="#14161a",
    boost="#2a2e35",
    dark=True,
    luminosity_spread=0.12,
    variables={
        "footer-key-foreground": "#ff8c1a",
        "input-selection-background": "#ff8c1a 35%",
        "block-cursor-background": "#ff8c1a",
        "block-cursor-foreground": "#0c0d0f",
    },
)


def as_json_markdown(data) -> str:
    return "```json\n" + json.dumps(data, indent=2, default=str) + "\n```"


class SideBarWidget(Vertical):
    def compose(self) -> ComposeResult:
        yield Static("Resume Pipeline", classes="brand")
        yield Static("Views", classes="section-title")

        yield Button("Summarize a job", id="nav-summarize", classes="nav")
        yield Button("View profile schema", id="nav-profile", classes="nav")
        yield Button("Generate resume", id="nav-resume", classes="nav")

        with Vertical(id="actions"):
            yield Static("Actions", classes="section-title")
            yield Button("Execute", id="exec", variant="primary")
            yield Button("Save case", id="save", variant="success")
            yield Static("", id="status")


class SummarizeJob(Vertical):
    def compose(self):
        yield Static("Summarize Job", classes="view-title")
        yield Static(
            "Paste a job description, then run Execute to extract key phrases.",
            classes="hint",
        )
        yield TextArea(
            "",
            placeholder="Paste the job description here...",
            id="job-input",
        )
        with VerticalScroll(classes="output"):
            yield Markdown("_No summary yet._", id="summary-output")

    def update_output(self, data) -> None:
        self.query_one("#summary-output", Markdown).update(as_json_markdown(data))


class ProfileView(Vertical):
    def compose(self):
        yield Static("Profile Schema", classes="view-title")
        yield Static(
            "Your loaded profile and the schema inferred from it.",
            classes="hint",
        )
        with VerticalScroll(classes="output"):
            yield Markdown("_Profile not loaded yet._", id="profile-output")

    def update_output(self, data) -> None:
        self.query_one("#profile-output", Markdown).update(as_json_markdown(data))


class GenerateResumeView(Vertical):
    def compose(self):
        yield Static("Generate Resume", classes="view-title")
        yield Static(
            "Run Execute to tailor a resume to the summarized job.",
            classes="hint",
        )
        with VerticalScroll(classes="output"):
            yield Markdown("_No resume generated yet._", id="resume-output")

    def update_output(self, data) -> None:
        self.query_one("#resume-output", Markdown).update(as_json_markdown(data))


class ResumePipelineApp(App):
    CSS_PATH = "layout.tcss"
    TITLE = "Resume Pipeline"
    SUB_TITLE = "Job-tailored resumes"
    BINDINGS = [
        ("q", "show_sum", "Summarize"),
        ("w", "show_profile", "Profile"),
        ("e", "show_resume", "Resume"),
        ("ctrl+x", "execute", "Execute"),
        ("ctrl+s", "save", "Save"),
        ("ctrl+q", "quit", "Quit"),
    ]

    def __init__(
        self,
        model: str = "gemma4:e4b",
        profile_path: str = "master.yaml",
    ):
        self.model = model
        self.editor = Editor(model, profile=profile_path)
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="body"):
            yield SideBarWidget(id="sidebar")
            with ContentSwitcher(initial="view-summarize", id="views"):
                yield SummarizeJob(id="view-summarize", classes="view")
                yield ProfileView(id="view-profile", classes="view")
                yield GenerateResumeView(id="view-resume", classes="view")
        yield Footer()

    def on_mount(self) -> None:
        self.register_theme(PORTAL2_THEME)
        self.theme = "portal2"
        self._update_status()
        self._highlight_nav("view-summarize")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id

        if button_id == "exec":
            self.action_execute()
            return
        if button_id == "save":
            self.action_save()
            return

        view = {
            "nav-summarize": "view-summarize",
            "nav-profile": "view-profile",
            "nav-resume": "view-resume",
        }.get(button_id)
        if view:
            self._switch_to(view)

    def _switch_to(self, view_id: str) -> None:
        self.query_one(ContentSwitcher).current = view_id
        self._highlight_nav(view_id)

        if view_id == "view-profile":
            self.query_one(ProfileView).update_output(self.editor.profile)

    def _highlight_nav(self, view_id: str) -> None:
        mapping = {
            "view-summarize": "nav-summarize",
            "view-profile": "nav-profile",
            "view-resume": "nav-resume",
        }
        for button in self.query(".nav").results(Button):
            button.set_class(button.id == mapping.get(view_id), "nav-active")

    def _update_status(self, message: str | None = None) -> None:
        if message is None:
            message = f"model: {self.model}"
            if self.editor.case_dir:
                message += f"\ncase: {self.editor.case_dir}"
        self.query_one("#status", Static).update(message)

    def action_show_sum(self) -> None:
        self._switch_to("view-summarize")

    def action_show_profile(self) -> None:
        self._switch_to("view-profile")

    def action_show_resume(self) -> None:
        self._switch_to("view-resume")

    def action_save(self) -> None:
        state = self.query_one(ContentSwitcher).current
        editor = self.editor

        try:
            if state == "view-summarize":
                editor.save_key_phrases()
            elif state == "view-profile":
                editor.save_profile()
            elif state == "view-resume":
                editor.save_resume()
        except Exception as error:
            self.notify(str(error), title="Save failed", severity="error")
            return

        self._update_status()
        self.notify(f"Saved to {editor.case_dir}", title="Case saved", severity="success")

    def action_execute(self) -> None:
        state = self.query_one(ContentSwitcher).current
        job_text = self.query_one("#job-input", TextArea).text
        self.query_one("#status", Static).update("Working...")
        self._execute(state, job_text)

    @work(thread=True, exclusive=True, group="execute")
    def _execute(self, state: str, job_text: str) -> None:
        try:
            if state == "view-summarize":
                if not job_text.strip():
                    raise ValueError("Paste a job description first.")
                result = self.editor.find_key_phrases(job_text)
                message = "Key phrases extracted."

            elif state == "view-profile":
                profile, schema = self.editor.set_profile_and_schema("master.yaml")
                result = {"profile": profile, "schema": schema}
                message = "Profile loaded."

            elif state == "view-resume":
                if self.editor.key_phrases is None:
                    raise ValueError("Summarize a job first.")
                result = self.editor.generate_resume()
                message = "Resume generated."

            else:
                return

            self.call_from_thread(self._show_result, state, result, message)
        except Exception as error:
            self.call_from_thread(self._exec_failed, error)

    def _show_result(self, state: str, result, message: str) -> None:
        view = {
            "view-summarize": SummarizeJob,
            "view-profile": ProfileView,
            "view-resume": GenerateResumeView,
        }[state]
        self.query_one(view).update_output(result)
        self._update_status()
        self.notify(message, title="Done", severity="success")

    def _exec_failed(self, error: Exception) -> None:
        self._update_status()
        self.notify(str(error), title="Execution failed", severity="error")


if __name__ == "__main__":
    app = ResumePipelineApp()
    app.run()
