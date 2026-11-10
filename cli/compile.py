import pathlib
import sys
import textwrap
from typing import Sequence

from editor import Editor


def ask_questions(questions: Sequence[str], stream=sys.stdout) -> list[str]:
    """Prompt for one answer per question and return the answers."""
    answers: list[str] = []
    total = len(questions)

    for index, question in enumerate(questions, start=1):
        print(f"\nQuestion {index}/{total}", file=stream)
        print(textwrap.fill(str(question), width=88), file=stream)
        try:
            answer = input("Answer (press Enter to skip): ")
        except EOFError:
            answer = ""
        answers.append(answer.strip())

    return answers


def read_job_description(job_desc: str | pathlib.Path) -> str:
    """Return the job text, reading it from a file when a path was given."""
    if isinstance(job_desc, pathlib.Path):
        return job_desc.read_text()

    candidate = pathlib.Path(job_desc).expanduser()
    try:
        if candidate.is_file():
            return candidate.read_text()
    except OSError:
        pass

    return job_desc


def run_pipeline(
    editor: Editor,
    job_desc: str | pathlib.Path,
) -> pathlib.Path:
    print("\n[1/4] Extracting job key phrases...")

    desc = read_job_description(job_desc)

    key_phrases = editor.find_key_phrases(desc)
    editor.save_key_phrases()
    if isinstance(key_phrases, dict):
        details = " - ".join(
            str(value)
            for value in (key_phrases.get("company"), key_phrases.get("job"))
            if value
        )
        if details:
            print(f"      {details}")
    print(f"      Case: {editor.case_dir}")

    print("[2/4] Generating questions...")
    questions = editor.generate_questions()
    answers = ask_questions(questions)

    print("\nSaving profile and answers...")
    editor.save_profile()
    editor.save_questions(answers)

    print("[3/4] Generating tailored resume...")
    editor.generate_resume()

    print("[4/4] Compiling PDF...")
    editor.save_resume()

    pdf_path = pathlib.Path(editor.case_dir) / "resume.pdf"
    print(f"\nResume: {pdf_path}")
    return pdf_path
