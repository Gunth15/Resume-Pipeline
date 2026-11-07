import json
from textual.app import App, ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widgets import (
    Pretty,
    ContentSwitcher,
    Footer,
    TextArea,
    Static,
    Button,
)

from editor import Editor


class SideBarWidget(Static):
    def compose(self) -> ComposeResult:
        yield Button(
            "Summarize a job",
            id="summarize-job",
            variant="default",
        )

        yield Button(
            "View Profile Schema",
            id="profile-view",
            variant="default",
        )

        yield Button(
            "Generate Resume",
            id="generate-resume",
            variant="default",
        )

        yield Button(
            "Excute",
            id="exec",
            variant="error",
        )

        yield Button(
            "Save",
            id="save",
            variant="success",
        )


class SummarizeJob(Vertical):
    def compose(self):
        yield Static("Summarize Job")
        yield TextArea(
            "Paste the job description here...",
        )
        with VerticalScroll(id="profile-view"):
            yield Pretty(
                "Summary goes here",
            )


class ProfileView(Vertical):
    def compose(self):
        yield Static("View Profile in JSON")
        with VerticalScroll(id="profile-view"):
            yield Pretty("Profile not loaded yet")


class GenerateResumeView(Vertical):
    def compose(self):
        yield Static("Generate Resume")
        with VerticalScroll(id="profile-view"):
            yield Pretty("No resume generated yet")


class ResumePipelineApp(App):
    CSS_PATH = "layout.tcss"
    BINDINGS = [
        ("q", "show_sum", "Summarize view"),
        ("w", "show_profile", "Profile view"),
        ("e", "show_resume", "Generate view"),
        ("ctrl+s", "save", "save"),
        ("ctrl+x", "execute", "execute"),
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

        super().__init__()

    def compose(self) -> ComposeResult:
        yield SideBarWidget(id="sidebar")
        with ContentSwitcher(initial="summarize-job"):
            yield SummarizeJob(id="summarize-job")
            yield ProfileView(id="profile-view")
            yield GenerateResumeView(id="generate-resume")

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "exec":
            self.action_exec()
            return

        if event.button.id == "save":
            self.action_save()
            return

        self.query_one(ContentSwitcher).current = event.button.id

        editor = self.editor
        if event.button.id == "profile-view":
            self.query_one(ProfileView).query_one(Pretty).update(editor.profile)

    def action_show_sum(self) -> None:
        self.query_one(ContentSwitcher).current = "summarize-job"

    def action_show_profile(self) -> None:
        self.query_one(ContentSwitcher).current = "profile-view"

    def action_show_resume(self) -> None:
        self.query_one(ContentSwitcher).current = "generate-resume"

    def action_save(self) -> None:
        state = self.query_one(ContentSwitcher).current
        editor = self.editor

        match state:
            case "summarize-job":
                editor.save_key_phrases()

            case "profile-view":
                editor.save_profile()

            case "generate-resume":
                editor.save_resume()

    def action_exec(self) -> None:
        state = self.query_one(ContentSwitcher).current
        editor = self.editor

        match state:
            case "summarize-job":
                sj = self.query_one(SummarizeJob)
                text = sj.query_one(TextArea).text
                sum = editor.find_key_phrases(text)
                sj.query_one(Pretty).update(sum)
            case "profile-view":
                prof, _ = editor.set_profile_and_schema("master.yaml")
                self.query_one(ProfileView).query_one(Pretty).update(prof)
            case "generate-resume":
                resume = editor.generate_resume()
                self.query_one(GenerateResumeView).query_one(Pretty).update(resume)


if __name__ == "__main__":
    app = ResumePipelineApp()
    app.run()
