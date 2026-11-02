"""Audit and package only the explicitly reviewed public source files."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import zipfile


MANIFEST = "PUBLIC_FILES.json"
DEMO_IMAGE = "docs/demo/portal.png"
# Only the visually reviewed, synthetic screenshot may bypass the UTF-8 scan.
DEMO_SHA256 = "e70560ddcfdf3da94e5c9fcf8c1b0b8211c736adc3c4873cf98fd9099a394123"
EXACT_PATHS = {
    MANIFEST, "career.py", "README.md", "README.uk.md", "AGENTS.md", "CLAUDE.md", ".gitignore",
    "start.cmd", "start.sh", "LICENSE", ".github/workflows/ci.yml", DEMO_IMAGE,
}
SOURCE_DIRS = {
    "careerkit": {".py"},
    "tests": {".py"},
    "workflows": {".md"},
    "templates": {".json", ".md"},
    "docs": {".md"},
}
IGNORED_DIRS = {
    "local", "dist", "build", ".git", ".venv", "venv", "node_modules",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
}
IGNORED_FILES = {".DS_Store", "Thumbs.db"}

# Patterns identify likely leaks; they cannot establish that all prose is public.
EMAIL = re.compile(r"[\w.+%-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
USER_PATH = re.compile(
    r"(?i)(?:\b[a-z]:[\\/]Users[\\/]|/(?:Users|home)/)[^/\s\\\"'<>]+"
)
SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{30,}\b"),
    re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    re.compile(r"\b[a-z][a-z0-9+.-]*://[^/\s:@]+:[^/\s@]+@", re.I),
    re.compile(
        r"""(?i)\b(?:api[_-]?key|access[_-]?token|secret[_-]?key|password)"""
        r"""\s*["']?\s*[:=]\s*["'][A-Za-z0-9_+/.=-]{12,}["']"""
    ),
]


def _safe_email_domain(domain: str) -> bool:
    domain = domain.casefold().rstrip(".")
    return (
        any(domain == base or domain.endswith("." + base)
            for base in ("example.com", "example.net", "example.org"))
        or domain.endswith((".example", ".test", ".invalid"))
    )


def _private_tokens() -> tuple[list[str], list[str]]:
    raw = os.environ.get("CAREER_PRIVATE_TOKENS", "")
    if not raw:
        return [], []
    try:
        tokens = json.loads(raw)
    except (ValueError, TypeError):
        return [], ["CAREER_PRIVATE_TOKENS must be a JSON array of nonempty strings."]
    if not isinstance(tokens, list) or any(
        not isinstance(token, str) or not token.strip() for token in tokens
    ):
        return [], ["CAREER_PRIVATE_TOKENS must be a JSON array of nonempty strings."]
    return [token.casefold() for token in tokens], []


def _is_link(path: Path) -> bool:
    # Windows junctions must not let a public tree reach into another directory.
    return path.is_symlink() or bool(getattr(path, "is_junction", lambda: False)())


def _eligible(path: str) -> bool:
    if not path or "\\" in path or ":" in path:
        return False
    relative = PurePosixPath(path)
    if relative.is_absolute() or str(relative) != path:
        return False
    if any(part in {".", ".."} or part in IGNORED_DIRS for part in relative.parts):
        return False
    if path in EXACT_PATHS:
        return True
    return (
        len(relative.parts) >= 2
        and relative.parts[0] in SOURCE_DIRS
        and relative.suffix in SOURCE_DIRS[relative.parts[0]]
        and all(not part.startswith(".") for part in relative.parts)
    )


def _manifest(root: Path) -> tuple[list[str], list[str]]:
    path = root / MANIFEST
    if _is_link(path):
        return [], [f"{MANIFEST}: symbolic links are not public source files."]
    try:
        entries = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        return [], [f"{MANIFEST}: missing or invalid JSON; expected an explicit file list."]
    if not isinstance(entries, list) or not all(isinstance(item, str) for item in entries):
        return [], [f"{MANIFEST}: expected a JSON array of relative file paths."]
    issues = []
    if len(entries) != len(set(entries)):
        issues.append(f"{MANIFEST}: duplicate entries.")
    if MANIFEST not in entries:
        issues.append(f"{MANIFEST}: the manifest must list itself.")
    for index, item in enumerate(entries, start=1):
        if not _eligible(item):
            issues.append(f"{MANIFEST}: entry {index} is not an allowed public source path.")
    return entries, issues


def _scan_text(text: str, label: str, tokens: list[str]) -> list[str]:
    issues = []
    if any(not _safe_email_domain(match.group(1)) for match in EMAIL.finditer(text)):
        issues.append(f"{label}: non-example email address.")
    if USER_PATH.search(text):
        issues.append(f"{label}: absolute personal home path.")
    if any(pattern.search(text) for pattern in SECRET_PATTERNS):
        issues.append(f"{label}: possible credential or private key.")
    if any(token in text.casefold() for token in tokens):
        issues.append(f"{label}: private identity token.")
    return issues


def _inspect(root: Path) -> tuple[dict[str, bytes], list[str]]:
    """Read verified bytes once, so packaging uses the content that was audited."""
    if _is_link(root) or not root.is_dir():
        return {}, ["Public root must be an existing directory, not a symbolic link."]
    root = root.resolve()
    entries, issues = _manifest(root)
    tokens, token_issues = _private_tokens()
    issues.extend(token_issues)
    if issues:
        return {}, issues
    listed = set(entries)
    found = set()
    contents = {}
    def read_error(_error: OSError) -> None:
        issues.append("A public source directory could not be inspected.")

    for directory, dirs, files in os.walk(root, followlinks=False, onerror=read_error):
        base = Path(directory)
        safe_dirs = []
        for name in sorted(dirs):
            child = base / name
            relative = child.relative_to(root).as_posix()
            if _is_link(child):
                issues.append(f"{relative}: symbolic links are not allowed.")
            elif name not in IGNORED_DIRS:
                safe_dirs.append(name)
        dirs[:] = safe_dirs
        for name in sorted(files):
            path = base / name
            relative = path.relative_to(root).as_posix()
            if _is_link(path):
                issues.append(f"{relative}: symbolic links are not allowed.")
                continue
            if name in IGNORED_FILES or path.suffix in {".pyc", ".pyo"}:
                continue
            found.add(relative)
            if relative not in listed:
                issues.append(f"{relative}: file is not in {MANIFEST}.")
                continue
            try:
                content = path.read_bytes()
                if relative != DEMO_IMAGE:
                    issues.extend(_scan_text(content.decode("utf-8"), relative, tokens))
                elif hashlib.sha256(content).hexdigest() != DEMO_SHA256:
                    issues.append(f"{relative}: image differs from the reviewed demo screenshot.")
            except OSError:
                issues.append(f"{relative}: public source could not be read.")
                continue
            except UnicodeError:
                issues.append(f"{relative}: public source must be readable UTF-8 text.")
                continue
            contents[relative] = content
            if any(token in relative.casefold() for token in tokens):
                issues.append("A public filename contains a private identity token.")
    for missing in sorted(listed - found):
        issues.append(f"{missing}: listed public source file is missing.")
    return contents, issues


def check_public(root: Path) -> list[str]:
    """Return privacy/release issues, without printing suspected secret values."""
    return _inspect(Path(root))[1]


def package_public(root: Path, output: Path) -> Path:
    """Build a new ZIP from audited manifest bytes; never overwrite an archive."""
    root = Path(root)
    output = Path(output).absolute()
    if output.suffix.lower() != ".zip":
        raise ValueError("Public package output must be a .zip file.")
    if output.exists() or output.is_symlink():
        raise FileExistsError("Package output already exists; choose a new filename.")
    contents, issues = _inspect(root)
    if issues:
        raise ValueError("Public release check failed:\n" + "\n".join(issues))
    resolved_root = root.resolve()
    resolved_output = output.resolve()
    if resolved_output.is_relative_to(resolved_root):
        relative = resolved_output.relative_to(resolved_root)
        if relative.parts[0] != "dist":
            raise ValueError("An archive inside the project must be placed under dist/.")
    output.parent.mkdir(parents=True, exist_ok=True)
    created = False
    try:
        with output.open("xb") as handle:
            created = True
            with zipfile.ZipFile(handle, "w", zipfile.ZIP_DEFLATED) as archive:
                for name, content in sorted(contents.items()):
                    archive.writestr(name, content)
        with zipfile.ZipFile(output) as archive:
            if set(archive.namelist()) != set(contents) or archive.testzip() is not None:
                raise ValueError("Archive verification failed.")
            for name, content in contents.items():
                expected = hashlib.sha256(content).digest()
                if hashlib.sha256(archive.read(name)).digest() != expected:
                    raise ValueError("Archive content verification failed.")
    except BaseException:
        if created:
            output.unlink(missing_ok=True)
        raise
    return output
