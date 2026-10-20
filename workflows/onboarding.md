# Onboarding

Start in English unless the candidate asks for another language or writes in
Ukrainian. Honor their language choice throughout the conversation; confirm the
language of the learning plan and CV separately.

The first useful outcome is a confirmed profile,
a private master CV, a small set of real job matches and a feasible learning
plan. Do not require a perfect CV or a long questionnaire before helping.

## Portal option

`python career.py portal` opens a four-step upload/paste, preferences, learning
and confirmation flow. Answers autosave in `local/onboarding-draft.json`.
The candidate reviews the extracted CV text before confirming; completion
creates `master.md`, `evidence.json` and `profile.json` and can start a search.
If this is already complete, read those artifacts and continue from the saved
state. Do not replace them or treat candidate confirmation as independent
fact verification. A saved draft alone is not a confirmed profile.

## 1. Inspect and import

Run `python career.py init` if needed. Ask the candidate to place their existing
CV in `local/inbox/`, or import an accessible file:

```text
python career.py import-cv "PATH_TO_CV"
```

Read the import result. Markdown, text and DOCX can be extracted locally.
PDF text extraction requires `pdftotext`; if it is unavailable or the PDF is an
image, use an available document-reading tool or ask for a text/DOCX version.
Do not treat empty extraction as an empty career. Preserve the original.

If there is no CV, start from the candidate's description of work, education,
volunteering, personal projects or other relevant experience. Do not equate
absence of formal employment with absence of skills.

## 2. Ask only what the CV cannot answer

Summarize what the document actually says before asking for corrections.
Collect these decisions conversationally, in small groups:

- Desired roles or type of work. “I do not know yet” is valid: compare a few
  plausible directions using transferable skills and market evidence.
- Countries/cities, remote/hybrid/on-site preference, and any relevant
  eligibility or sponsorship constraints. Do not infer work authorization.
- Languages for work, the conversation and application documents; language
  proficiency only when the candidate confirms it.
- Required conditions such as schedule, contract type or compensation, with
  currency and period where applicable. Distinguish a preference from a
  non-negotiable condition.
- Search timing and realistic time available for learning each week.
- Tone: a few sentences written or approved by the candidate, if available.

Do not ask for date of birth, a full home address, identity documents, marital
status or family/medical reasons for a break. Contact details for a CV are
optional until the candidate chooses to export one. A career break may remain
unexplained; discuss wording only at the candidate's request or when they want
help presenting it.

## 3. Confirm facts and save privately

Use `templates/profile.example.json` as the schema reference, replace its
synthetic examples, and save the candidate's input as
`local/profile-input.json`. Keep unknowns explicit. Show a concise summary of
the intended search and material factual uncertainties. Set `confirmed` to
`true` only after the candidate confirms the profile. Before running `onboard`,
create the candidate's human-readable master CV at `local/master.md` and a
claim ledger at `local/evidence.json`, according to the supported schema.

For each claim, preserve a stable ID, a precise statement and its source:

```json
{
  "claims": [
    {
      "id": "E1",
      "text": "An exact fact confirmed by the candidate.",
      "source": "user confirmation during onboarding",
      "confirmed": true
    }
  ]
}
```

This example is a format illustration, not candidate evidence. Record real
facts before preparing an application. Include approved identity/contact
details and education if they will appear as factual CV lines.

Resolve uncertain dates, ownership and metrics before presenting them as
confirmed. The candidate's confirmation can be the source; do not require
confidential employer files. Reuse supported phrasing and candidate-written
sentences where possible.

The master is the confirmed baseline. Tailored CVs live in application
folders; tailoring must not overwrite the baseline. Update the master later
only for actual corrections or newly confirmed experience.

Once `local/profile-input.json`, `local/master.md` and `local/evidence.json`
exist and reflect the candidate's confirmations, complete onboarding:

```text
python career.py onboard --profile local/profile-input.json
```

Read the result. The command validates these inputs and saves the active
profile as `local/profile.json`; it does not write the master or evidence for
you. Keep any unresolved facts in private notes outside the confirmed ledger.

## 4. Complete the first useful run

Configure sources appropriate to the confirmed roles and geography. Follow
`search.md`, run `python career.py search`, and explain the strongest matches,
uncertainties and any inaccessible sources. If a configured source has no
matches, revise the search with evidence; do not fabricate sample vacancies.

Follow `learning.md` and run `python career.py learn`. Turn the initial output
into a plan with at most three active topics, a small first task and clear
completion evidence. A candidate ready to apply does not need invented gaps.

End with the next useful action: inspect a match, prepare its application,
answer one consequential unknown, or do the first learning task.
