from ollama import ChatResponse
from ollama import Client
import json


def key_phrases_prompt(description: str) -> str:
    return f"""
    Read the job post and return relevant information. The job is inside <text></text>XML tags.
    <text>
    {description}
    </text>
    Based on the job post, return the following information as a JSON blob. Match the schema below EXACTLY. Do not include a preamble in your response.
    ```json
    {{
        'company' : <>The company/organization the job is for. String or Null.</>,
        'requirements' : <>The requirements for the job post. List of requirements or null.</> {{
            'type' : <>Type of the requirement. Value is either "education", "technical", or "senority"</>,
            'importance' : <>Is the requirement prefered or required. Value is prefered or required</>,
            'description' : <>A summarised version of the requirement found. String or null</>,

        }},
        'hard_skills' : <>Skills that are earned via experience and time in the craft. List of strings or null</>,
        'soft_skills' : <>Skills that are earned from working with others. List of strings or null</>,
        'tools' : <>Tools the job posting ask for. List of string or null</>,
    }}
    ```
    """


class Editor:
    def __init__(self, model="") -> None:
        self.model = model
        self.client = Client()

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
        )

        if resp.message.content is None:
            raise TypeError("RESPONSE IS NOT THE EXPECTED FORMAT")

        content = resp.message.content

        with open("response.json", "w+") as f:
            f.write(content)

        return json.loads(content)
