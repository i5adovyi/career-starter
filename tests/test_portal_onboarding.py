"""HTTP onboarding and private persistence, using synthetic documents only."""

import base64
import http.client
import io
import json
import re
import tempfile
import threading
import time
import unittest
import zipfile
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from careerkit import cv, portal, workspace
from careerkit import search as search_module


class PortalOnboardingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cv_text = (
            "# Example Candidate\n\n## Experience\n\n"
            "- Helped customers resolve billing questions.\n"
        )
        self.server = None
        self.thread = None
        self.addCleanup(self.stop_server)
        self.start_server()

    def start_server(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), portal.handler(self.root))
        self.thread = threading.Thread(
            target=lambda: self.server.serve_forever(poll_interval=0.02), daemon=True
        )
        self.thread.start()
        self.origin = f"http://127.0.0.1:{self.server.server_port}"
        status, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        match = re.search(rb'<meta name="csrf-token" content="([^"]+)">', body)
        self.assertIsNotNone(match, "The page must supply its session CSRF token.")
        self.token = match[1].decode("ascii")
        self.assertNotEqual(self.token, "__CSRF_TOKEN__")

    def stop_server(self):
        if self.server is not None:
            self.server.shutdown()
            self.thread.join(timeout=3)
            self.server.server_close()
            self.server = None

    def request(self, method, route, payload=None, *, headers=None, raw=None):
        body = raw if raw is not None else (
            json.dumps(payload).encode("utf-8") if payload is not None else None
        )
        outgoing = {}
        if method == "POST":
            outgoing = {
                "Content-Type": "application/json",
                "Origin": self.origin,
                "X-CSRF-Token": self.token,
            }
        outgoing.update(headers or {})
        connection = http.client.HTTPConnection(
            "127.0.0.1", self.server.server_port, timeout=3
        )
        try:
            connection.request(method, route, body=body, headers=outgoing)
            response = connection.getresponse()
            return response.status, response.read()
        finally:
            connection.close()

    def json_request(self, method, route, payload=None):
        status, body = self.request(method, route, payload)
        return status, json.loads(body)

    def draft(self):
        status, result = self.json_request("GET", "/api/onboarding")
        self.assertEqual(status, 200)
        return result

    def snapshot(self):
        return {
            path.relative_to(self.root).as_posix(): path.read_bytes()
            for path in self.root.rglob("*") if path.is_file()
        }

    def save_ready_draft(self, **updates):
        draft = self.draft()
        draft.update({
            "cv_text": self.cv_text,
            "target_roles": ["Customer Support"],
            "locations": ["Germany"],
            "work_modes": ["remote"],
            "languages": ["English"],
            "seniority": [],
            "keywords": ["billing"],
            "excluded_keywords": [],
            "skills": ["Customer communication"],
            "weekly_hours": 3,
            "learning_goals": [
                {"skill": "Spreadsheets", "reason": "Suitable roles ask for reporting."}
            ],
            "salary": {"minimum": None, "currency": "", "period": ""},
            "learning_language": "en",
            "sources": [{"type": "arbeitnow"}],
        })
        draft.update(updates)
        status, saved = self.json_request("POST", "/api/onboarding", draft)
        self.assertEqual(status, 200, saved)
        return saved

    def complete(self):
        self.save_ready_draft()
        status, result = self.json_request(
            "POST", "/api/onboarding/complete", {"confirmed": True}
        )
        self.assertEqual(status, 200, result)
        self.assertTrue(result["onboarded"])
        return result

    def test_txt_upload_and_saved_answers_resume_after_server_restart(self):
        status, uploaded = self.json_request("POST", "/api/cv", {
            "name": "candidate.txt",
            "content": base64.b64encode(self.cv_text.encode("utf-8")).decode("ascii"),
        })
        self.assertEqual(status, 200, uploaded)
        self.assertEqual(uploaded["cv_text"].strip(), self.cv_text.strip())
        self.assertTrue(uploaded["import_id"])
        uploaded["target_roles"] = ["Customer Support"]
        uploaded["locations"] = ["Germany"]
        status, saved = self.json_request("POST", "/api/onboarding", uploaded)
        self.assertEqual(status, 200, saved)
        originals = list((self.root / "local/imports").glob("*/original.txt"))
        self.assertEqual(len(originals), 1)
        self.assertEqual(originals[0].read_bytes(), self.cv_text.encode("utf-8"))
        self.assertFalse((self.root / "local/profile.json").exists())

        old_token = self.token
        self.stop_server()
        self.start_server()
        resumed = self.draft()
        self.assertNotEqual(self.token, old_token)
        self.assertEqual(resumed["cv_text"], saved["cv_text"])
        self.assertEqual(resumed["target_roles"], ["Customer Support"])
        self.assertEqual(resumed["locations"], ["Germany"])
        self.assertEqual(resumed["import_id"], uploaded["import_id"])

    def test_docx_upload_extracts_text_and_preserves_the_original(self):
        document = io.BytesIO()
        with zipfile.ZipFile(document, "w") as archive:
            archive.writestr(
                "word/document.xml",
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                "<w:body><w:p><w:r><w:t>Helped customers with billing.</w:t>"
                "</w:r></w:p></w:body></w:document>",
            )
        content = document.getvalue()
        status, uploaded = self.json_request("POST", "/api/cv", {
            "name": "candidate.docx",
            "content": base64.b64encode(content).decode("ascii"),
        })
        self.assertEqual(status, 200, uploaded)
        self.assertEqual(uploaded["cv_text"], "Helped customers with billing.")
        originals = list((self.root / "local/imports").glob("*/original.docx"))
        self.assertEqual(len(originals), 1)
        self.assertEqual(originals[0].read_bytes(), content)

    def test_unreadable_docx_preserves_original_and_saved_search_answers(self):
        self.save_ready_draft()
        content = b"This synthetic input is not a DOCX archive."
        status, uploaded = self.json_request("POST", "/api/cv", {
            "name": "unreadable.docx",
            "content": base64.b64encode(content).decode("ascii"),
        })
        self.assertEqual(status, 200, uploaded)
        self.assertEqual(uploaded["extraction"], "assistant_required")
        self.assertEqual(uploaded["cv_text"], "")
        self.assertTrue(uploaded["notice"])
        self.assertEqual(uploaded["target_roles"], ["Customer Support"])
        self.assertEqual(uploaded["locations"], ["Germany"])
        originals = list((self.root / "local/imports").glob("*/original.docx"))
        self.assertEqual(len(originals), 1)
        self.assertEqual(originals[0].read_bytes(), content)
        self.assertFalse((self.root / "local/profile.json").exists())

    def test_confirmation_and_valid_profile_are_required_before_creating_artifacts(self):
        draft = self.save_ready_draft()
        before = self.snapshot()
        status, _ = self.json_request(
            "POST", "/api/onboarding/complete", {"confirmed": False}
        )
        self.assertEqual(status, 400)
        self.assertEqual(self.snapshot(), before)
        draft["target_roles"] = []
        status, saved = self.json_request("POST", "/api/onboarding", draft)
        self.assertEqual(status, 200, saved)
        before = self.snapshot()
        status, _ = self.json_request(
            "POST", "/api/onboarding/complete", {"confirmed": True}
        )
        self.assertEqual(status, 400)
        self.assertEqual(self.snapshot(), before)
        for name in ("master.md", "evidence.json", "profile.json"):
            self.assertFalse((self.root / "local" / name).exists(), name)

    def test_completion_creates_confirmed_artifacts_and_repeat_preserves_them(self):
        self.complete()
        master = self.root / "local/master.md"
        self.assertEqual(master.read_text(encoding="utf-8"), self.cv_text)
        claims = workspace.evidence(self.root)
        self.assertEqual(
            {claim["text"] for claim in claims.values()}, set(cv.claim_lines(self.cv_text))
        )
        self.assertTrue(all(claim["confirmed"] is True for claim in claims.values()))
        self.assertTrue(all(claim["source"].strip() for claim in claims.values()))
        profile = workspace.read_json(self.root / "local/profile.json")
        self.assertTrue(profile["confirmed"])
        self.assertEqual(profile["target_roles"], ["Customer Support"])
        self.assertEqual(profile["locations"], ["Germany"])
        self.assertEqual(profile["weekly_hours"], 3)
        self.assertEqual(profile["sources"], [{"type": "arbeitnow"}])
        before = self.snapshot()
        status, repeated = self.json_request(
            "POST", "/api/onboarding/complete", {"confirmed": True}
        )
        self.assertEqual(status, 200, repeated)
        self.assertEqual(self.snapshot(), before)
        self.assertTrue(self.draft()["onboarded"])
        status, state = self.json_request("GET", "/api/state")
        self.assertEqual(status, 200)
        self.assertTrue(state["onboarded"])

    def test_stale_draft_cannot_overwrite_or_confirm_newer_answers(self):
        old = self.save_ready_draft()
        changed = {**old, "locations": ["Poland"]}
        status, saved = self.json_request("POST", "/api/onboarding", changed)
        self.assertEqual(status, 200, saved)
        before = self.snapshot()
        status, _ = self.json_request("POST", "/api/onboarding", old)
        self.assertEqual(status, 400)
        status, _ = self.json_request("POST", "/api/onboarding/complete", {
            "confirmed": True, "draft_sha256": old["draft_sha256"],
        })
        self.assertEqual(status, 400)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.draft()["locations"], ["Poland"])
        self.assertFalse((self.root / "local/profile.json").exists())

    def test_ukrainian_profile_controls_plan_language_and_preserves_manual_work(self):
        self.save_ready_draft(learning_language="uk")
        status, result = self.json_request(
            "POST", "/api/onboarding/complete", {"confirmed": True}
        )
        self.assertEqual(status, 200, result)
        self.assertEqual(
            workspace.read_json(self.root / "local/profile.json")["learning_language"], "uk"
        )
        result = workspace.learn(self.root)
        plan = self.root / result["path"]
        self.assertTrue(plan.read_text(encoding="utf-8").startswith("# План навчання"))
        manual = "# План навчання\n\nМої нотатки після першого заняття.\n"
        workspace.write_text(plan, manual)
        repeated = workspace.learn(self.root)
        self.assertTrue(repeated["preserved"])
        self.assertEqual(plan.read_text(encoding="utf-8"), manual)
        status, state = self.json_request("GET", "/api/state")
        self.assertEqual(status, 200)
        self.assertEqual(state["learning_plan"], manual)
        self.assertIn("# План навчання", state["learning_plan_suggestion"])
        self.assertIn("Spreadsheets", state["learning_plan_suggestion"])

    def test_plan_suggestion_state_cannot_expose_other_private_documents(self):
        self.complete()
        workspace.write_text(self.root / "local/private-note.md", "Not a learning plan")
        workspace.write_json(self.root / "local/learning-plan-state.json", {
            "suggestion_path": "local/private-note.md",
        })
        status, state = self.json_request("GET", "/api/state")
        self.assertEqual(status, 200)
        self.assertEqual(state["learning_plan_suggestion"], "")

    def test_existing_cli_master_evidence_and_profile_are_not_replaced(self):
        self.stop_server()
        workspace.init(self.root)
        workspace.write_text(self.root / "local/master.md", "# Existing candidate\n")
        workspace.write_json(self.root / "local/evidence.json", {"claims": [{
            "id": "E-old", "text": "Existing candidate",
            "source": "Existing confirmation", "confirmed": True,
        }]})
        workspace.write_json(self.root / "local/profile.json", {
            "confirmed": True, "target_roles": ["Existing role"], "locations": ["Poland"]
        })
        before = self.snapshot()
        self.start_server()
        self.assertTrue(self.draft()["onboarded"])
        status, _ = self.json_request(
            "POST", "/api/onboarding/complete", {"confirmed": True}
        )
        self.assertEqual(status, 400)
        self.assertEqual(self.snapshot(), before)

    def test_async_search_uses_saved_profile_and_persists_jobs_and_learning_plan(self):
        self.complete()
        entered, release = threading.Event(), threading.Event()
        public_job = {
            "title": "Mitarbeiter Kundensupport",
            "company": "Example Company",
            "url": "https://example.org/jobs/support",
            "location": "Germany",
            "remote": True,
            "description": "Requirements: Excel reporting and handling customer billing questions.",
        }

        def fetch_source(source):
            self.assertEqual(source, {"type": "arbeitnow"})
            entered.set()
            if not release.wait(timeout=3):
                raise RuntimeError("The test did not release its feed fixture.")
            return [public_job]

        with patch.object(search_module, "_fetch_source", side_effect=fetch_source) as fetch:
            try:
                status, queued = self.json_request("POST", "/api/search", {})
                self.assertEqual(status, 202, queued)
                self.assertTrue(entered.wait(timeout=2), "The search worker never started.")
                status, running = self.json_request("GET", "/api/state")
                self.assertEqual(status, 200)
                self.assertEqual(running["search_task"]["status"], "running")
                status, again = self.json_request("POST", "/api/search", {})
                self.assertEqual(status, 202, again)
                self.assertEqual(again["status"], "running")
            finally:
                release.set()
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                status, state = self.json_request("GET", "/api/state")
                self.assertEqual(status, 200)
                if state["search_task"]["status"] != "running":
                    break
                time.sleep(0.01)
            self.assertEqual(state["search_task"]["status"], "complete", state["search_task"])
            self.assertEqual(fetch.call_count, 1)

        stored = workspace.read_json(self.root / "local/jobs.json")
        self.assertEqual(stored["status"], "ok")
        self.assertEqual([job["url"] for job in stored["jobs"]], [public_job["url"]])
        self.assertEqual(state["jobs"][0]["company"], "Example Company")
        self.assertEqual(state["jobs"][0]["title_matches"][0]["kind"], "synonym_translation")
        plan = (self.root / "local/learning-plan.md").read_text(encoding="utf-8")
        self.assertIn("Spreadsheets", plan)
        self.assertIn("3 hours", plan)
        self.assertIn(public_job["url"], plan)
        self.assertEqual(state["learning_plan"], plan)
        analysis = workspace.read_json(self.root / "local/learning-plan.json")
        self.assertEqual(analysis["job_sample_count"], 1)

    def test_rejected_post_requests_do_not_write_private_files(self):
        before = self.snapshot()
        upload = {
            "name": "candidate.txt",
            "content": base64.b64encode(self.cv_text.encode("utf-8")).decode("ascii"),
        }
        cases = [
            ({"Origin": "https://untrusted.example"}, None, 403),
            ({"X-CSRF-Token": "wrong-token"}, None, 403),
            ({"Host": "untrusted.example"}, None, 403),
            ({"Content-Type": "text/plain"}, None, 415),
            ({}, b"{", 400),
            ({"Content-Length": str(28 * 1024 * 1024 + 1)}, b"{}", 413),
        ]
        for headers, raw, expected in cases:
            with self.subTest(headers=headers, raw=raw):
                status, body = self.request("POST", "/api/cv", upload, headers=headers, raw=raw)
                self.assertEqual(status, expected, body)
                self.assertIsInstance(json.loads(body), dict)
                self.assertEqual(self.snapshot(), before)


if __name__ == "__main__":
    unittest.main()
