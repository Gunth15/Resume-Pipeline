from ollama import ChatResponse
from ollama import Client
import json
import yaml
from genson import SchemaBuilder


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
    DO MAKE THE RESUM
    DO NOT MAKE UP INFORMATIONS THAT CAN NOT BE INFERRED FROM THE USER'S profile.
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

        self.profile = profile
        self.profile_schema = profile_schema
        self.resume = None

    def find_key_phrases(self, description: str):
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

        with open("response.json", "w+") as f:
            f.write(content)

        self.key_phrases = json.loads(content)
        return self.key_phrases

    def set_schema_from_profile(self, file: str):
        with open(file) as prof_file:
            profile = yaml.safe_load(prof_file)
            builder = SchemaBuilder()
            builder.add_object(profile)

            self.profile = profile
            self.profile_schema = builder.to_schema()
            return (self.profile, self.profile_schema)

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

        with open("resume.json", "w+") as f:
            f.write(content)

        self.resume = json.loads(content)
        return self.resume
