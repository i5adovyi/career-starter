# Career Starter

## Project context

Career Starter is a local career workspace for one candidate per folder:
CV and confirmed preferences → real job leads → personalized practice →
tailored CV → humanization and fact review → candidate approval → export.
It supports different professions and career stages without preset candidate
criteria. Reusable source is shareable; all candidate data belongs in `local/`.

Python 3.10+ and its standard library run the CLI and portal. The interface is
inline HTML/CSS/JavaScript, with English/Ukrainian and light/dark themes.
There is no Node build, database setup, embedded LLM or API key requirement.
Claude Code supplies the conversation, writing and semantic review.

## Begin or resume

1. Read [AGENTS.md](AGENTS.md) in full. It is the shared operating guide for
   Claude Code and Codex: privacy, saved state, workflow, mandatory review and
   development rules all live there.
2. Read [README.md](README.md) for current behavior, commands and the code map
   ([Ukrainian version](README.uk.md)). Work in the folder containing `career.py`;
   if it is nested in another project, do not reuse that project's candidate data.
3. For candidate assistance, run `python career.py status` and inspect the
   relevant saved artifacts. Resume the draft, profile, plan or application
   instead of asking for onboarding again.
4. For code/documentation work, inspect `git status --short` and the relevant
   diff first. Use synthetic test data and preserve other sessions' changes.
   Do not read private CV content merely to understand the architecture.

Start the portal with `python career.py portal`; its default address is
`http://127.0.0.1:8766/`. Use `--no-open` to leave the browser closed.
Read `python career.py --help` for commands and AGENTS.md for verification.

## Follow the requested stage

- [Onboarding](workflows/onboarding.md): confirm facts and preferences, preserve
  the original CV, save the active profile and evidence.
- [Search](workflows/search.md): fetch/import real vacancies, inspect synonym
  and translation matches, freshness and unresolved employment conditions.
- [Learning](workflows/learning.md): compare CV evidence with job requirements,
  review concrete tasks and preserve the candidate's notes.
- [Tailoring](workflows/tailoring.md) and [humanization](workflows/humanization.md):
  write from supported facts, preserve natural voice and review the final version.

A missing CV keyword means unknown ability, not a proven deficit. A generated
plan is not a qualification. Never invent career facts or mark practice complete
without evidence. Every tailored CV and cover letter needs the actual style and
fact review; do not populate review flags just to unblock export.

The candidate personally runs `python career.py approve JOB_ID`. Never run it
for them, supply its response or edit approval state. Export is not submission;
this workflow does not authorize contacting employers or uploading CVs.

Keep detailed rules in AGENTS.md so the two assistants follow the same process.
Make Git commits, pushes, publications and recurring searches only when requested.
