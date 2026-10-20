"""Run the documented commands as subprocesses in a fresh, synthetic workspace."""

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "Project with spaces"
        self.root.mkdir()
        for name in json.loads((PROJECT / "PUBLIC_FILES.json").read_text(encoding="utf-8")):
            destination = self.root / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(PROJECT / name, destination)
        self.outside = Path(self.temp.name) / "outside"
        self.outside.mkdir()

    def run_cli(self, *args, expected=0, stdin=None):
        result = subprocess.run(
            [sys.executable, str(self.root / "career.py"), *map(str, args)],
            input=stdin, capture_output=True, text=True, encoding="utf-8",
            cwd=self.outside, timeout=30,
        )
        self.assertEqual(result.returncode, expected,
                         f"{args}: stdout={result.stdout}\nstderr={result.stderr}")
        self.assertNotIn("Traceback", result.stderr)
        return result

    def save_json(self, name, value):
        destination = self.root / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        return destination

    def onboard(self):
        self.run_cli("init")
        self.master = "# Sample Candidate\n\n## Experience\n\n- Answered customer billing questions.\n"
        source = self.root / "local/inbox/sample-cv.txt"
        source.write_text(self.master, encoding="utf-8")
        imported = json.loads(self.run_cli("import-cv", source).stdout)
        self.assertEqual((self.root / imported["folder"] / "cv.txt").read_text(encoding="utf-8"), self.master)
        (self.root / "local/master.md").write_text(self.master, encoding="utf-8")
        self.save_json("local/evidence.json", {"claims": [
            {"id": "E1", "text": "Sample Candidate", "source": "Synthetic test fixture", "confirmed": True},
            {"id": "E2", "text": "Answered customer billing questions.",
             "source": "Synthetic test fixture", "confirmed": True},
        ]})
        profile = json.loads((self.root / "templates/profile.example.json").read_text(encoding="utf-8"))
        profile.update(confirmed=True, target_roles=["Customer Support"], sources=[], seniority=[])
        self.run_cli("onboard", "--profile", self.save_json("local/profile-input.json", profile))

    def test_documented_manual_only_journey_and_fresh_package(self):
        self.onboard()
        imported = self.run_cli("import-jobs", self.save_json("local/jobs-input.json", [{
            "title": "Customer Support Specialist", "company": "Example Company",
            "url": "https://example.org/jobs/support", "location": "Germany",
            "remote": True, "description": "Answer customer billing questions.",
        }]))
        self.assertEqual(json.loads(imported.stdout)["operation"], "import")
        state = json.loads(self.run_cli("status").stdout)
        self.assertTrue(state["onboarded"])
        self.assertEqual(state["jobs"][0]["title"], "Customer Support Specialist")
        job_id = state["jobs"][0]["id"]
        self.run_cli("learn")
        self.run_cli("prepare", job_id)
        application = self.root / "local/applications" / job_id
        (application / "CV.md").write_text(self.master, encoding="utf-8")
        self.assertIn("review", self.run_cli("export", job_id, expected=1).stderr)
        current = json.loads(self.run_cli("hash", job_id).stdout)
        review = {
            **current, "reviewer": "Synthetic test",
            "summary": "Exercise the CLI gate using a short, fact-backed test CV.",
            "changes": ["Retained the specific customer task without invented results."],
            "checks": dict.fromkeys(("plain_language", "specific_evidence", "natural_voice",
                                    "read_aloud", "no_invented_claims"), True),
            "claim_map": [
                {"quote": "# Sample Candidate", "evidence_ids": ["E1"]},
                {"quote": "- Answered customer billing questions.", "evidence_ids": ["E2"]},
            ],
        }
        review_path = self.save_json(f"local/applications/{job_id}/review-input.json", review)
        self.run_cli("review", job_id, "--review", review_path)
        self.assertIn("approval", self.run_cli("export", job_id, expected=1).stderr)
        self.run_cli("approve", job_id, stdin="WRONG\n", expected=1)
        # This is an automated fixture, never a real candidate's approval.
        self.run_cli("approve", job_id, stdin="APPROVE " + current["cv_sha256"][:12] + "\n")
        exported = json.loads(self.run_cli("export", job_id).stdout)
        exported_path = self.root / exported["exported"]
        self.assertEqual(hashlib.sha256((exported_path / "CV.md").read_bytes()).hexdigest(), current["cv_sha256"])
        self.assertIn("Answered customer billing questions.", (exported_path / "CV.html").read_text(encoding="utf-8"))
        self.run_cli("stage", job_id, "applied", "--note", "Synthetic submission event")
        (self.root / "local/master.md").write_text(self.master + "\nNew practice.", encoding="utf-8")
        self.run_cli("stage", job_id, "interview", "--note", "Synthetic interview event")
        self.run_cli("export", job_id, expected=1)
        self.assertTrue(json.loads(self.run_cli("check-public").stdout)["passed"])
        output = self.root / "dist/repacked.zip"
        self.run_cli("package", "--output", output)
        self.assertTrue(output.is_file())
        self.assertFalse((self.outside / "local").exists())

    def test_manual_import_succeeds_even_when_previous_feed_failed(self):
        self.onboard()
        self.save_json("local/jobs.json", {
            "status": "failed", "jobs": [], "sources": [{"name": "remotive", "status": "failed", "count": 0}],
            "searched_at": "2026-01-01T00:00:00+00:00",
        })
        result = self.run_cli("import-jobs", self.save_json("local/jobs-input.json", [{
            "title": "Customer Support Specialist", "company": "Example Company",
            "url": "https://example.org/jobs/support", "description": "Customer support role.",
        }]))
        self.assertEqual(json.loads(result.stdout)["status"], "failed")
        self.assertEqual(json.loads(result.stdout)["operation"], "import")
        self.assertEqual(len(json.loads(self.run_cli("status").stdout)["jobs"]), 1)
        self.assertEqual(json.loads((self.root / "local/jobs.json").read_text())["searched_at"],
                         "2026-01-01T00:00:00+00:00")

    def test_invalid_docx_has_actionable_error_not_traceback(self):
        self.run_cli("init")
        broken = self.root / "local/inbox/broken.docx"
        broken.write_text("This is not a Word document.", encoding="utf-8")
        result = self.run_cli("import-cv", broken, expected=1)
        self.assertIn("DOCX", result.stderr)


if __name__ == "__main__":
    unittest.main()
