# Resume-Pipeline

Transforms your experience into a beautiful resume

## GOAL

[x] One Mega Data thread of your Work history, personal info, education + user definable extensions
[x] Parse job for key phrases, soft skills, hard skills , verbs, tools company, etc.
[ ] Ask the user questions to create to find more skill that might have been missed
[ ] Make a Final resume using a given Typst template (The AI must be able to understand Typst, fit everything on one page, and FOLLOW THE TEMPLATE EXACTLY)
[ ] Critique Data Thread

## Design constraints

- Templates will be in Typst and users will have to define the data used in the template as a contract
- Each generation will be its own savable case(Cases contain the skill extracted, job description, and the resume generated)

## Prof file structure

## Config file options

- Model: Which model to use
- Profile: The profile(\*.prof) file to use
- Save: Wether to save the case or not
- THEME: the theme, duh
