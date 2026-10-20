# Mandatory humanization and factual review

Every tailored CV and cover letter must pass this workflow before approval and
export. The aim is natural, candidate-specific writing that remains truthful.
No writing pass can guarantee a judgment by a reader or an AI detector.

## 1. Read as the candidate

Read the entire draft and any candidate-written sample. Keep distinctive
phrasing that is clear and appropriate. Ask whether the candidate could say
the sentences aloud and explain the work behind them in an interview.

Remove or revise:

- Generic enthusiasm and claims that could describe any applicant.
- Inflated adjectives or verbs unsupported by the candidate's actual role.
- Empty phrases such as “results-driven professional”, “proven track record”
  and “leveraged synergies” when concrete work communicates more.
- Repeated sentence patterns, unnecessary summaries and long stacked clauses.
- Unnatural synonyms, mechanical keyword repetition and copied JD phrasing
  that overstates the candidate's experience.

Prefer concrete actions, an understandable context and a supported result.
Use numbers only when confirmed. Vary sentence length where it makes reading
easier; do not add quirks, mistakes, personal anecdotes or false opinions to
simulate a person.

## 2. Freeze the inputs and review the final version

After the writing pass, capture the inputs **before** the final review:

```text
python career.py hash JOB_ID
```

Save both returned values, `cv_sha256` and `bundle_sha256`, for the review
record. The bundle covers the CV, draft, JD, job metadata, evidence, master and
profile. Now reread the final CV for natural voice and perform the fact pass
below. If you edit any input, capture new hashes and repeat the final review;
do not replace hashes in an old review to make it pass.

Compare the revised text with its evidence claim IDs and the master. Check
names, dates, numbers, role boundaries, tools, qualifications and skill levels.
Style edits must not increase certainty, change ownership or expand scope.
Keep learning projects and volunteer work accurately labelled.

Check that removed wording has not removed an important limitation or changed
the candidate's intended meaning. Revisit the requirement mapping if the
emphasis changed.

## 3. Record an actual review

Use `templates/review.example.json` for the supported schema. Put the
`cv_sha256` and `bundle_sha256` values captured before the final review into
the matching fields. Map every
visible content line of `CV.md`, including identity and employment headings,
to a `claim_map` entry. `quote` must match the exact line, including any
heading or bullet prefix; `evidence_ids` must reference confirmed claims from
`local/evidence.json`. For example, `# Candidate Name` needs evidence just as
a work-history bullet does.

Only blank lines, horizontal separators and a fixed set of standard section
headings (such as `## Experience`, `## Skills`, `## Education`, `## Summary`,
`## Досвід` and `## Освіта`) are exempt. The canonical list is
`SECTION_TITLES` in `careerkit/cv.py`. A custom heading in another language
still needs mapping; if it is only a structural label, use a supported heading
or discuss the desired label rather than inventing career evidence.

This includes identity/contact, dates, skills and education lines. Do not put
the internal evidence IDs in the CV itself.

Save the completed review input as
`local/applications/JOB_ID/review-input.json`, then register it:

```text
python career.py review JOB_ID --review local/applications/JOB_ID/review-input.json
```

Read the CLI result. A review identifies the reviewer, claim mapping, specific
style changes and remaining concerns using the supported fields.
Affirm only checks actually completed. File hashes bind the review to the
reviewed content; they establish version consistency, not factual truth or
human authorship.

Automated checks are a backstop. They cannot judge whether an anecdote is
true, a sentence sounds like the candidate or a job is right for them. The
assistant must perform the reading and evidence comparison.

## 4. Candidate review

Present the final CV and optional cover letter, plus the few questions or
risks that matter. Let the candidate edit vocabulary or reject wording.
After any change, repeat the review for the final version before requesting
approval.

The candidate must personally run the first command and respond to its
interactive confirmation of that version. An assistant must never execute it
or supply the response. After successful approval, export can proceed:

```text
python career.py approve JOB_ID
python career.py export JOB_ID
```

Do not mark human approval yourself merely because automated checks pass.
Do not send or upload the exported document as part of this workflow.

The automated gate and exported files cover `CV.md`. A cover letter still
requires this style/fact pass and the candidate's separate review; do not
claim that a CV hash also covers the letter.
