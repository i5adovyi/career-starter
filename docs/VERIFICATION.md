# Verification — 2026-10-20

Tested locally on Windows with Python 3.12.10. The runtime targets Python 3.10+
and uses the standard library. macOS and Linux were not executed in this check.

## Automated behavior

```text
python -m unittest discover -s tests -v
```

47 tests: 46 passed, one skipped because this Windows environment cannot create
symbolic links. The suite includes:

- Synthetic CV import, confirmed onboarding, job import and learning-plan creation.
- Preparation that preserves existing candidate edits and application history.
- Mandatory humanisation checks and evidence mapping, including factual headings.
- Rejection of changed CV, JD, profile, master or evidence after review.
- Approval bound to the reviewed version and refusal to export unreviewed bytes.
- Progression of submitted applications after the candidate's profile changes.
- Localhost route, Host and Origin checks; safe text rendering.
- Public-feed adapters, conservative matching, failures, caches and imports.
- Manifest-only packaging, private-file exclusion and refusal to overwrite archives.
- Subprocess CLI journey from a fresh workspace whose path contains spaces,
  invoked from a different working directory.
- Successful manual imports without configured feeds or after feed failure,
  without misreporting a fresh network search.
- Actionable errors for invalid DOCX and preservation of inputs when PDF
  extraction times out or yields no text.

The first sandboxed test run could not connect to a loopback socket. The full
suite passed with permission to use the local socket. No check was weakened.

## Download-to-use verification

The original ZIP was extracted and exercised through the documented CLI commands.
This reproduced an incorrect failure exit for successful manual job import.
The CLI check also found an unhandled invalid-DOCX error. Both are fixed, and
manual imports now preserve the date of the last actual feed search.

An updated ZIP passed this sequence in a separate synthetic workspace:

```text
init → import-cv → onboard → import-jobs → search → learn → prepare
→ reject export without review → hash → review
→ reject export without approval → simulated fixture approval → export
→ record applied → record interview → check-public
```

The approval above belongs to an automated synthetic fixture, not a real
candidate. No application was submitted and no employer was contacted.

The localhost dashboard was loaded in a real browser. It showed 16 leads
(15 from feeds and one imported fixture), the source statuses, application stage
and learning scaffold. The vacancy filter and refresh worked, and refresh
preserved the filter.

Exported Markdown content and its SHA-256 were checked against the approved
fixture. HTML output was generated and its text checked. Browser print-to-PDF
layout was not exercised; the browser tool does not permit local file URLs.

## English and Ukrainian interface

After adding the language switch, the journey and release suites were rerun:
27 tests passed and one symbolic-link test was skipped on Windows. The first
sandboxed release run was blocked by temporary-directory permissions; the rerun
used the workspace's verification directory and permitted local socket access.

Browser checks confirmed English on first load, switching to Ukrainian,
remembering Ukrainian after a reload, switching back to English, and remembering
that choice after another reload. On the existing synthetic workspace, source
statuses, matching explanations, review warnings, application stage and export
readiness changed language. The vacancy filter survived switching and refresh.
Job titles and the saved learning plan retained their original text.

The public package includes both `README.md` (English) and `README.uk.md`
(Ukrainian). The portal language is a browser preference; document language is
chosen separately with the assistant.

## Light and dark themes

Browser checks confirmed the initial system theme, switching to light,
persisting the light choice after reload, switching to dark, and preserving dark
after another reload. Switching between English and Ukrainian translated the
theme control without changing the theme. The dark layout was visually checked
in both languages.

Calculated contrast for 14 text/background color pairs in each palette was at
least 4.5:1 (lowest: 4.99:1 light, 6.02:1 dark). These checks cover text, muted
labels, links, tags, code, warnings, buttons and the introduction panel; they are
not a complete accessibility audit.

## Product boundaries

This is an assistant-led working version. Codex or Claude Code must conduct the
conversation, interpret evidence, write the tailored CV, perform the semantic
humanisation review and refine the learning plan. The Python `learn` command
creates a scaffold; it does not produce a complete personalized curriculum.
The review gate checks recorded coverage and freshness; it cannot evaluate
writing quality. There is no background search scheduler or automatic submission.
Separate Codex and Claude Code installations were not tested; their shared
file-based instructions and the runtime were checked in this environment.

## Public feeds

A live search with a synthetic generic profile fetched 300 Arbeitnow records
and 10 Remotive records. It produced 15 leads requiring review and rejected 295.
These counts describe that test run, not promised coverage or job availability.
No CV or candidate contact details were sent to the feeds.

Greenhouse and Lever adapters were verified with fixtures against their documented
response shapes. See [SOURCES.md](SOURCES.md) for provider documentation and limits.

## Privacy and content review

This distribution was assembled from an explicit public source manifest without
the original project's history, CVs, application records, employer evidence or
candidate settings. The release checker scans public bytes for likely credentials,
non-example email addresses and personal home paths. Additional identity tokens
can be checked privately using `CAREER_PRIVATE_TOKENS`.

Pattern scanning is a backstop, not proof that arbitrary future prose is public.
Review changes to public files before packaging. There are no third-party runtime
packages to install; this check did not run an external dependency scanner.

The CV checks establish coverage, review completion and version consistency.
Candidate-provided facts and natural language still require the assistant's
semantic review and the candidate's approval. No AI-detector outcome is promised.
