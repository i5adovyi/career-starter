# Verification — 2026-10-20

Tested locally on Windows with Python 3.12.10. The runtime targets Python 3.10+
and uses the standard library. macOS and Linux were not executed in this check.

## Automated behavior

```text
python -m unittest discover -s tests -v
```

85 tests: 84 passed, one skipped because this Windows environment cannot create
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
- Portal upload, resumable drafts, explicit confirmation, preserved originals
  and existing CLI artifacts, stale-draft rejection and repeated completion.
- Origin/CSRF/body-limit checks on write routes and background search persistence.
- Ukrainian learning-plan generation and preservation of manual plan edits.
- Multilingual title aliases, occupation boundaries and explicit seniority.
- CV evidence and job requirements, negation, company-section exclusion,
  learning budgets, zero-hour plans and preservation of edited suggestions.

The first sandboxed test run could not connect to a loopback socket. The full
suite passed with permission to use the local socket. No check was weakened.

## Multilingual search and personalized learning

A fresh synthetic workspace completed the portal onboarding with an English
support/operations CV, English target roles, a Ukrainian learning preference,
four weekly hours and no explicit learning goals. The live feeds returned
300 Arbeitnow and 10 Remotive records. Seven review leads matched: one literal
title match and six synonym/translation matches in the same feed snapshot,
including German and French titles. These are review leads, not verified
eligibility or promised coverage.

The generated plan selected three topics from the found descriptions and CV:
customer support, bookkeeping/reconciliation, and English for work. Each received
80 minutes. It displayed the candidate's evidence, quoted requirements with
source links, a concrete exercise, expected output and completion checks.
Missing CV evidence remained unknown instead of becoming an asserted skill gap.

After a server restart, another search refreshed the generated plan with the
updated analysis. Browser inspection confirmed valid source URLs and the actual
support-work sentence from the CV. A synthetic progress note was then added to
the plan. Searching again preserved its exact SHA-256 and displayed a separate
updated suggestion. No browser console warnings or errors were recorded.

After the final coordinated-negation fix, all 28 learning and portal-onboarding
tests passed again. Independent review also checked eight positive/negative
requirement cases. The live check used only synthetic candidate data.

## Earlier portal onboarding verification

A separate synthetic workspace was exercised through the actual browser UI:
upload DOCX, review extracted text, enter roles and location, reload and resume
the saved second step, enter skills and learning preferences, review the summary,
reject completion without confirmation, then confirm and search.

The real search fetched 300 Arbeitnow and 10 Remotive records and displayed
18 review leads. A Ukrainian starting learning plan was created from the
selected topic and three-hour weekly budget. No candidate CV was sent to the
sources. The user's workspace was kept separate from this synthetic check.

Targeted JavaScript checks also verified that a refresh after a mutation waits
for any older read and fetches fresh state, and that saving form answers preserves
custom Greenhouse/Lever sources not represented by the two feed checkboxes.
After a server restart, the browser restored the completed dashboard; a repeated
search used the cache and retained the active vacancy filter.

The portal records candidate-confirmed CV lines as evidence; it does not
independently verify those claims or perform a humanisation review. PDF extraction
still depends on `pdftotext`; if extraction fails or the file is scanned, the
original is preserved and the form offers manual text entry.

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

The portal conducts upload, preferences, confirmation and search without an
embedded AI model. Role matching now uses a curated multilingual vocabulary.
The Python `learn` command compares CV evidence with recognized requirements
in found job descriptions and supplies exercises, source excerpts and checks.
Its local vocabulary and exercise library have finite coverage; specialist
requirements remain explicit review items. Codex or Claude Code can provide
conversational guidance, interpret evidence, write the tailored CV, perform
the semantic humanisation review and refine the learning plan.
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
