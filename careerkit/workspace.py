"""Private workspace initialization, CV import and confirmed search preferences."""

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import subprocess
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_json(path: Path, default=None):
    if not path.exists() and default is not None:
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".write-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def write_json(path: Path, value) -> None:
    write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def private(root: Path, relative: str = "") -> Path:
    """Reject links that could redirect private writes outside this workspace."""
    base = root.resolve() / "local"
    candidate = base / relative
    if base.is_symlink() or not candidate.resolve().is_relative_to(base):
        raise ValueError("Private data path must remain inside this workspace's local/ directory.")
    for item in [candidate, *candidate.parents]:
        if item == root.resolve():
            break
        if item.is_symlink() or bool(getattr(item, "is_junction", lambda: False)()):
            raise ValueError("Symlinks are not allowed in the private workspace.")
    return candidate


def init(root: Path) -> dict:
    base = private(root)
    for name in ("inbox", "imports", "applications", "exports"):
        private(root, name).mkdir(parents=True, exist_ok=True)
    marker = base / "workspace.json"
    if not marker.exists():
        write_json(marker, {"version": 1, "created_at": now()})
    return {"workspace": "local/", "next": "Import a CV, then follow workflows/onboarding.md with your assistant."}


def import_cv(root: Path, source: Path) -> dict:
    init(root)
    source = source.expanduser().resolve()
    if not source.is_file():
        raise ValueError("CV input must be an existing file.")
    if source.stat().st_size > 20 * 1024 * 1024:
        raise ValueError("CV input exceeds 20 MiB.")
    suffix = source.suffix.lower()
    if suffix not in {".md", ".txt", ".docx", ".pdf"}:
        raise ValueError("Supported CV inputs: .md, .txt, .docx and .pdf.")
    text = ""
    extraction = "text"
    if suffix in {".md", ".txt"}:
        text = source.read_text(encoding="utf-8-sig")
    elif suffix == ".docx":
        try:
            with zipfile.ZipFile(source) as archive:
                info = archive.getinfo("word/document.xml")
                if info.file_size > 10 * 1024 * 1024:
                    raise ValueError("DOCX document is too large to extract.")
                document = ElementTree.fromstring(archive.read(info))
        except (zipfile.BadZipFile, KeyError, ElementTree.ParseError) as exc:
            raise ValueError("Cannot read this DOCX. Save it again as .docx or provide a UTF-8 text copy.") from exc
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        text = "\n".join("".join(p.itertext()) for p in document.findall(".//w:p", ns))
        extraction = "docx"
    elif shutil.which("pdftotext"):
        try:
            result = subprocess.run(
                [shutil.which("pdftotext"), "-layout", str(source), "-"],
                capture_output=True, timeout=45, check=False,
            )
            if result.returncode == 0:
                text = result.stdout.decode("utf-8", errors="replace")
        except subprocess.TimeoutExpired:
            pass  # Preserve the original and offer assistant extraction below.
        extraction = "pdftotext" if text.strip() else "assistant_required"
    else:
        extraction = "assistant_required"
    if not text.strip():
        extraction = "assistant_required"
    folder = private(root, "imports/" + uuid.uuid4().hex[:12])
    folder.mkdir()
    shutil.copyfile(source, folder / ("original" + suffix))
    if text.strip():
        write_text(folder / "cv.txt", text)
    write_json(folder / "import.json", {
        "imported_at": now(), "sha256": digest(source),
        "format": suffix, "extraction": extraction,
    })
    return {
        "folder": folder.relative_to(root).as_posix(),
        "extraction": extraction,
        "next": ("Read cv.txt and confirm facts during onboarding." if text.strip()
                 else f"No text extracted. Ask your assistant to read original{suffix} and save verified text as cv.txt here. Scanned PDFs may need OCR."),
    }


def validate_profile(profile: dict) -> dict:
    if not isinstance(profile, dict) or profile.get("confirmed") is not True:
        raise ValueError("The candidate must confirm the onboarding profile (confirmed: true).")
    for key in ("target_roles", "locations", "work_modes", "languages", "seniority",
                "keywords", "excluded_keywords", "skills"):
        value = profile.get(key, [])
        if not isinstance(value, list) or any(not isinstance(x, str) or not x.strip() for x in value):
            raise ValueError(f"{key} must be a list of non-empty strings.")
        profile[key] = [x.strip() for x in value]
    if not profile["target_roles"] or not profile["locations"]:
        raise ValueError("At least one target role and location are required.")
    if not profile["work_modes"] or set(profile["work_modes"]) - {"remote", "hybrid", "onsite"}:
        raise ValueError("Choose remote, hybrid and/or onsite work.")
    hours = profile.get("weekly_hours")
    if isinstance(hours, bool) or not isinstance(hours, (int, float)) or not math.isfinite(hours) or not 0 <= hours <= 80:
        raise ValueError("weekly_hours must be a number between 0 and 80.")
    salary = profile.setdefault("salary", {"minimum": None, "currency": "", "period": ""})
    if not isinstance(salary, dict):
        raise ValueError("salary must be an object.")
    minimum = salary.get("minimum")
    if minimum is not None:
        if isinstance(minimum, bool) or not isinstance(minimum, (int, float)) or not math.isfinite(minimum) or minimum < 0:
            raise ValueError("Salary minimum must be null or a non-negative number.")
        if not salary.get("currency") or not salary.get("period"):
            raise ValueError("A salary minimum needs a currency and period.")
    goals = profile.setdefault("learning_goals", [])
    if not isinstance(goals, list) or any(
        not isinstance(g, dict) or not isinstance(g.get("skill"), str) or not g["skill"].strip()
        or not isinstance(g.get("reason"), str) or not g["reason"].strip() for g in goals
    ):
        raise ValueError("learning_goals must contain objects with skill and reason.")
    sources = profile.setdefault("sources", [])
    if not isinstance(sources, list) or any(not isinstance(s, dict) or s.get("type") not in {
        "arbeitnow", "remotive", "greenhouse", "lever",
    } for s in sources):
        raise ValueError("sources must list supported public feed types.")
    if any(s.get("type") in {"greenhouse", "lever"} and not s.get("board") for s in sources):
        raise ValueError("ATS sources need a public board slug.")
    return profile


def onboard(root: Path, profile_path: Path) -> dict:
    profile = validate_profile(read_json(profile_path))
    init(root)
    master = private(root, "master.md")
    if not master.exists() or not master.read_text(encoding="utf-8").strip():
        raise ValueError("Create local/master.md from the candidate's confirmed CV facts first.")
    evidence(root)
    destination = private(root, "profile.json")
    if destination.exists():
        backup = private(root, "profile-history/" + uuid.uuid4().hex + ".json")
        write_text(backup, destination.read_text(encoding="utf-8"))
    write_json(destination, {**profile, "updated_at": now()})
    return {"onboarded": True, "next": "Run search, then learn. Refine the learning plan with your assistant."}


def evidence(root: Path) -> dict:
    value = read_json(private(root, "evidence.json"))
    claims = value.get("claims", []) if isinstance(value, dict) else []
    if not isinstance(claims, list) or not claims:
        raise ValueError("local/evidence.json must contain confirmed candidate claims.")
    by_id = {}
    for claim in claims:
        if not isinstance(claim, dict) or any(
            not isinstance(claim.get(key), str) or not claim[key].strip() for key in ("id", "text", "source")
        ) or claim.get("confirmed") is not True:
            raise ValueError("Each evidence claim needs id, text, source and confirmed: true.")
        if claim["id"] in by_id:
            raise ValueError("Evidence claim IDs must be unique.")
        by_id[claim["id"]] = claim
    return by_id


def learn(root: Path) -> dict:
    from .learning import generate

    return generate(root)
