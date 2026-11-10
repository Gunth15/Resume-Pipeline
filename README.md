# Resume Pipeline

**One profile, many resumes.**

Resume Pipeline tailors a resume to a specific job posting using any local model using Ollama.
[Typst](https://typst.app) files are used as templates for generating to PDFs.
Keep your experience in one YAML file, paste in a job description, and get back a resume that speaks to
that role — without sending your personal data to a cloud service.

- **Local-first** — runs entirely against [Ollama](https://ollama.com) on your machine.
- **Profile-driven** — write your history once; every resume is generated from it.
- **Layout in your hands** — the PDF is produced by a Typst template you own.
- **Case files** — every run is saved so you can revisit, edit, and recompile it.

---

## How it works

1. **Summarize the job** — the LLM extracts the title, company, requirements,
   hard skills, soft skills, and tools from the posting.
2. **Answer a few questions** — it compares that summary against your profile and
   asks about the gaps and seniority expectations.
3. **Generate the resume** — your profile, the job summary, and your answers are
   turned into structured resume JSON.
4. **Compile** — the JSON is passed into your Typst template and rendered to PDF.

Everything is stored in a timestamped **case** directory, so a run is never lost.

## Requirements

| Dependency                            | Notes                                                                      |
| ------------------------------------- | -------------------------------------------------------------------------- |
| Python 3.10+                          | Uses modern type hints.                                                    |
| [Ollama](https://ollama.com/download) | Must be running locally.                                                   |
| An Ollama model                       | Any model you have pulled. The default is `gemma4:e4b` (set in `main.py`). |
| [Typst](https://typst.app)            | Installed automatically with the `typst` Python package.                   |

## Installation

```sh
git clone https://github.com/Gunth15/Resume-Pipeline.git
cd Resume-Pipeline

python3 -m venv .venc
res/bin/pip install -r requirements.txt
```

Start Ollama and pull a model:

```sh
ollama serve            # skip if it is already running
ollama pull gemma4:e4b  # or any other model you prefer
```

## Usage

### Command line

```sh
# Inline job description
./resume-pipeline compile "Senior Python developer with 5+ years of experience..."

# Job description from a file
./resume-pipeline compile job.txt

# Use a different profile, template, or model
./resume-pipeline -p my-profile.yaml -t my-template.typ -m qwen2.5:7b compile job.txt
```

`-m`, `-p`, and `-t` are global options, so they go **before** the subcommand.

```sh
python main.py compile job.txt
```

### Interactive UI

```sh
./resume-pipeline ui
```

The UI walks through the same pipeline with a sidebar for each stage:

1. Open **Summarize a job**, paste the description, and press `ctrl+x`.
2. Press `ctrl+s` to save the job and its summary to a case.
3. Switch to **Answer questions**, press `ctrl+x` to generate them, fill in your
   answers, then press `ctrl+s` to save them.
4. Open **Generate resume**, press `ctrl+x` to build the resume, then `ctrl+s` to
   write `resume.json` and compile the PDF.

| Key      | Action                                |
| -------- | ------------------------------------- |
| `q`      | Job summary                           |
| `w`      | Profile and its inferred schema       |
| `e`      | Interview questions                   |
| `r`      | Generated resume                      |
| `ctrl+x` | Run the action for the current screen |
| `ctrl+s` | Save the current screen to the case   |
| `ctrl+o` | Restore a previously saved case       |
| `ctrl+q` | Quit                                  |

## Options

| Option           | Default        | Description                              |
| ---------------- | -------------- | ---------------------------------------- |
| `-m, --model`    | `gemma4:e4b`   | Ollama model to use.                     |
| `-p, --profile`  | `master.yaml`  | Profile YAML file.                       |
| `-t, --template` | `template.typ` | Typst template that renders the PDF.     |
| `-h, --help`     | —              | Show help for the command or subcommand. |

## Cases

Each run creates a directory named after the company and timestamp (for example
`Acme-20261110-115024/`) containing:

| File             | Contents                                      |
| ---------------- | --------------------------------------------- |
| `job.txt`        | The original job description.                 |
| `response.json`  | Extracted job key phrases.                    |
| `profile.yaml`   | Snapshot of the profile used for this run.    |
| `questions.json` | Generated questions paired with your answers. |
| `resume.json`    | The tailored resume data.                     |
| `resume.pdf`     | The compiled resume.                          |

Cases are self-contained: you can restore one in the UI (`ctrl+o`) and recompile
its `resume.json` with `ctrl+s` without repeating the interview.

## Profile format

The profile is YAML. Its top-level keys are up to you, but they must match what
your Typst template reads. The bundled `template.typ` expects
`personal details`, `education`, `work_history`, and `projects`:

```yaml
personal details:
  name: Jane Doe
  phone: "+1 555 010 0000"
  email: jane@example.com
  linkedin: https://www.linkedin.com/in/jane-doe
  github: https://github.com/janedoe
  address: Shreveport, Louisiana
  citizenship: US Citizen

education:
  - school:
      institute: Example University
      primary: B.S. of Computer Science
      secondary: Cybersecurity
      status: Graduated May 2025

work_history:
  - employer: Example Corp
    title: Software Engineer
    city: Remote
    start: June 2025
    end: Present
    highlights:
      - Built and shipped an internal service used by 200 employees.
      - Cut build times by 40% by caching dependencies.

projects:
  - name: Example Project
    start: 2025
    end: Present
    link: https://github.com/janedoe/example
    highlights:
      - Designed a small web service with a local-first data model.
```

Write it like an autobiography: more detail gives the model more to work with.
The pipeline derives a JSON schema from whatever structure you use, so it can
only reference fields that exist in your profile.

## Templates

`template.typ` receives the generated resume JSON through Typst's `sys.inputs`:

```typst
#let source = json(bytes(sys.inputs.data))

#source.at("personal details").name
#for job in source.work_history [
  #job.title at #job.employer
]
```

Because the template is plain Typst, you can restyle, reorder, or rewrite the
layout freely. To use a custom template:

```sh
./resume-pipeline -t my-template.typ compile job.txt
```
