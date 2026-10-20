"""Synthetic first-user journey and export barriers; no real candidate data."""

import http.client
import json
import subprocess
import tempfile
import threading
import unittest
import zipfile
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from pathlib import Path

from careerkit import cv, portal, workspace
from careerkit.search import import_jobs


class JourneyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        workspace.init(self.root)
        self.master = "# Sample Candidate\n\n## Experience\n\n- Helped customers resolve billing questions.\n"
        source = self.root / "sample.txt"
        source.write_text(self.master, encoding="utf-8")
        imported = workspace.import_cv(self.root, source)
        workspace.write_text(self.root / "local/master.md", self.master)
        workspace.write_json(self.root / "local/evidence.json", {"claims": [
            {"id": "E1", "text": "Helped customers resolve billing questions.",
             "source": imported["folder"] + "/cv.txt, confirmed during onboarding", "confirmed": True},
            {"id": "E2", "text": "Sample Candidate", "source": "Candidate confirmation", "confirmed": True},
        ]})
        self.profile = {
            "confirmed": True, "target_roles": ["Customer Support"], "locations": ["Germany"],
            "work_modes": ["remote"], "languages": ["English"], "seniority": [],
            "keywords": ["billing"], "excluded_keywords": [], "skills": ["billing"],
            "salary": {"minimum": None, "currency": "", "period": ""},
            "weekly_hours": 3, "learning_goals": [{"skill": "Spreadsheets", "reason": "A target role asks for reporting."}],
            "sources": [],
        }
        workspace.write_json(self.root / "local/profile-input.json", self.profile)
        workspace.onboard(self.root, self.root / "local/profile-input.json")
        workspace.write_json(self.root / "local/jobs-input.json", [{
            "title": "Customer Support Specialist", "company": "Example Company",
            "url": "https://example.org/jobs/support", "location": "Germany", "remote": True,
            "description": "Answer billing questions. Spreadsheet reporting is useful.",
        }])
        result = import_jobs(self.root, self.root / "local/jobs-input.json")
        self.job_id = result["jobs"][0]["id"]
        cv.prepare(self.root, self.job_id)
        self.app = cv.folder(self.root, self.job_id)
        workspace.write_text(self.app / "CV.md", self.master)

    def record_review(self):
        current = cv.fingerprint(self.root, self.job_id)
        review = {
            "cv_sha256": current["cv_sha256"], "bundle_sha256": current["bundle_sha256"],
            "reviewer": "Synthetic review",
            "summary": "Checked wording against E1; retained a concrete plain-language account.",
            "changes": ["Kept the specific billing task; no unsupported metric was added."],
            "checks": {key: True for key in cv.CHECKS},
            "claim_map": [{"quote": line, "evidence_ids": ["E2" if "Sample Candidate" in line else "E1"]}
                          for line in cv.claim_lines(self.master)],
        }
        path = self.app / "review-input.json"
        workspace.write_json(path, review)
        return cv.review(self.root, self.job_id, path)

    def approval(self):
        current = cv.fingerprint(self.root, self.job_id)
        return cv.approve(self.root, self.job_id, "APPROVE " + current["cv_sha256"][:12])

    def test_full_onboarding_to_reviewed_export_and_pipeline(self):
        learning = workspace.learn(self.root)
        self.assertFalse(learning["preserved"])
        plan = (self.root / learning["path"]).read_text(encoding="utf-8")
        self.assertIn("Spreadsheets", plan)
        self.assertIn("3 hours", plan)
        with self.assertRaisesRegex(ValueError, "review"):
            cv.export(self.root, self.job_id)
        self.record_review()
        with self.assertRaisesRegex(ValueError, "approval"):
            cv.export(self.root, self.job_id)
        self.approval()
        result = cv.export(self.root, self.job_id)
        exported = self.root / result["exported"]
        self.assertEqual((exported / "CV.md").read_text(encoding="utf-8"), self.master)
        html = (exported / "CV.html").read_text(encoding="utf-8")
        self.assertIn("Helped customers resolve billing questions.", html)
        self.assertNotIn("E1", html)
        cv.stage(self.root, self.job_id, "applied", "Candidate reports submitting manually.")
        state = workspace.read_json(self.app / "state.json")
        self.assertEqual(state["history"][0]["from"], "preparing")
        self.assertEqual(state["stage"], "applied")
        self.assertEqual(portal.state(self.root)["applications"][0]["readiness"], "Approved for export")

    def test_any_input_edit_invalidates_review_and_approval(self):
        self.record_review()
        self.approval()
        for path in (self.app / "CV.md", self.app / "JD.txt", self.root / "local/evidence.json",
                     self.root / "local/master.md", self.root / "local/profile.json"):
            previous = path.read_text(encoding="utf-8")
            workspace.write_text(path, previous + "\n")
            with self.assertRaisesRegex(ValueError, "stale"):
                cv.export(self.root, self.job_id)
            workspace.write_text(path, previous)
        cv.check(self.root, self.job_id)

    def test_changed_review_requires_new_candidate_approval(self):
        self.record_review()
        self.approval()
        record = workspace.read_json(self.app / "review.json")
        record["summary"] += " Additional review note."
        workspace.write_json(self.app / "review.json", record)
        with self.assertRaisesRegex(ValueError, "Review changed"):
            cv.export(self.root, self.job_id)

    def test_submitted_application_can_progress_after_profile_changes(self):
        self.record_review()
        self.approval()
        cv.stage(self.root, self.job_id, "applied", "Candidate reports submitting manually.")
        workspace.write_text(self.root / "local/master.md", self.master + "\nNew learning work")
        cv.stage(self.root, self.job_id, "interview", "Interview scheduled.")
        self.assertEqual(workspace.read_json(self.app / "state.json")["stage"], "interview")
        with self.assertRaisesRegex(ValueError, "stale"):
            cv.export(self.root, self.job_id)

    def test_export_refuses_cv_changed_after_approval_check(self):
        self.record_review()
        self.approval()
        original_check = cv.check
        def mutate_after_check(*args, **kwargs):
            result = original_check(*args, **kwargs)
            workspace.write_text(self.app / "CV.md", self.master + "\nUnreviewed statement")
            return result
        with patch.object(cv, "check", side_effect=mutate_after_check):
            with self.assertRaisesRegex(ValueError, "changed during export"):
                cv.export(self.root, self.job_id)
        self.assertEqual(list((self.root / "local/exports").iterdir()), [])

    def test_partial_humanisation_and_unmapped_claims_are_rejected(self):
        self.record_review()
        path = self.app / "review-input.json"
        record = workspace.read_json(path)
        record["checks"]["natural_voice"] = False
        workspace.write_json(path, record)
        with self.assertRaisesRegex(ValueError, "checks"):
            cv.review(self.root, self.job_id, path)
        record["checks"]["natural_voice"] = True
        record["claim_map"] = []
        workspace.write_json(path, record)
        with self.assertRaisesRegex(ValueError, "line"):
            cv.review(self.root, self.job_id, path)
        self.assertEqual(workspace.read_json(self.app / "review.json")["checks"]["natural_voice"], True)

    def test_malformed_review_checks_fail_with_a_validation_message(self):
        self.record_review()
        path = self.app / "review-input.json"
        record = workspace.read_json(path)
        for invalid in (None, [], "done"):
            record["checks"] = invalid
            workspace.write_json(path, record)
            with self.subTest(invalid=invalid), self.assertRaisesRegex(ValueError, "checks"):
                cv.review(self.root, self.job_id, path)

    def test_claims_in_headings_require_evidence(self):
        lines = cv.claim_lines("# Sample Candidate\n## Certified Specialist\n## Experience\n- Actual work")
        self.assertEqual(lines, ["# Sample Candidate", "## Certified Specialist", "- Actual work"])

    def test_changed_jd_during_review_cannot_be_stamped_as_current(self):
        self.record_review()
        workspace.write_text(self.app / "JD.txt", "Changed requirements after reading the CV.")
        with self.assertRaisesRegex(ValueError, "inputs changed"):
            cv.review(self.root, self.job_id, self.app / "review-input.json")

    def test_prepare_and_learning_preserve_user_work(self):
        workspace.write_text(self.app / "CV.draft.md", "Candidate's ongoing edits")
        workspace.write_text(self.app / "JD.txt", "Saved original description")
        self.assertEqual(cv.prepare(self.root, self.job_id)["created"], [])
        self.assertEqual((self.app / "CV.draft.md").read_text(), "Candidate's ongoing edits")
        workspace.learn(self.root)
        workspace.write_text(self.root / "local/learning-plan.md", "Personal learning progress")
        self.assertTrue(workspace.learn(self.root)["preserved"])
        self.assertEqual((self.root / "local/learning-plan.md").read_text(), "Personal learning progress")

    def test_onboarding_rejects_unconfirmed_or_malformed_profile(self):
        for updates in ({"confirmed": False}, {"weekly_hours": -1}, {"weekly_hours": True},
                        {"work_modes": ["anything"]}, {"target_roles": []}, {"sources": [{"type": "shell"}]}):
            with self.subTest(updates=updates), self.assertRaises(ValueError):
                workspace.validate_profile({**self.profile, **updates})

    def test_reonboarding_preserves_old_profile(self):
        previous = (self.root / "local/profile.json").read_bytes()
        self.profile["weekly_hours"] = 5
        workspace.write_json(self.root / "local/profile-input.json", self.profile)
        workspace.onboard(self.root, self.root / "local/profile-input.json")
        history = list((self.root / "local/profile-history").glob("*.json"))
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].read_bytes(), previous)
        self.assertEqual(workspace.read_json(self.root / "local/profile.json")["weekly_hours"], 5)

    def test_docx_import_without_third_party_packages(self):
        path = self.root / "sample.docx"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("word/document.xml",
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                '<w:body><w:p><w:r><w:t>Worked with customers.</w:t></w:r></w:p></w:body></w:document>')
        result = workspace.import_cv(self.root, path)
        self.assertEqual((self.root / result["folder"] / "cv.txt").read_text(), "Worked with customers.")

    def test_empty_text_and_pdf_timeout_preserve_input_and_request_extraction(self):
        source = self.root / "empty.txt"
        source.write_text("  \n", encoding="utf-8")
        result = workspace.import_cv(self.root, source)
        self.assertEqual(result["extraction"], "assistant_required")
        self.assertIn("original.txt", result["next"])
        pdf = self.root / "sample.pdf"
        pdf.write_bytes(b"%PDF-1.4\nsynthetic timeout test")
        with patch("careerkit.workspace.shutil.which", return_value="pdftotext"), \
                patch("careerkit.workspace.subprocess.run", side_effect=subprocess.TimeoutExpired("pdftotext", 45)):
            result = workspace.import_cv(self.root, pdf)
        self.assertEqual(result["extraction"], "assistant_required")
        self.assertEqual((self.root / result["folder"] / "original.pdf").read_bytes(), pdf.read_bytes())

    def test_paths_and_html_do_not_execute_untrusted_content(self):
        with self.assertRaises(ValueError):
            cv.prepare(self.root, "../escape")
        with self.assertRaises(ValueError):
            workspace.private(self.root, "../public.md")
        output = cv.render_cv('<script>alert("x")</script>\n- <img src=x onerror=x>')
        self.assertNotIn("<script>", output)
        self.assertNotIn("<img", output)
        self.assertIn("&lt;script&gt;", output)

    def test_portal_exposes_only_exact_routes_and_loopback_origin(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), portal.handler(self.root))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        def get(path, headers=None):
            connection = http.client.HTTPConnection("127.0.0.1", server.server_port)
            connection.request("GET", path, headers=headers or {})
            response = connection.getresponse()
            result = response.status, response.read()
            connection.close()
            return result
        status, body = get("/api/state")
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(body)["onboarded"])
        self.assertEqual(get("/local/master.md")[0], 404)
        self.assertEqual(get("/api/state", {"Host": "evil.example"})[0], 403)
        self.assertEqual(get("/api/state", {"Origin": "https://evil.example"})[0], 403)
        self.assertEqual(get("/")[0], 200)


if __name__ == "__main__":
    unittest.main()
