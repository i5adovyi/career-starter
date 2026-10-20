"""Resumable local portal onboarding and one background search per workspace."""

from __future__ import annotations

import base64
import binascii
import copy
import hashlib
import json
import math
import os
import re
import threading
import uuid
from pathlib import Path

from . import cv, search, workspace

MAX_UPLOAD = 20 * 1024 * 1024
MAX_CV_TEXT = 200_000
DRAFT_FILE = "onboarding-draft.json"
RECEIPT_FILE = "onboarding-completed.json"
LIST_FIELDS = (
    "target_roles", "locations", "work_modes", "languages", "seniority",
    "keywords", "excluded_keywords", "skills",
)
PROFILE_FIELDS = (*LIST_FIELDS, "weekly_hours", "learning_goals", "salary",
                  "learning_language", "sources")
EDITABLE = {"step", "cv_text", *PROFILE_FIELDS}
READ_ONLY = {"onboarded", "draft_sha256", "import_id", "extraction", "notice"}


class ConflictError(ValueError):
    """A local artifact changed or already belongs to another workflow."""


class _Shared:
    def __init__(self):
        self.lock = threading.RLock()
        self.task = {"status": "idle"}


_SHARED: dict[str, _Shared] = {}
_SHARED_LOCK = threading.Lock()


def _defaults() -> dict:
    return {
        "step": 0, "cv_text": "", "extraction": "not_uploaded",
        **{key: [] for key in LIST_FIELDS},
        "weekly_hours": 3, "learning_goals": [],
        "salary": {"minimum": None, "currency": "", "period": ""},
        "learning_language": "en",
        "sources": [{"type": "arbeitnow"}, {"type": "remotive"}],
    }


def _text(value, field: str, maximum: int, *, multiline: bool = False) -> str:
    if not isinstance(value, str) or len(value) > maximum:
        raise ValueError(f"{field} must be text of at most {maximum} characters.")
    allowed = "\n\r\t" if multiline else ""
    if any((ord(char) < 32 and char not in allowed) or ord(char) == 127 for char in value):
        raise ValueError(f"{field} contains unsupported control characters.")
    return value.replace("\r\n", "\n").replace("\r", "\n").strip()


def _number(value, field: str, maximum: float):
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or not 0 <= value <= maximum):
        raise ValueError(f"{field} must be a finite number between 0 and {maximum:g}.")
    return value


def _sanitize(payload: dict, previous: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("The onboarding draft must be a JSON object.")
    if set(payload) - EDITABLE - READ_ONLY:
        raise ValueError("The onboarding draft contains an unsupported field.")
    result = copy.deepcopy(previous)
    for key, value in payload.items():
        if key in READ_ONLY:
            continue
        if key == "step":
            if type(value) is not int or not 0 <= value <= 3:
                raise ValueError("step must be an integer from 0 to 3.")
        elif key == "cv_text":
            value = _text(value, key, MAX_CV_TEXT, multiline=True)
        elif key in LIST_FIELDS:
            maximum = 30 if key in {"target_roles", "locations", "languages", "seniority"} else 100
            if not isinstance(value, list) or len(value) > maximum:
                raise ValueError(f"{key} must contain at most {maximum} entries.")
            value = list(dict.fromkeys(_text(item, key, 200) for item in value))
            if any(not item for item in value):
                raise ValueError(f"{key} entries cannot be empty.")
            if key == "work_modes" and set(value) - {"remote", "hybrid", "onsite"}:
                raise ValueError("Choose remote, hybrid and/or onsite work.")
        elif key == "weekly_hours":
            value = _number(value, key, 80)
        elif key == "learning_language":
            if value not in ("en", "uk"):
                raise ValueError("learning_language must be en or uk.")
        elif key == "salary":
            if not isinstance(value, dict) or set(value) - {"minimum", "currency", "period"}:
                raise ValueError("salary needs minimum, currency and period fields.")
            value = {**result["salary"], **value}
            if value["minimum"] is not None:
                value["minimum"] = _number(value["minimum"], "salary minimum", 1_000_000_000)
            value["currency"] = _text(value["currency"], "salary currency", 12).upper()
            value["period"] = _text(value["period"], "salary period", 30)
        elif key == "learning_goals":
            if not isinstance(value, list) or len(value) > 20:
                raise ValueError("Choose at most 20 learning goals.")
            goals = []
            for goal in value:
                if not isinstance(goal, dict) or set(goal) - {"skill", "reason"}:
                    raise ValueError("Each learning goal needs a skill and reason.")
                goals.append({
                    "skill": _text(goal.get("skill", ""), "learning skill", 200),
                    "reason": _text(goal.get("reason", ""), "learning reason", 2000),
                })
            value = goals
        elif key == "sources":
            if not isinstance(value, list) or len(value) > 12:
                raise ValueError("Choose at most 12 public sources.")
            sources = []
            for source in value:
                if (not isinstance(source, dict)
                        or set(source) - {"type", "board", "company", "region", "enabled"}):
                    raise ValueError("Unsupported public source configuration.")
                source = copy.deepcopy(source)
                if "enabled" in source and type(source["enabled"]) is not bool:
                    raise ValueError("Source enabled must be true or false.")
                if "company" in source:
                    source["company"] = _text(source["company"], "source company", 200)
                try:
                    search._source_key(source)
                except (TypeError, ValueError):
                    raise ValueError("Choose a supported source and a valid public board slug.") from None
                sources.append(source)
            value = sources
        result[key] = value
    return result


def _fingerprint(draft: dict) -> str:
    data = {key: value for key, value in draft.items() if key not in {"notice", "onboarded", "draft_sha256"}}
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class PortalSession:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        workspace.private(self.root)
        with _SHARED_LOCK:
            self._shared = _SHARED.setdefault(str(self.root).casefold() if os.name == "nt" else str(self.root), _Shared())

    def _path(self, relative: str) -> Path:
        return workspace.private(self.root, relative)

    def _confirmed(self) -> bool:
        profile = workspace.read_json(self._path("profile.json"), {})
        return isinstance(profile, dict) and profile.get("confirmed") is True

    def _load(self) -> dict:
        raw = workspace.read_json(self._path(DRAFT_FILE), {})
        if not isinstance(raw, dict):
            raise ValueError("The saved onboarding draft needs repair before continuing.")
        result = _sanitize({key: value for key, value in raw.items() if key in EDITABLE}, _defaults())
        # These fields are written by the upload handler, never accepted from a request.
        if "import_id" in raw:
            if not isinstance(raw["import_id"], str) or not re.fullmatch(r"[a-f0-9]{12}", raw["import_id"]):
                raise ValueError("The saved CV import reference is invalid.")
            result["import_id"] = raw["import_id"]
        for key in ("extraction", "notice"):
            if key in raw:
                result[key] = _text(raw[key], key, 1000)
        return result

    def _view(self, draft: dict) -> dict:
        return {**copy.deepcopy(draft), "onboarded": False, "draft_sha256": _fingerprint(draft)}

    def _ensure_open(self):
        if self._confirmed():
            raise ConflictError("Onboarding is already complete. Your existing profile has been preserved.")

    def draft(self) -> dict:
        with self._shared.lock:
            if self._confirmed():
                return {"onboarded": True}
            return self._view(self._load())

    def save(self, payload: dict) -> dict:
        with self._shared.lock:
            self._ensure_open()
            draft = self._load()
            if isinstance(payload, dict) and "draft_sha256" in payload and payload["draft_sha256"] != _fingerprint(draft):
                raise ConflictError("This draft changed in another request. Reload before saving.")
            saved = _sanitize(payload, draft)
            workspace.write_json(self._path(DRAFT_FILE), saved)
            return self._view(saved)

    def upload(self, payload: dict) -> dict:
        with self._shared.lock:
            self._ensure_open()
            if not isinstance(payload, dict) or set(payload) != {"name", "content"}:
                raise ValueError("Upload needs a filename and base64 file content.")
            name = _text(payload["name"], "filename", 240)
            if not name or any(char in name for char in "/\\:") or name in {".", ".."}:
                raise ValueError("Upload a filename, not a filesystem path.")
            encoded = payload["content"]
            if not isinstance(encoded, str) or len(encoded) > 4 * ((MAX_UPLOAD + 2) // 3):
                raise ValueError("CV upload exceeds 20 MiB.")
            try:
                content = base64.b64decode(encoded, validate=True)
            except (binascii.Error, ValueError):
                raise ValueError("CV upload is not valid base64 content.") from None
            if not content or len(content) > MAX_UPLOAD:
                raise ValueError("Upload a non-empty CV no larger than 20 MiB.")
            suffix = Path(name).suffix.lower()
            if not re.fullmatch(r"\.[a-z0-9]{1,12}", suffix):
                suffix = ".bin"
            workspace.init(self.root)
            temporary = self._path("inbox/upload-" + uuid.uuid4().hex + suffix)
            with temporary.open("xb") as stream:
                stream.write(content)
            notice = ""
            try:
                try:
                    imported = workspace.import_cv(self.root, temporary)
                    folder = self.root / imported["folder"]
                    import_id = folder.name
                    folder = self._path("imports/" + import_id)
                    extraction = imported["extraction"]
                except (ValueError, OSError, RuntimeError):
                    # Preserve unsupported or unreadable files for assistant/manual extraction.
                    import_id = uuid.uuid4().hex[:12]
                    folder = self._path("imports/" + import_id)
                    folder.mkdir()
                    with (folder / ("original" + suffix)).open("xb") as stream:
                        stream.write(content)
                    workspace.write_json(folder / "import.json", {
                        "imported_at": workspace.now(),
                        "sha256": hashlib.sha256(content).hexdigest(),
                        "format": suffix, "extraction": "assistant_required",
                    })
                    extraction = "assistant_required"
                extracted = folder / "cv.txt"
                text = extracted.read_text(encoding="utf-8") if extracted.is_file() else ""
                if len(text) > MAX_CV_TEXT:
                    extraction, text = "assistant_required", ""
                    notice = "The extracted CV exceeds 200,000 characters. Paste a reviewed, shorter version below."
                elif not text.strip():
                    extraction, text = "assistant_required", ""
                    notice = "The original is saved. Paste the CV text below or ask your assistant to extract it, then review it."
                else:
                    notice = "The original is saved. Review the extracted text and correct any formatting or extraction errors."
                    try:
                        text = _text(text, "cv_text", MAX_CV_TEXT, multiline=True)
                    except ValueError:
                        extraction, text = "assistant_required", ""
                        notice = "The original is saved, but extraction produced unsupported characters. Paste reviewed CV text below."
                saved = _sanitize({"cv_text": text, "step": 0}, self._load())
                saved.update({"import_id": import_id, "extraction": extraction, "notice": notice})
                workspace.write_json(self._path(DRAFT_FILE), saved)
                return self._view(saved)
            finally:
                temporary.unlink(missing_ok=True)

    def _completed(self, draft: dict) -> dict | None:
        receipt = workspace.read_json(self._path(RECEIPT_FILE), {})
        if not receipt:
            return None
        if not isinstance(receipt, dict) or receipt.get("draft_sha256") != _fingerprint(draft):
            raise ConflictError("The completed onboarding belongs to another draft. Existing files were preserved.")
        hashes = receipt.get("artifacts")
        if not isinstance(hashes, dict) or set(hashes) != {"master.md", "evidence.json", "profile.json"}:
            raise ConflictError("The onboarding receipt is incomplete. Existing files were preserved.")
        for name, expected in hashes.items():
            path = self._path(name)
            if not path.is_file() or workspace.digest(path) != expected:
                raise ConflictError("A completed onboarding file changed. Existing files were preserved.")
        return {"onboarded": True, "completed": True, "next": "search"}

    def complete(self, payload: dict) -> dict:
        with self._shared.lock:
            if (not isinstance(payload, dict) or payload.get("confirmed") is not True
                    or set(payload) - {"confirmed", "draft_sha256"}):
                raise ValueError("Review your CV and preferences, then confirm them to finish onboarding.")
            draft = self._load()
            if "draft_sha256" in payload and payload["draft_sha256"] != _fingerprint(draft):
                raise ConflictError("The reviewed draft changed. Reload and review it before confirming.")
            completed = self._completed(draft)
            if completed:
                return completed
            if any(self._path(name).exists() for name in ("master.md", "evidence.json", "profile.json")):
                raise ConflictError("Existing master, evidence or profile files were found. They were preserved; continue with your assistant.")
            text = draft["cv_text"].strip()
            claims = cv.claim_lines(text)
            if not text or not claims:
                raise ValueError("Provide and review CV text before completing onboarding.")
            if len(claims) > 5000:
                raise ValueError("The CV has too many content lines. Review and shorten it before continuing.")
            profile = workspace.validate_profile({
                key: copy.deepcopy(draft[key]) for key in PROFILE_FIELDS
            } | {"confirmed": True})
            if not any(source.get("enabled", True) for source in profile["sources"]):
                raise ValueError("Choose at least one public source before starting the search.")
            completed_at = workspace.now()
            source = "Candidate-provided CV text reviewed and confirmed in the local portal on " + completed_at
            if draft.get("import_id"):
                source += "; original preserved in local/imports/" + draft["import_id"] + "/"
            source += ". Candidate confirmation is not independent verification."
            ledger = {
                "kind": "candidate_provided", "confirmed_at": completed_at,
                "claims": [{"id": f"cv-{index:04d}", "text": line, "source": source, "confirmed": True}
                           for index, line in enumerate(claims, 1)],
            }
            profile["updated_at"] = completed_at
            contents = {
                "master.md": text + "\n",
                "evidence.json": json.dumps(ledger, ensure_ascii=False, indent=2) + "\n",
                "profile.json": json.dumps(profile, ensure_ascii=False, indent=2) + "\n",
            }
            receipt = {
                "draft_sha256": _fingerprint(draft), "completed_at": completed_at,
                "artifacts": {name: hashlib.sha256(content.encode()).hexdigest()
                              for name, content in contents.items()},
            }
            contents[RECEIPT_FILE] = json.dumps(receipt, ensure_ascii=False, indent=2) + "\n"
            self._publish_new(contents)
            return {"onboarded": True, "completed": True, "next": "search"}

    def _publish_new(self, contents: dict[str, str]):
        """Create files exclusively under the session lock; never replace CLI work."""
        published = []
        try:
            for name, content in contents.items():
                target = self._path(name)
                try:
                    stream = target.open("xb")
                except FileExistsError:
                    raise ConflictError("An onboarding file appeared during completion. Existing files were preserved.") from None
                with stream:
                    info = os.fstat(stream.fileno())
                    published.append((name, info.st_dev, info.st_ino))
                    stream.write(content.encode("utf-8"))
                    stream.flush()
                    os.fsync(stream.fileno())
        except BaseException:
            # Roll back only complete, unchanged files created by this call.
            # An interrupted or externally edited file is retained for repair.
            for name, device, inode in reversed(published):
                target = self._path(name)
                try:
                    info = target.stat()
                    if ((info.st_dev, info.st_ino) == (device, inode)
                            and target.read_bytes() == contents[name].encode("utf-8")):
                        target.unlink()
                except OSError:
                    pass
            raise

    def start_search(self, payload=None) -> dict:
        if payload is None:
            payload = {}
        if not isinstance(payload, dict) or payload:
            raise ValueError("Search does not accept CV text or arbitrary commands.")
        with self._shared.lock:
            if self._shared.task["status"] == "running":
                return copy.deepcopy(self._shared.task)
            if not self._confirmed():
                raise ValueError("Complete and confirm onboarding before starting the search.")
            workspace.validate_profile(workspace.read_json(self._path("profile.json")))
            self._shared.task = {"status": "running", "started_at": workspace.now()}
            worker = threading.Thread(target=self._run_search, name="career-starter-search", daemon=True)
            try:
                worker.start()
            except RuntimeError:
                self._shared.task = {"status": "failed", "error": "The search could not start. Please retry."}
            return copy.deepcopy(self._shared.task)

    def _run_search(self):
        try:
            result = search.search(self.root)
            plan = workspace.learn(self.root)
            failed = result.get("status") in {"failed", "not_configured"}
            task = {
                "status": "failed" if failed else "complete", "finished_at": workspace.now(),
                "search_status": result.get("status"),
                "matched": len(result.get("jobs", [])),
                "learning_plan": plan.get("path", "local/learning-plan.md"),
            }
            if failed:
                task["error"] = "No configured source could complete the search. Your profile is saved; check Sources and retry."
        except Exception:
            task = {
                "status": "failed", "finished_at": workspace.now(),
                "error": "The search could not finish. Your confirmed profile is saved; check source settings and retry.",
            }
        with self._shared.lock:
            self._shared.task = task

    def task(self) -> dict:
        with self._shared.lock:
            return copy.deepcopy(self._shared.task)
