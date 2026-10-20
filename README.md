# Career Starter

**English** · [Українська](README.uk.md)

A local job-search workspace for use with Codex or Claude Code. Add your CV,
complete a short onboarding conversation, and get job leads, a learning plan
and tailored CVs with a mandatory natural-language review.

It supports different professions, first jobs, career changes and returning
after a break. Your answers define the profile and criteria. There is no
preset profession, salary threshold or “ideal candidate”.

## Get started

You need Python 3.10 or newer and a working Codex or Claude Code setup. The
Python tool uses only the standard library and needs no separate API key.
Job-feed searches require internet access.

Codex or Claude Code conducts onboarding, writes and edits your CV, and refines
the learning plan. Python commands manage local files, retrieve job listings
and check preparation stages. There is no language model embedded in Python.

1. Download a clean copy and extract it into its own folder.
2. Open that folder in Codex or Claude Code.
3. Attach your CV, provide an accessible file path, or put it in `local/inbox/`.
4. Ask your assistant:

   > Read AGENTS.md and guide me through onboarding. Here is my CV. Ask only
   > what is missing for the search, confirm my facts and criteria with me,
   > find relevant jobs and create a realistic learning plan.

The assistant should carry out the work. If you do not have a CV yet, start
with a description of your experience, education or desired work.

To start manually:

```text
python career.py init
python career.py import-cv "PATH_TO_CV"
python career.py status
python career.py portal
```

Use `python3` instead of `python` if that is your system's Python command.
Markdown, TXT and DOCX are supported. PDF extraction requires `pdftotext`;
a scanned PDF may need the assistant's document-reading tools or a text copy.
An extraction failure does not mean you have no experience.

## Language

The portal opens in **English** by default. Use **EN / УК** at the top right to
switch between English and Ukrainian. Your choice is remembered in that browser
and survives a page reload. Job descriptions and saved documents keep their
original language.

Use the **Dark theme / Light theme** button beside the language switch to change
appearance. The first visit follows your system theme; an explicit choice is
saved in that browser and applied before the page is drawn.

Assistant onboarding also starts in English unless you request another language
or write in Ukrainian. The portal's onboarding prompt follows its selected
language. Choose your conversation and learning-plan language with the assistant;
confirm the CV language separately for each application.

Onboarding takes place in the assistant chat. The portal currently displays
progress and instructions; it does not have a CV upload form or onboarding wizard.

## Onboarding

Your assistant reads the CV, summarizes the facts and asks a few questions:
what work to look for, where and in which working arrangement, working languages,
important conditions, and realistic weekly learning time. If your direction is
unclear, it helps compare options against your experience and actual vacancies.

You do not need to explain a career break or share family or other sensitive
details. You decide whether to include them. Unknown information stays unknown;
the assistant must not invent experience, tools, achievements or language levels.

After you confirm the facts, the assistant creates your private profile, master
CV and evidence ledger. The technical command is:

```text
python career.py onboard --profile local/profile-input.json
```

See [templates/profile.example.json](templates/profile.example.json) for the
format. It contains synthetic examples to replace with your own information.
`confirmed` becomes `true` only after you confirm the profile.

## Search and learn

```text
python career.py search
python career.py learn
python career.py status
python career.py portal
```

Search reads configured public sources: Arbeitnow, Remotive and selected
Greenhouse or Lever company boards. These cover part of the market. Your
assistant can add available web research or jobs you found yourself. Sources
that fail must be reported as failures.

Check results against the actual description: “remote” does not always mean
worldwide hiring, and matching words do not establish suitability. Unknown
salary, work authorization or requirements do not become confirmed matches.

Use `python career.py import-jobs PATH` to add an external list. The format and
source capabilities are documented in [docs/SOURCES.md](docs/SOURCES.md); your
assistant can prepare the file from reviewed descriptions.

The learning plan lives in `local/learning-plan.md`. After the first search,
your assistant refines it with at most three active topics, concrete exercises,
outputs and realistic time estimates. The command preserves an existing plan.
Useful outputs depend on your profession: a written piece, spreadsheet,
analysis, presentation, case study or project can all count.

Search runs when invoked. Background monitoring or a schedule needs separate
setup at your request.

## Tailored CV: facts, natural writing, your decision

For a selected job, ask:

> Prepare an application for JOB_ID. Map its requirements to my confirmed facts,
> tailor my CV, perform humanization and check the facts again. Show me the
> final text to review.

The assistant runs `prepare`, works on a CV copy, and saves the final `CV.md`
with its evidence mapping and review. Rephrasing is allowed; facts from a job
description do not become your experience.

Humanization is mandatory: remove formulaic phrases, exaggerated claims and
unnatural wording while preserving your voice. You should be able to discuss
what it says naturally in an interview. Facts are checked again after editing.
This is not a promise about AI-detector results.

The assistant's technical cycle:

```text
python career.py prepare JOB_ID
python career.py hash JOB_ID
python career.py review JOB_ID --review local/applications/JOB_ID/review-input.json
```

The review format is in [templates/review.example.json](templates/review.example.json).
After editing, the assistant obtains `cv_sha256` and `bundle_sha256` with `hash`,
reviews that exact version, and records both values in the review. Every
substantive CV line, including your name and job headings, must map to confirmed
facts. Standard section headings such as “Experience” and “Education” are exempt.
Changes require another review. Automated checks verify coverage and version
consistency; they cannot establish truth or writing quality on their own.

After reading the final text, run this command **personally**:

```text
python career.py approve JOB_ID
```

It asks you to confirm the displayed version. The assistant must not do this
step on your behalf. Once approved, export it:

```text
python career.py export JOB_ID
```

Markdown and HTML versions appear in `local/exports/`. Open the HTML in a browser,
check its appearance and print to PDF if needed. Export covers the CV; review
any cover letter separately. The project does not send applications or contact
employers.

After an actual submission or interview, ask the assistant to record the event.
For example, `python career.py stage JOB_ID applied --note "Submitted by candidate"`
only updates history. `python career.py check JOB_ID` checks whether the review
and your approval are still current.

## Private data and public copies

All personal files belong in `local/`, which is excluded from Git. Public code,
instructions and templates must not contain CVs, contact details, private notes,
application history or credentials.

```text
career-starter/
  AGENTS.md                 shared assistant instructions
  CLAUDE.md                 entry point for Claude Code
  workflows/                onboarding, search, learning, CV, humanization
  templates/                synthetic examples only
  local/                    your data; never publish
    inbox/                  CVs to import
    imports/                preserved originals and extracted text
    profile-input.json      confirmed criteria
    profile.json            active profile after onboarding
    master.md               master CV
    evidence.json           confirmed facts
    applications/           jobs, drafts and reviews
    learning-plan.md        learning plan
    exports/                finished CVs
```

Local storage does not mean the AI runs offline. Text your assistant reads is
processed according to your Codex or Claude Code settings. Public job searches
must not send your CV to the feeds.

To share the tool itself:

```text
python career.py check-public
python career.py package
```

Inspect the generated package before sharing. Do not manually ZIP the entire
workspace: it may already contain personal data. `.gitignore` does not remove
files previously committed to Git history. Start a clean public copy without
private history.

## If something stops

- **CV could not be read:** check the import result, provide text/DOCX or use the
  assistant's document-reading tools.
- **No jobs:** check source statuses and criteria. Broaden locations or roles
  only if they suit you.
- **Export blocked:** the assistant must fix the specific evidence or review
  gap, then you approve the current version. Do not disable the gate.
- **Unclear command:** run `python career.py --help`.

The full assistant workflow is in [AGENTS.md](AGENTS.md). Verification results
and current limits are in [docs/VERIFICATION.md](docs/VERIFICATION.md).
