import argparse
import pathlib
from cli import ui, compile
from editor import Editor

DEFAULT_MODEL = "gemma4:e4b"
DEFAULT_PROFILE = "master.yaml"
DEFAULT_TEMPLATE = "template.typ"

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="resume-pipeline",
        description=(
            "Tailor a resume to a job description. "
            "JOB_DESCRIPTION may be a file or the job text itself."
        ),
    )

    parser.add_argument(
        "-m",
        "--model",
        default=DEFAULT_MODEL,
        help=f"Ollama model to use (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "-p",
        "--profile",
        default=DEFAULT_PROFILE,
        help=f"profile YAML file (default: {DEFAULT_PROFILE})",
    )
    parser.add_argument(
        "-t",
        "--template",
        default=DEFAULT_TEMPLATE,
        help=f"Typst template to compile (default: {DEFAULT_TEMPLATE})",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    _ = sub.add_parser("ui", help="Launch the Resume Pipeline UI")
    compile_parser = sub.add_parser(
        "compile",
        help="Run the resume pipeline without the interactive UI",
    )
    compile_parser.add_argument("job_description")

    return parser


if __name__ == "__main__":
    parser = build_parser()

    args = parser.parse_args()

    editor = Editor(model=args.model, profile=args.profile, template=args.template)

    if args.command == "ui":
        app = ui.ResumePipelineApp(editor, args.model)
        app.run()
        exit()

    if args.command == "compile":
        compile.run_pipeline(editor, args.job_description)
        exit()
    else:
        raise SystemExit("Invalid command")
