#!/usr/bin/env python3
"""Portable entry point for Career Starter (Python 3.10+)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from careerkit import cv, workspace

ROOT = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Local job search, learning and evidence-backed CV preparation.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="Create private local directories without overwriting data.")
    command = commands.add_parser("import-cv", help="Import .md/.txt/.docx/.pdf privately.")
    command.add_argument("path", type=Path)
    command = commands.add_parser("onboard", help="Save candidate-confirmed profile after CV/evidence review.")
    command.add_argument("--profile", type=Path, required=True)
    commands.add_parser("search", help="Fetch public vacancies and rank locally.")
    command = commands.add_parser("import-jobs", help="Import jobs found with your assistant.")
    command.add_argument("path", type=Path)
    commands.add_parser("learn", help="Create a learning plan scaffold; preserve existing work.")
    commands.add_parser("status", help="Summarize local workspace.")
    for name in ("prepare", "hash", "check", "approve", "export"):
        command = commands.add_parser(name)
        command.add_argument("job_id")
    command = commands.add_parser("review", help="Record mandatory evidence/humanisation review.")
    command.add_argument("job_id")
    command.add_argument("--review", type=Path, required=True)
    command = commands.add_parser("stage", help="Record an application stage; does not submit anything.")
    command.add_argument("job_id")
    command.add_argument("value", choices=sorted(cv.STAGES))
    command.add_argument("--note", default="")
    command = commands.add_parser("portal", help="Open the read-only localhost dashboard.")
    command.add_argument("--port", type=int, default=8766)
    command.add_argument("--no-open", action="store_true")
    commands.add_parser("check-public", help="Audit the explicit public package manifest.")
    command = commands.add_parser("package", help="Create a public-only ZIP, excluding all local data.")
    command.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = None
    exit_code = 0
    try:
        if args.command == "init":
            result = workspace.init(ROOT)
        elif args.command == "import-cv":
            result = workspace.import_cv(ROOT, args.path)
        elif args.command == "onboard":
            result = workspace.onboard(ROOT, args.profile)
        elif args.command in {"search", "import-jobs"}:
            from careerkit.search import import_jobs, search
            workspace.private(ROOT)
            result = search(ROOT) if args.command == "search" else import_jobs(ROOT, args.path)
            # Keep full descriptions local rather than flooding the assistant context.
            result = {key: value for key, value in result.items() if key not in {"jobs", "rejected"}}
            result["results"] = "local/jobs.json"
            exit_code = 1 if args.command == "search" and result.get("status") in {"failed", "not_configured"} else 0
        elif args.command == "learn":
            result = workspace.learn(ROOT)
        elif args.command == "status":
            from careerkit.portal import state
            result = state(ROOT)
            result["jobs"] = [{k: j.get(k) for k in ("id", "title", "company", "score", "review_flags")} for j in result["jobs"]]
            result["learning_plan"] = bool(result["learning_plan"])
        elif args.command == "prepare":
            result = cv.prepare(ROOT, args.job_id)
        elif args.command == "hash":
            result = cv.fingerprint(ROOT, args.job_id)
        elif args.command == "review":
            result = cv.review(ROOT, args.job_id, args.review)
        elif args.command == "check":
            result = cv.check(ROOT, args.job_id)
        elif args.command == "approve":
            current = cv.check(ROOT, args.job_id, require_approval=False)
            print("Candidate approval: read local/applications/" + args.job_id + "/CV.md first.")
            print("Confirm this is accurate, sounds like you, and is suitable for this job.")
            print("Assistants must leave this decision to the candidate.")
            phrase = "APPROVE " + current["cv_sha256"][:12]
            result = cv.approve(ROOT, args.job_id, input(f"Type {phrase}: "))
        elif args.command == "export":
            result = cv.export(ROOT, args.job_id)
        elif args.command == "stage":
            result = cv.stage(ROOT, args.job_id, args.value, args.note)
        elif args.command == "portal":
            from careerkit.portal import serve
            workspace.init(ROOT)
            serve(ROOT, args.port, not args.no_open)
        elif args.command in {"check-public", "package"}:
            from careerkit.release import check_public, package_public
            if args.command == "check-public":
                issues = check_public(ROOT)
                result = {"passed": not issues, "issues": issues}
                exit_code = bool(issues)
            else:
                destination = args.output or ROOT / "dist" / ("career-starter-" + workspace.now().replace(":", "-") + ".zip")
                path = package_public(ROOT, destination)
                result = {"package": str(path)}
    except (ValueError, OSError, KeyError, EOFError) as exc:
        print(f"Cannot complete {args.command}: {exc}", file=sys.stderr)
        return 1
    if result is not None:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(exit_code)


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
