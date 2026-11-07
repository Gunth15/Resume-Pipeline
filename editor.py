from copy import Error
import time
from ollama import ChatResponse
from ollama import Client
import json
import yaml
import pathlib
import typst
from genson import SchemaBuilder


CASE_FILES = (
    "response.json",
    "profile.yaml",
    "resume.json",
    "questions.json",
    "job.txt",
    "resume.pdf",
)

# The resume prompt includes the profile, job data, and all Q&A. With Ollama's
# default 4096-token context this can be cut off mid-JSON, so give it room.
CHAT_OPTIONS = {
    "num_ctx": 16384,
    "num_predict": 4096,
}


def response_content(resp, label: str) -> str:
    """Get response text, with a useful error when generation was cut off."""
    if resp.get("done_reason") == "length":
        raise ValueError(
            f"{label}: the model response was cut off at the token limit. "
            "Try increasing num_ctx/num_predict or shortening the questions."
        )

    content = resp["message"]["content"]
    if content is None:
        raise TypeError(f"{label}: response is not the expected format.")
    return content


def parse_json_response(content: str, label: str):
    """Parse model JSON, reporting truncation instead of a raw decoder error."""
    try:
        return json.loads(content)
    except json.JSONDecodeError as error:
        snippet = content[max(0, error.pos - 80) : error.pos + 80]
        raise ValueError(
            f"{label}: the model returned invalid JSON "
            f"({error.msg} at line {error.lineno}, column {error.colno}). "
            "The response may have been truncated. Try increasing num_ctx "
            "or shortening the questions.\n"
            f"Near: {snippet!r}"
        ) from error


def find_cases(root="."):
    """Return saved case directories under root, newest first."""
    root_path = pathlib.Path(root)
    if not root_path.is_dir():
        return []

    cases = [
        entry
        for entry in root_path.iterdir()
        if entry.is_dir() and any((entry / name).exists() for name in CASE_FILES)
    ]
    return sorted(cases, key=lambda case: case.stat().st_mtime, reverse=True)


def case_label(case_path) -> str:
    """Build a human readable label for a saved case."""
    label = pathlib.Path(case_path).name
    response_file = pathlib.Path(case_path) / "response.json"
    if not response_file.exists():
        return label

    try:
        with open(response_file) as response:
            data = json.load(response)
    except (OSError, json.JSONDecodeError):
        return label
    if not isinstance(data, dict):
        return label

    details = " - ".join(
        str(value) for value in (data.get("company"), data.get("job")) if value
    )
    return f"{details} ({label})" if details else label


def key_phrases_prompt(description: str) -> str:
    return f"""
    Read the job post and return relevant information. The job is inside <text></text>XML tags.
    <text>
    {description}
    </text>
    Based on the job post, return the following information as a JSON blob. Match the schema below EXACTLY. Do not include a preamble in your response.
    ```json
    {{
        'job' : <>Job title. String or Null.</>,
        'company' : <>The company/organization the job is for. String or Null.</>,
        'requirements' : <>The requirements for the job post. List of requirements or null.</> {{
            'type' : <>Type of the requirement. Value is either "education", "technical", or "seniority"</>,
            'importance' : <>Is the requirement prefered or required. Value is prefered or required</>,
            'description' : <>A summarised version of the requirement found. String or null</>,

        }},
        'hard_skills' : <>Skills that are earned via experience and time in the craft. List of strings or null</>,
        'soft_skills' : <>Skills that are earned from working with others. List of strings or null</>,
        'tools' : <>Tools the job posting ask for. List of string or null</>,
    }}
    ```
    """


def resume_prompt(job: str, profile: str, qa: str) -> str:
    return f"""
    Using the user's profile information, between the <profile></profile>XML tags with the questions and answers between the <QA></QA>XML tags to create a resume tailored from the relevant job information, which is between the <job></job>XML tags.
    DO PICK the information that aligns best with the job information.
    DO MAKE THE RESUME ONE PAGE
    DO NOT MAKE UP INFORMATION THAT CAN NOT BE INFERRED FROM THE USER'S profile.
    PREFER WORK THATS IS NEWER
    The resume must be returned in JSON form.
    <profile>
        {profile}
    </profile>
    <QA>
        {qa}
    </QA>
    <job>
        {job}
    </job>
    """


def question_prompt(job: str, profile: str) -> str:
    return f"""
    Using the user's profile information, which is between the <profile></profile>XML tags, create a series of questions to ask the user that relates to the necesarry job information which is between the <job></job>XML tags.
    DO PICK the information that aligns best with the job information.
    DO ASK RELEVANT QUESTIONS BASED ON COMPANY.
    DO ASK RELEVANT QUESTIONS BASED ON SENORITY.
    DO ASK RELEVANT QUESTIONS BASED ON PROFILE EXPERIENCE.
    TRY TO ASK QUESTIONS TO FILL IN GAPS BETWEEN RESUME AND GIVEN JOB INFORMATION.
    The questions must be a JSON string list.
    <profile>
        {profile}
    </profile>
    <job>
        {job}
    </job>
    """


def schema_from_profile(file: str):
    with open(file) as prof_file:
        profile = yaml.safe_load(prof_file)
        builder = SchemaBuilder()
        builder.add_object(profile)

        profile_schema = builder.to_schema()
        return (profile, profile_schema)


class Editor:
    def __init__(self, model="", profile="master.yaml") -> None:
        self.model = model
        self.client = Client()

        (profile, profile_schema) = schema_from_profile(profile)

        self.case_dir = None
        self.profile = profile
        self.key_phrases = None
        self.profile_schema = profile_schema
        self.resume = None
        self.job_description = None
        self.questions = None
        self.answers = []

    def create_case_directory(self):
        timestamp = time.strftime("%Y%m%d-%H%M%S")

        company = self.key_phrases.get("company") if self.key_phrases else None

        if company:
            dir = f"./{company}-{timestamp}"
        else:
            dir = f"./case-{timestamp}"

        pathlib.Path(dir).mkdir()
        self.case_dir = dir

    def find_key_phrases(self, description: str):
        self.job_description = description
        prompt = key_phrases_prompt(description)
        resp: ChatResponse = self.client.chat(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            format={
                "type": "object",
                "properties": {
                    "job": {"type": ["string", "null"]},
                    "company": {"type": ["string", "null"]},
                    "requirements": {
                        "type": ["array", "null"],
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {
                                    "type": "string",
                                    "enum": ["education", "technical", "senority"],
                                },
                                "importance": {
                                    "type": "string",
                                    "enum": ["preferred", "required"],
                                },
                                "description": {"type": ["string", "null"]},
                            },
                            "required": ["type", "importance", "description"],
                        },
                    },
                    "hard_skills": {
                        "type": ["array", "null"],
                        "items": {"type": "string"},
                    },
                    "soft_skills": {
                        "type": ["array", "null"],
                        "items": {"type": "string"},
                    },
                    "tools": {"type": ["array", "null"], "items": {"type": "string"}},
                },
                "required": [
                    "company",
                    "requirements",
                    "hard_skills",
                    "soft_skills",
                    "tools",
                ],
            },
            think=False,
            options=CHAT_OPTIONS,
        )

        content = response_content(resp, "Job summary")
        self.key_phrases = parse_json_response(content, "Job summary")
        return self.key_phrases

    def save_key_phrases(self):
        if self.case_dir is None:
            self.create_case_directory()

        if self.job_description is not None:
            with open(f"{self.case_dir}/job.txt", "w+") as f:
                f.write(self.job_description)

        with open(f"{self.case_dir}/response.json", "w+") as f:
            json.dump(self.key_phrases, f)

    def set_profile_and_schema(self, file: str):
        with open(file) as prof_file:
            profile = yaml.safe_load(prof_file)
            builder = SchemaBuilder()
            builder.add_object(profile)

            self.profile = profile
            self.profile_schema = builder.to_schema()
            return (self.profile, self.profile_schema)

    def save_profile(self):
        if self.case_dir is None:
            self.create_case_directory()
        with open(f"{self.case_dir}/profile.yaml", "w+") as f:
            yaml.dump(self.profile, f)

    def generate_resume(self):
        qa = (
            [
                {
                    "question": question,
                    "answer": self.answers[index] if index < len(self.answers) else "",
                }
                for index, question in enumerate(self.questions)
            ]
            if self.questions is not None
            else "No Questions and Answers found"
        )
        prompt = resume_prompt(
            json.dumps(self.key_phrases),
            json.dumps(self.profile),
            json.dumps(qa),
        )
        resp: ChatResponse = self.client.chat(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            format=self.profile_schema,
            think=False,
            options=CHAT_OPTIONS,
        )

        content = response_content(resp, "Resume")
        self.resume = parse_json_response(content, "Resume")
        return self.resume

    def generate_questions(self):
        job = self.key_phrases if self.key_phrases is not None else self.job_description
        if job is None:
            raise ValueError("Summarize a job first.")

        prompt = question_prompt(json.dumps(job), json.dumps(self.profile))
        resp: ChatResponse = self.client.chat(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            format={
                "type": "array",
                "items": {
                    "type": "string",
                },
            },
            think=False,
            options=CHAT_OPTIONS,
        )

        content = response_content(resp, "Questions")
        questions = parse_json_response(content, "Questions")
        if not isinstance(questions, list):
            raise TypeError(f"Questions: expected a JSON list, got {type(questions).__name__}.")

        self.questions = [str(question) for question in questions]
        self.answers = ["" for _ in self.questions]
        return self.questions

    def save_questions(self, answers=None):
        if self.questions is None:
            raise Error("Generate questions first.")
        if self.case_dir is None:
            self.create_case_directory()

        if answers is not None:
            self.answers = list(answers)

        payload = [
            {
                "question": question,
                "answer": self.answers[index] if index < len(self.answers) else "",
            }
            for index, question in enumerate(self.questions)
        ]
        with open(f"{self.case_dir}/questions.json", "w+") as f:
            json.dump(payload, f, indent=2)

    def save_resume(self):
        if self.resume is None:
            raise Error("Generate a resume first.")
        if self.case_dir is None:
            self.create_case_directory()
        with open(f"{self.case_dir}/resume.json", "w+") as f:
            json.dump(self.resume, f, indent=2)
        typst.compile(
            "resume.typ",
            output=f"{self.case_dir}/resume.pdf",
            sys_inputs={"data": json.dumps(self.resume)},
        )

    def restore_case(self, case_path):
        """Load a saved case back into the editor and return its state."""
        case_dir = pathlib.Path(case_path)
        if not case_dir.is_dir():
            raise FileNotFoundError(f"Case directory not found: {case_dir}")
        if not any((case_dir / name).exists() for name in CASE_FILES):
            raise ValueError(f"No saved case data found in {case_dir}")

        key_phrases = None
        response_file = case_dir / "response.json"
        if response_file.exists():
            with open(response_file) as f:
                key_phrases = json.load(f)

        profile_file = case_dir / "profile.yaml"
        if profile_file.exists():
            with open(profile_file) as f:
                profile = yaml.safe_load(f)
            builder = SchemaBuilder()
            builder.add_object(profile)
            self.profile = profile
            self.profile_schema = builder.to_schema()

        job_file = case_dir / "job.txt"
        job_description = job_file.read_text() if job_file.exists() else None

        resume = None
        resume_file = case_dir / "resume.json"
        if resume_file.exists():
            with open(resume_file) as f:
                resume = json.load(f)

        questions = None
        answers = []
        questions_file = case_dir / "questions.json"
        if questions_file.exists():
            with open(questions_file) as f:
                saved_questions = json.load(f)
            if isinstance(saved_questions, list):
                questions = []
                for entry in saved_questions:
                    if isinstance(entry, dict):
                        questions.append(entry.get("question", ""))
                        answers.append(entry.get("answer", ""))
                    else:
                        questions.append(str(entry))
                        answers.append("")

        self.case_dir = str(case_dir)
        self.key_phrases = key_phrases
        self.job_description = job_description
        self.resume = resume
        self.questions = questions
        self.answers = answers

        return {
            "case_dir": self.case_dir,
            "key_phrases": self.key_phrases,
            "profile": self.profile,
            "profile_schema": self.profile_schema,
            "job_description": self.job_description,
            "resume": self.resume,
            "questions": self.questions,
            "answers": self.answers,
        }
