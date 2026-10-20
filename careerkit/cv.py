"""Evidence and mandatory humanisation gates for versioned CV export."""

from __future__ import annotations

import hashlib
import html
import json
import re
import uuid
from pathlib import Path

from .workspace import digest, evidence, now, private, read_json, write_json, write_text

CHECKS = ("plain_language", "specific_evidence", "natural_voice", "read_aloud", "no_invented_claims")
ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,95}$")
SECTION_TITLES = {
    "summary", "profile", "professional summary", "experience", "professional experience",
    "work experience", "employment", "earlier experience", "education", "skills",
    "technical skills", "languages", "certifications", "projects", "volunteering",
    "contact", "interests", "references", "профіль", "про себе", "досвід",
    "досвід роботи", "освіта", "навички", "мови", "сертифікації", "проєкти",
    "волонтерство", "контакти",
}


def folder(root: Path, job_id: str) -> Path:
    if not ID.fullmatch(job_id):
        raise ValueError("Invalid job ID.")
    path = private(root, "applications/" + job_id)
    if path.exists():
        for child in path.iterdir():
            private(root, "applications/" + job_id + "/" + child.name)
    return path


def prepare(root: Path, job_id: str) -> dict:
    destination = folder(root, job_id)
    master = private(root, "master.md")
    evidence(root)
    if not master.exists():
        raise ValueError("Onboard and create local/master.md first.")
    jobs = read_json(private(root, "jobs.json"), {}).get("jobs", [])
    job = next((j for j in jobs if j["id"] == job_id), None)
    if not job:
        raise ValueError("Job not found in current local/jobs.json. Search or import it first.")
    destination.mkdir(parents=True, exist_ok=True)
    files = {
        "job.json": json.dumps(job, ensure_ascii=False, indent=2) + "\n",
        "JD.txt": f"{job.get('title', '')}\n{job.get('company', '')}\n{job.get('url', '')}\n\n{job.get('description', '')}\n",
        "CV.draft.md": master.read_text(encoding="utf-8"),
        "application.md": (
            f"# {job.get('title', '')} — {job.get('company', '')}\n\n"
            f"Source: {job.get('url', '')}\n\n"
            "## Requirement → evidence\n\n"
            "| Job requirement | Evidence ID | Match / gap / unknown |\n"
            "|---|---|---|\n\n"
            "## Questions before applying\n\n"
            "Confirm location, work authorization, language, salary and posting availability.\n\n"
            "## Next action\n\nReview JD, tailor CV.draft.md, humanise into CV.md and record review.\n"
        ),
        "state.json": json.dumps({"stage": "preparing", "created_at": now(), "history": []}) + "\n",
    }
    created = []
    for name, text in files.items():
        path = destination / name
        if not path.exists():
            write_text(path, text)
            created.append(name)
    return {"folder": destination.relative_to(root).as_posix(), "created": created,
            "next": "Follow workflows/tailoring.md and workflows/humanization.md, then review."}


def fingerprint(root: Path, job_id: str) -> dict:
    application = folder(root, job_id)
    paths = {
        "cv": application / "CV.md", "draft": application / "CV.draft.md",
        "jd": application / "JD.txt", "job": application / "job.json",
        "evidence": private(root, "evidence.json"), "master": private(root, "master.md"),
        "profile": private(root, "profile.json"),
    }
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        raise ValueError("Missing review inputs: " + ", ".join(missing))
    hashes = {name: digest(path) for name, path in paths.items()}
    bundle = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    return {"cv_sha256": hashes["cv"], "inputs": hashes, "bundle_sha256": bundle}


def claim_lines(text: str) -> list[str]:
    """Exempt fixed structural labels, never factual/identity/employment headings."""
    result = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or re.fullmatch(r"[-*_]{3,}", line):
            continue
        heading = re.fullmatch(r"#{1,6}\s+(.+)", line)
        if heading and heading[1].strip().casefold() in SECTION_TITLES:
            continue
        result.append(line)
    return result


def review(root: Path, job_id: str, review_path: Path) -> dict:
    application = folder(root, job_id)
    current = fingerprint(root, job_id)
    record = read_json(review_path)
    if not isinstance(record, dict) or record.get("cv_sha256") != current["cv_sha256"]:
        raise ValueError("Review must reference the current CV.md hash. Run: python career.py hash JOB_ID")
    if record.get("bundle_sha256") != current["bundle_sha256"]:
        raise ValueError("Review inputs changed or bundle_sha256 is missing. Re-read inputs and review the current bundle.")
    checks = record.get("checks")
    if not isinstance(checks, dict) or any(checks.get(check) is not True for check in CHECKS):
        raise ValueError("All fact-check and humanisation checks must be completed.")
    for field in ("reviewer", "summary"):
        if not isinstance(record.get(field), str) or not record[field].strip():
            raise ValueError(f"Review needs a meaningful {field}.")
    changes = record.get("changes")
    if not isinstance(changes, list) or not changes or any(not isinstance(c, str) or not c.strip() for c in changes):
        raise ValueError("Review must describe actual humanisation edits or why wording was retained.")
    claims = evidence(root)
    mappings = record.get("claim_map")
    if not isinstance(mappings, list):
        raise ValueError("Review needs claim_map entries for every CV content line.")
    content = claim_lines((application / "CV.md").read_text(encoding="utf-8"))
    if not content:
        raise ValueError("CV has no reviewable content.")
    covered = set()
    for entry in mappings:
        if not isinstance(entry, dict) or not isinstance(entry.get("quote"), str):
            raise ValueError("Each claim map needs an exact quote.")
        quote = entry["quote"].strip()
        ids = entry.get("evidence_ids")
        if quote not in content or not isinstance(ids, list) or not ids or any(
            not isinstance(i, str) or i not in claims for i in ids
        ):
            raise ValueError("Claim map has an unknown quote or unconfirmed evidence ID.")
        covered.add(quote)
    if set(content) - covered:
        raise ValueError("Every content line, including factual headings, needs evidence mapping.")
    # The assistant performs semantic review. This verifies coverage and freshness,
    # not whether one natural-language claim logically entails another.
    saved = {**record, **current, "reviewed_at": now(), "kind": "assistant_review"}
    write_json(application / "review.json", saved)
    return {"reviewed": True, "cv_sha256": current["cv_sha256"],
            "next": "Candidate reads CV.md and runs approve JOB_ID. Any input edit invalidates this review."}


def check(root: Path, job_id: str, require_approval: bool = True) -> dict:
    application = folder(root, job_id)
    current = fingerprint(root, job_id)
    record = read_json(application / "review.json", {})
    if not isinstance(record, dict) or record.get("bundle_sha256") != current["bundle_sha256"]:
        raise ValueError("Mandatory fact-check/humanisation review is missing or stale.")
    checks = record.get("checks")
    if not isinstance(checks, dict) or any(checks.get(key) is not True for key in CHECKS):
        raise ValueError("Humanisation review is incomplete.")
    if require_approval:
        approval = read_json(application / "approval.json", {})
        if not isinstance(approval, dict) or approval.get("bundle_sha256") != current["bundle_sha256"] or approval.get("approved_by") != "candidate":
            raise ValueError("Candidate approval is missing or stale. Read the final CV and run approve JOB_ID.")
        if approval.get("review_sha256") != digest(application / "review.json"):
            raise ValueError("Review changed after candidate approval; approve again.")
    return current


def approve(root: Path, job_id: str, confirmation: str) -> dict:
    current = check(root, job_id, require_approval=False)
    expected = "APPROVE " + current["cv_sha256"][:12]
    if confirmation.strip() != expected:
        raise ValueError("Approval phrase did not match this CV version.")
    write_json(folder(root, job_id) / "approval.json", {
        **current, "approved_by": "candidate", "approved_at": now(),
        "review_sha256": digest(folder(root, job_id) / "review.json"),
    })
    return {"approved": True, "next": "Run export JOB_ID. Sending remains a separate candidate decision."}


def render_cv(text: str) -> str:
    parts = []
    in_list = False
    for line in text.splitlines():
        line = line.strip()
        is_bullet = line.startswith(("- ", "* "))
        if in_list and not is_bullet:
            parts.append("</ul>")
            in_list = False
        if not line:
            continue
        heading = re.match(r"^(#{1,3})\s+(.+)$", line)
        if heading:
            size = len(heading[1])
            parts.append(f"<h{size}>{html.escape(heading[2])}</h{size}>")
        elif is_bullet:
            if not in_list:
                parts.append("<ul>")
                in_list = True
            parts.append("<li>" + html.escape(line[2:]) + "</li>")
        else:
            parts.append("<p>" + html.escape(line) + "</p>")
    if in_list:
        parts.append("</ul>")
    return (
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">'
        "<title>CV</title><style>"
        "@page{size:A4;margin:16mm}body{font:11pt/1.45 Arial,sans-serif;max-width:760px;margin:30px auto;color:#172330}"
        "h1{font-size:24pt}h2{font-size:13pt;border-bottom:1px solid #b4c2ca;padding-bottom:4px}"
        "h3{font-size:11pt}p{margin:6px 0}li{margin:5px 0;break-inside:avoid}"
        "@media print{body{margin:0}h1,h2,h3{break-after:avoid}}"
        "</style><body>" + "\n".join(parts) + "</body></html>"
    )


def export(root: Path, job_id: str) -> dict:
    current = check(root, job_id)
    application = folder(root, job_id)
    content = (application / "CV.md").read_bytes()
    if hashlib.sha256(content).hexdigest() != current["cv_sha256"]:
        raise ValueError("CV changed during export; review the current version.")
    text = content.decode("utf-8")
    if check(root, job_id)["bundle_sha256"] != current["bundle_sha256"]:
        raise ValueError("Inputs changed during export; review the current version.")
    destination = private(root, f"exports/{job_id}-{current['cv_sha256'][:12]}-{uuid.uuid4().hex[:8]}")
    destination.mkdir(parents=True)
    write_text(destination / "CV.md", text)
    write_text(destination / "CV.html", render_cv(text))
    write_json(destination / "receipt.json", {**current, "exported_at": now()})
    return {"exported": destination.relative_to(root).as_posix(),
            "next": "Open CV.html, check layout, then print to PDF if needed. No application was sent."}


STAGES = {"preparing", "applied", "interview", "offer", "accepted", "rejected", "withdrawn"}


def stage(root: Path, job_id: str, value: str, note: str = "") -> dict:
    application = folder(root, job_id)
    if value not in STAGES or not (application / "state.json").exists():
        raise ValueError("Use a valid stage for a prepared application.")
    state = read_json(application / "state.json")
    if value == "applied":
        state["submission"] = {**check(root, job_id), "recorded_at": now()}
    elif value in {"interview", "offer", "accepted"} and not state.get("submission"):
        raise ValueError("Record the actual submission as applied before tracking its outcome.")
    state.setdefault("history", []).append({"from": state["stage"], "to": value, "at": now(), "note": note})
    state["stage"] = value
    write_json(application / "state.json", state)
    return {"stage": value, "recorded_only": True}
