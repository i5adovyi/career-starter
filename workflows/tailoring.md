# Prepare an application

Run `python career.py prepare JOB_ID` for a real saved job. Inspect the command
output and application folder before editing; preserve any existing work.
The folder is `local/applications/JOB_ID/` and contains `job.json`, `JD.txt`,
`CV.draft.md` and `application.md`. Write the final reviewed text to `CV.md`;
the draft itself is not export-ready.

## Evidence before prose

Read the full saved description, the confirmed profile, `local/master.md` and
`local/evidence.json`. Build a short mapping in the application notes:

| Requirement from the description | Evidence claim IDs | Fit | What remains unknown |
|---|---|---|---|
| Exact requirement or a short faithful excerpt | Confirmed claim IDs | Strong / partial / none / unknown | A concrete question |

Do not convert “unknown” into “none”, or a partial match into a stronger skill.
If a critical fact is missing, ask the candidate once. Preparation can continue
on independent sections while that fact remains unresolved.

## Write for this role

Select relevant experience, reorder sections and bullets, and rephrase for
clarity and the role's vocabulary where the meaning is supported. Use ordinary
headings and readable text. Length should fit the relevant experience; never
add filler to meet a page count.

Preserve titles, employers, dates, qualifications and factual scope. A
professional title in the history cannot be silently replaced by the desired
job title. Do not transform team results into individual ownership, coursework
into employment or a tool mentioned in a vacancy into candidate experience.

The original import and confirmed master remain intact. Keep the tailored CV,
its evidence mapping, optional cover letter and review in the job's private
application folder. Internal evidence IDs and personal assessment notes do
not belong in the exported CV.

Write a cover letter only when useful or requested. Use a specific reason for
interest, a supported match and a natural closing. Verify company details or
omit them. Do not claim admiration, motivation or personal preferences the
candidate has not expressed. Explain material gaps honestly when they need
context; avoid turning a letter into an unsolicited list of shortcomings.

## Complete the gates

Follow `humanization.md`. Register the completed review using the CLI. Show
the candidate the actual final text and material gaps. Obtain explicit
approval for that version before export. The candidate personally runs
`python career.py approve JOB_ID` and answers its interactive prompt.
An assistant must not run approval or modify approval state.

Do not interpret “prepare a CV” as approval of unseen final text. Approval of
one application does not approve another. If the text changes after review or
approval, repeat the affected review and get approval of the new version.

An exported application is still unsent. The candidate decides whether,
where and when to submit it.
