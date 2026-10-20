"""Public-feed search. Candidate preferences stay on this computer."""

from __future__ import annotations

import hashlib
import html
import http.client
import ipaddress
import json
import os
import re
import socket
import ssl
import tempfile
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

from .workspace import private, validate_profile

MAX_BYTES = 12 * 1024 * 1024
MAX_JOBS = 5000
TIMEOUT = 25
CACHE_SECONDS = 6 * 60 * 60
API_HOSTS = {
    "www.arbeitnow.com", "remotive.com", "boards-api.greenhouse.io",
    "api.lever.co", "api.eu.lever.co",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read(path: Path, default):
    if not path.exists():
        return default
    if path.stat().st_size > MAX_BYTES * 5:
        raise ValueError(f"Local JSON file is too large: {path.name}")
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="." + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript", "iframe"}:
            self.hidden += 1
        elif not self.hidden and tag in {"p", "br", "li", "div", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "iframe"} and self.hidden:
            self.hidden -= 1
        elif not self.hidden and tag in {"p", "li", "div"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def plain_text(value) -> str:
    parser = _Text()
    parser.feed(html.unescape(str(value or ""))[:120_000])
    return "\n".join(
        line for line in (re.sub(r"[^\S\n]+", " ", x).strip()
                          for x in "".join(parser.parts).splitlines()) if line
    )


def public_url(value: str) -> str:
    """Validate a link without fetching it; network fetches also validate DNS."""
    if not isinstance(value, str) or len(value) > 4096:
        raise ValueError("Job URL must be a public HTTPS URL")
    if any(ord(c) < 33 for c in value) or "\\" in value:
        raise ValueError("Invalid characters in job URL")
    try:
        parsed = urlsplit(value)
        host = (parsed.hostname or "").lower().rstrip(".")
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Invalid job URL") from exc
    if (parsed.scheme != "https" or not host or parsed.username or parsed.password
            or port not in (None, 443)):
        raise ValueError("Only public HTTPS URLs on port 443 are supported")
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        raise ValueError("Local addresses are not supported")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        if "." not in host or not re.fullmatch(r"[a-z0-9.-]+", host):
            raise ValueError("Invalid public hostname")
    else:
        if not address.is_global:
            raise ValueError("Private or reserved addresses are not supported")
    return urlunsplit(("https", parsed.netloc, parsed.path or "/", parsed.query, ""))


class _PinnedHTTPS(http.client.HTTPSConnection):
    """Connect to a checked IP while verifying TLS for the provider hostname."""

    def __init__(self, host: str, address: str, timeout: float):
        super().__init__(host, timeout=timeout, context=ssl.create_default_context())
        self.address = address

    def connect(self):
        raw = socket.create_connection((self.address, 443), self.timeout)
        try:
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except BaseException:
            raw.close()
            raise


def fetch_json(url: str):
    """Bounded read from fixed provider hosts, including each redirect target."""
    deadline = time.monotonic() + TIMEOUT
    for _ in range(4):
        url = public_url(url)
        parsed = urlsplit(url)
        if parsed.hostname not in API_HOSTS:
            raise ValueError("Network requests are restricted to supported public APIs")
        addresses = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
        ips = list(dict.fromkeys(item[4][0] for item in addresses))
        if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):
            raise ValueError("Provider DNS resolved to a non-public address")
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Provider request timed out")
        connection = _PinnedHTTPS(parsed.hostname, ips[0], remaining)
        try:
            path = urlunsplit(("", "", parsed.path, parsed.query, ""))
            connection.request("GET", path, headers={
                "Accept": "application/json",
                "Accept-Encoding": "identity",
                "User-Agent": "CareerStarter/1.0 (local personal job search)",
            })
            response = connection.getresponse()
            if response.status in {301, 302, 303, 307, 308}:
                location = response.getheader("Location")
                if not location:
                    raise ValueError("Provider returned an empty redirect")
                url = urljoin(url, location)
                continue
            if response.status != 200:
                raise ValueError(f"Provider returned HTTP {response.status}")
            length = response.getheader("Content-Length")
            if length and int(length) > MAX_BYTES:
                raise ValueError("Provider response exceeds size limit")
            chunks, size = [], 0
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("Provider response timed out")
                if connection.sock:
                    connection.sock.settimeout(remaining)
                chunk = response.read1(min(65536, MAX_BYTES + 1 - size))
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_BYTES:
                    raise ValueError("Provider response exceeds size limit")
                chunks.append(chunk)
            return json.loads(b"".join(chunks).decode("utf-8"))
        finally:
            connection.close()
    raise ValueError("Provider exceeded redirect limit")


def _source_key(source: dict) -> str:
    kind = source.get("type", "")
    if kind in {"arbeitnow", "remotive"}:
        return kind
    board = source.get("board", "")
    if kind not in {"greenhouse", "lever"} or not isinstance(board, str):
        raise ValueError("Unsupported source; choose arbeitnow, remotive, greenhouse, or lever")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", board):
        raise ValueError("ATS source requires a board slug, not a URL")
    region = source.get("region", "global")
    if region not in {"global", "eu"}:
        raise ValueError("Lever region must be global or eu")
    return f"{kind}-{region}-{board}"


def _rows(payload, field: str | None) -> list:
    rows = payload.get(field) if field and isinstance(payload, dict) else payload
    if not isinstance(rows, list) or len(rows) > MAX_JOBS:
        raise ValueError("Provider returned an invalid or oversized jobs list")
    if any(not isinstance(row, dict) for row in rows):
        raise ValueError("Provider jobs must be objects")
    return rows


def _fetch_source(source: dict) -> list[dict]:
    kind = source["type"]
    if kind == "arbeitnow":
        payload = fetch_json("https://www.arbeitnow.com/api/job-board-api")
        return [{
            "title": row.get("title"), "company": row.get("company_name"),
            "url": row.get("url"), "location": row.get("location"),
            "remote": row.get("remote"), "description": row.get("description"),
            "published_at": row.get("created_at"),
        } for row in _rows(payload, "data")]
    if kind == "remotive":
        payload = fetch_json("https://remotive.com/api/remote-jobs")
        return [{
            "title": row.get("title"), "company": row.get("company_name"),
            "url": row.get("url"), "location": row.get("candidate_required_location"),
            "remote": True, "description": row.get("description"),
            "salary": row.get("salary"), "published_at": row.get("publication_date"),
        } for row in _rows(payload, "jobs")]
    board = source["board"]
    if kind == "greenhouse":
        payload = fetch_json(f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true")
        return [{
            "title": row.get("title"), "company": source.get("company") or board,
            "url": row.get("absolute_url"),
            "location": (row.get("location") or {}).get("name"),
            "description": row.get("content"), "published_at": "",
        } for row in _rows(payload, "jobs") if row.get("internal_job_id") is not None]
    host = "api.eu.lever.co" if source.get("region") == "eu" else "api.lever.co"
    payload = fetch_json(f"https://{host}/v0/postings/{board}?mode=json")
    return [{
        "title": row.get("text"), "company": source.get("company") or board,
        "url": row.get("hostedUrl"),
        "location": (row.get("categories") or {}).get("location"),
        "remote": True if row.get("workplaceType") == "remote" else None,
        "work_mode": row.get("workplaceType"),
        "description": "\n".join([str(row.get("descriptionPlain") or row.get("description") or "")]
                                 + [str(x.get("text", "")) + "\n" + str(x.get("content", ""))
                                    for x in row.get("lists", [])]),
        "published_at": "",
    } for row in _rows(payload, None)]


def _normalize(row: dict, source: str) -> dict:
    title, company = plain_text(row.get("title")), plain_text(row.get("company"))
    if not title or not company:
        raise ValueError("Each job needs title and company")
    url = public_url(row.get("url", ""))
    published = row.get("published_at") or ""
    if isinstance(published, (int, float)) and not isinstance(published, bool):
        try:
            published = datetime.fromtimestamp(published, timezone.utc).isoformat()
        except (ValueError, OverflowError, OSError):
            published = ""
    return {
        "id": hashlib.sha256(url.encode("utf-8")).hexdigest()[:16],
        "title": title[:500], "company": company[:300], "url": url,
        "location": plain_text(row.get("location"))[:1000],
        "remote": row.get("remote") if isinstance(row.get("remote"), bool) else None,
        "work_mode": row.get("work_mode") if row.get("work_mode") in {"remote", "hybrid", "onsite"} else "",
        "description": plain_text(row.get("description")),
        "source": source, "published_at": str(published)[:100],
        "salary": row.get("salary") if isinstance(row.get("salary"), (dict, str)) else "",
    }


def _words(text) -> str:
    return " ".join(re.findall(r"\w+", str(text).casefold()))


def _has(text: str, phrase: str) -> bool:
    small = _words(phrase)
    return bool(small) and f" {small} " in f" {_words(text)} "


def rank(job: dict, profile: dict) -> dict:
    """Conservative title matching; a match is a review lead, never eligibility."""
    result = dict(job)
    reasons, flags, rejected = [], [], []
    roles = [x for x in profile.get("target_roles", []) if str(x).strip()]
    matches = [role for role in roles if _has(job["title"], role)]
    if not matches:
        rejected.append("Title does not match any configured target role")
    else:
        reasons.append("Title matches: " + ", ".join(matches))
    blob = job["title"] + "\n" + job["description"]
    exclusions = [word for word in profile.get("excluded_keywords", []) if _has(blob, word)]
    if exclusions:
        rejected.append("Excluded terms: " + ", ".join(exclusions))
    keywords = [word for word in profile.get("keywords", []) if _has(blob, word)]
    if keywords:
        reasons.append("Keywords found: " + ", ".join(keywords))

    mode = job.get("work_mode") or ""
    place_title = job["location"] + " " + job["title"]
    if not mode and _has(place_title, "hybrid"):
        mode = "hybrid"
    if not mode and (job.get("remote") is True or _has(place_title, "remote")):
        mode = "remote"
    if not mode and (_has(place_title, "onsite") or _has(place_title, "on site")):
        mode = "onsite"
    modes = profile.get("work_modes", [])
    if modes and mode and mode not in modes:
        rejected.append("Work mode outside preferences: " + mode)
    if not mode:
        flags.append("Work mode is unknown; verify remote, hybrid, or onsite conditions")
    result["work_mode"] = mode

    locations = profile.get("locations", [])
    location_matches = [loc for loc in locations if _has(job["location"], loc)]
    if location_matches:
        reasons.append("Location text matches: " + ", ".join(location_matches))
    else:
        flags.append("Geography is unverified; confirm hiring country and location restrictions")
    flags.append("Work authorization and employer hiring eligibility are unverified")
    flags.append("Language requirements and proficiency are unverified")

    levels = profile.get("seniority", [])
    known = next((level for level in ("intern", "trainee", "junior", "middle", "senior", "lead")
                  if _has(job["title"], level)), "")
    aliases = {"entry": "junior", "entry level": "junior", "mid": "middle", "mid level": "middle"}
    requested = [aliases.get(_words(level), _words(level)) for level in levels]
    if levels and known and known not in requested:
        rejected.append("Explicit title seniority outside preferences: " + known)
    elif levels and not known:
        flags.append("Seniority is not explicit in the title")

    wanted_salary = profile.get("salary") or {}
    offered = job.get("salary")
    floor = wanted_salary.get("minimum")
    comparable = (
        isinstance(offered, dict)
        and offered.get("currency") == wanted_salary.get("currency")
        and offered.get("period") == wanted_salary.get("period")
        and isinstance(offered.get("maximum", offered.get("minimum")), (int, float))
        and not isinstance(offered.get("maximum", offered.get("minimum")), bool)
    )
    if floor is not None and comparable:
        top = offered.get("maximum", offered.get("minimum"))
        if top < floor:
            rejected.append("Published salary ceiling is below configured minimum")
        else:
            reasons.append("Published salary ceiling meets configured minimum")
            flags.append("Confirm salary range, gross/net basis, and contract before applying")
    else:
        flags.append("Salary is unknown or not comparable; no currency or period conversion assumed")
    result.update({
        "score": max(0, min(100, (40 if matches else 0) + min(30, len(keywords) * 6)
                           + (10 if location_matches else 0) + (10 if mode in modes else 0))),
        "reasons": reasons, "review_flags": flags,
        "match_status": "rejected" if rejected else "review",
        "rejection_reasons": rejected,
    })
    return result


def _profile(root: Path) -> dict:
    profile = _read(private(root, "profile.json"), None)
    if not isinstance(profile, dict) or not profile.get("target_roles"):
        raise ValueError("Complete onboarding and configure at least one target role first")
    return validate_profile(profile)


def _save_result(root: Path, previous: dict, records: list[dict], sources: list[dict], status: str,
                 *, is_search: bool = True) -> dict:
    profile = _profile(root)
    by_url = {job["url"]: job for job in records}
    ranked = [rank(job, profile) for job in by_url.values()]
    jobs = sorted((job for job in ranked if job["match_status"] != "rejected"),
                  key=lambda job: (-job["score"], job["company"].casefold(), job["title"].casefold()))
    # Unknown fields may contain user annotations from future compatible versions.
    old = {job.get("id"): job for job in previous.get("jobs", [])}
    for job in jobs:
        prior = old.get(job["id"], {})
        for key in ("notes", "application_status", "history", "first_seen"):
            if key in prior:
                job[key] = prior[key]
        job.setdefault("first_seen", _now())
        if job.get("stale"):
            job["review_flags"].append("Source failed; retained from an earlier run, availability unverified")
    result = {**previous, "searched_at": _now() if is_search else previous.get("searched_at"),
              "status": status, "sources": sources,
              "jobs": jobs, "no_results": not jobs,
              "partial_failure": status in {"partial", "failed"},
              "rejected": [{"id": job["id"], "title": job["title"], "company": job["company"],
                            "reasons": job["rejection_reasons"]}
                           for job in ranked if job["match_status"] == "rejected"]}
    _write(private(root, "jobs.json"), result)
    return result


def search(root: Path) -> dict:
    root = Path(root).resolve()
    profile = _profile(root)
    sources_config = profile.get("sources", [])
    if not isinstance(sources_config, list) or len(sources_config) > 12:
        raise ValueError("Configure at most 12 public sources")
    previous = _read(private(root, "jobs.json"), {})
    records, sources, processed = [], [], set()
    for source in sources_config:
        if not isinstance(source, dict):
            raise ValueError("Every source must be an object")
        if source.get("enabled") is False:
            continue
        key = str(source.get("type", "unknown"))
        try:
            key = _source_key(source)
            if key in processed:
                continue
            processed.add(key)
            cache_path = private(root, "source-cache/" + key + ".json")
            cached = _read(cache_path, {})
            age = time.time() - float(cached.get("timestamp", 0))
            if 0 <= age < CACHE_SECONDS and isinstance(cached.get("jobs"), list):
                normalized = cached["jobs"]
                state = "cached"
            else:
                raw = _fetch_source(source)
                normalized, invalid = [], 0
                for row in raw:
                    try:
                        normalized.append(_normalize(row, key))
                    except ValueError:
                        invalid += 1
                if raw and not normalized:
                    raise ValueError("Provider returned no valid public job records")
                _write(cache_path, {"timestamp": time.time(), "jobs": normalized})
                state = "ok"
                if invalid:
                    sources.append({"name": key + " invalid records", "status": "warning",
                                    "count": invalid, "error": "Records with missing fields or unsafe links skipped"})
            records.extend(normalized)
            sources.append({"name": key, "status": state, "count": len(normalized)})
        except (OSError, ValueError, TypeError, KeyError, AttributeError, http.client.HTTPException) as exc:
            # Avoid reflecting arbitrary endpoint URLs or user profile values.
            message = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
            sources.append({"name": key, "status": "failed", "count": 0, "error": message[:220]})
            records.extend({**job, "stale": True} for job in previous.get("jobs", [])
                           if job.get("source") == key and not job.get("imported"))
    imports = _read(private(root, "imported-jobs.json"), [])
    records.extend(imports)
    good = any(source["status"] in {"ok", "cached"} for source in sources)
    failed = any(source["status"] == "failed" for source in sources)
    status = "partial" if good and failed else "failed" if failed else "ok" if good else "not_configured"
    return _save_result(root, previous, records, sources, status)


def import_jobs(root: Path, path: Path) -> dict:
    """Import local JSON without network; every record is validated before writing."""
    root = Path(root).resolve()
    _profile(root)
    rows = _rows(_read(Path(path), None), None)
    normalized = [{**_normalize(row, "manual"), "imported": True} for row in rows]
    prior_imports = _read(private(root, "imported-jobs.json"), [])
    imports = {job["url"]: job for job in prior_imports + normalized}
    previous = _read(private(root, "jobs.json"), {})
    _write(private(root, "imported-jobs.json"), list(imports.values()))
    records = [job for job in previous.get("jobs", []) if not job.get("imported")]
    records.extend(imports.values())
    result = _save_result(root, previous, records, previous.get("sources", []),
                          previous.get("status", "not_configured"), is_search=False)
    return {**result, "operation": "import", "imported_count": len(normalized)}
