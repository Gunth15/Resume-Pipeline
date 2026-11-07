from copy import Error
import time
from ollama import ChatResponse
from ollama import Client
import json
import yaml
import pathlib
import typst
from genson import SchemaBuilder


CASE_FILES = ("response.json", "profile.yaml", "resume.json", "job.txt", "resume.pdf")


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


def resume_prompt(job: str, profile: str) -> str:
    return f"""
    Using the user's profile information, which is between the <profile></profile>XML tags, create a resume tailored from the relevant job information, which is between the <job></job>XML tags.
    DO PICK the information that aligns best with the job information.
    DO MAKE THE RESUME ONE PAGE
    DO NOT MAKE UP INFORMATION THAT CAN NOT BE INFERRED FROM THE USER'S profile.
    PREFER WORK THATS IS NEWER
    The resume must be returned in JSON form.
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
        )

        if resp["message"]["content"] is None:
            raise TypeError("RESPONSE IS NOT THE EXPECTED FORMAT")

        content = resp["message"]["content"]

        self.key_phrases = json.loads(content)
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
        prompt = resume_prompt(json.dumps(self.key_phrases), json.dumps(self.profile))
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
        )

        if resp["message"]["content"] is None:
            raise TypeError("RESPONSE IS NOT THE EXPECTED FORMAT")

        content = resp["message"]["content"]

        self.resume = json.loads(content)
        return self.resume

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

        self.case_dir = str(case_dir)
        self.key_phrases = key_phrases
        self.job_description = job_description
        self.resume = resume

        return {
            "case_dir": self.case_dir,
            "key_phrases": self.key_phrases,
            "profile": self.profile,
            "profile_schema": self.profile_schema,
            "job_description": self.job_description,
            "resume": self.resume,
        }
