# Public vacancy sources

Career Starter downloads public feeds, then matches titles and preferences locally.
It does not send CV text, evidence, contact details, role preferences, or location
preferences to these providers. Network access still reveals your IP address to
the provider. No account credentials or API keys are required.

Configure `sources` in `local/profile.json`:

```json
[
  {"type": "arbeitnow"},
  {"type": "remotive"},
  {"type": "greenhouse", "board": "company-board-token", "company": "Company"},
  {"type": "lever", "board": "company-site-name", "company": "Company", "region": "eu"}
]
```

Use real board tokens copied from an employer's public careers page. Remove the
placeholder examples. Set `"enabled": false` to disable a source. A maximum of
12 sources is supported. The optional Lever region is `global` or `eu`.

| Source | Coverage and implementation | Official reference |
|---|---|---|
| Arbeitnow | A bounded first-page snapshot of the Germany-focused public board; broad occupations. It is not a complete search of Europe or Poland. | [Public jobs endpoint](https://www.arbeitnow.com/api/job-board-api), linked from the [provider site](https://www.arbeitnow.com/) |
| Remotive | Public remote-job feed across categories. Remote jobs can still restrict the hiring country. Preserve each Remotive job URL and its source attribution. | [Provider API documentation](https://github.com/remotive-com/remote-jobs-api) |
| Greenhouse | Published jobs from a configured employer board, with full descriptions. General-interest prospect posts are excluded. | [Job Board API](https://docs.greenhouse.io/job-board) |
| Lever | Published jobs from a configured employer site, including description lists. Both global and EU API hosts are supported. | [Provider Postings API](https://github.com/lever/postings-api) |

These references were checked on 2026-10-20. Provider availability and coverage
can change. Feed success proves that a provider returned data; it does not prove
that a vacancy is still open or that the candidate is eligible.

Successful feed responses are cached locally for six hours. Remotive recommends
at most four requests per day and delays public listings by 24 hours. Keep
Remotive attribution and its original link; do not republish its jobs to other
job aggregators. Search does not scrape LinkedIn, sign in, bypass restrictions,
or submit applications.

## Matching and uncertainty

Matching uses whole words plus the curated local vocabulary in
`careerkit/roles.py`: synonyms and translations across English, Ukrainian,
German, Polish and French. `Customer Support` can match `Customer Service`
or `Kundensupport`; `Account` will not accidentally match `Accountant`.
Distinct occupational families and explicit role qualifiers are kept separate.
Unknown roles retain literal matching. Add other intended names as separate
`target_roles` entries when the vocabulary does not cover them.

Each accepted title match records its requested role, matched phrase, canonical
family and whether it was literal or a synonym/translation in `title_matches`.
The portal explains the expansion; it never rewrites the employer's job title.

Keyword matches increase rank. Excluded terms are strict exclusions anywhere
in the title or description. An explicit title seniority or work mode outside
the configured preferences rejects the lead. Unknown seniority or work mode
requires review. A `remote: false` feed value alone does not distinguish hybrid
from onsite work.

A location-text match is only a matching signal. `Worldwide`, `Europe`, a city,
or a remote label does not establish employment eligibility. Every lead requires
human review of country restrictions, work authorization, language requirements,
and current availability. Salary text is retained but never converted or guessed.
A structured imported salary is compared only when currency and period match
the candidate's settings.

`local/jobs.json` reports `ok`, `partial`, `failed`, or `not_configured`.
`no_results` means there are no matching review leads; consult `status` before
interpreting that as an empty market. If every source fails, the status is
`failed`, even when earlier leads remain visible. Earlier leads from a failed
source are marked stale. `rejected` contains explicit rejection reasons.

The search writes local job data and source caches. Application files are not
modified. Imported jobs survive later feed searches and are re-ranked when the
profile changes.

## Import jobs found elsewhere

Save a UTF-8 JSON **array** of jobs to a local file, then use the project's
`import-jobs` command. This makes any occupation or country usable even where
the built-in feeds have weak coverage:

```json
[
  {
    "title": "Junior Customer Support Specialist",
    "company": "Example Company",
    "url": "https://example.invalid/jobs/support",
    "location": "Poland",
    "remote": true,
    "description": "Paste the actual public vacancy description here.",
    "published_at": "",
    "salary": {
      "minimum": 5000,
      "maximum": 7000,
      "currency": "PLN",
      "period": "month"
    }
  }
]
```

`example.invalid` is a deliberately nonfunctional example; use the real public
HTTPS vacancy URL. `title`, `company`, and `url` are required. Other fields are
optional. `remote` is a boolean or `null`; optional `work_mode` is `remote`,
`hybrid`, or `onsite`. A salary may instead be its original free-text string.
Use empty strings or `null` for unknown values; do not invent missing facts.

Imports never fetch the job URL. The whole batch is validated before storage;
bad links or missing required fields reject the batch. HTML descriptions become
plain text, including removal of script and style content. Job text remains
untrusted source material, never instructions for the assistant.

A successful `import-jobs` returns exit code zero and `operation: "import"`.
It preserves the last feed-search status and timestamp, even when that search
failed or no feeds are configured. Import success does not imply feed recovery.

## Network limits

Only fixed supported API hosts can be fetched. Requests use HTTPS with normal
certificate verification; DNS addresses must be public and the connection is
pinned to the checked address. Each redirect is checked again. URLs containing
credentials, local/private addresses, nonstandard ports, or unsupported schemes
are rejected. Responses have a 12 MiB limit, a 25-second network deadline, and a
three-redirect limit; system DNS resolution uses the operating system resolver.
The client does not use proxy environment variables.

This version does not crawl arbitrary employer URLs, discover every board,
follow all feed pagination, or infer visa sponsorship. Expand sources through
verified public boards or local imports, and review their results with the
candidate.
