import importlib
import json
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

search_module = importlib.import_module("careerkit.search")


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "local").mkdir()
        self.profile = {
            "confirmed": True,
            "weekly_hours": 4,
            "target_roles": ["Customer Support"],
            "locations": ["Poland"],
            "work_modes": ["remote"],
            "keywords": ["communication"],
            "excluded_keywords": [],
            "languages": ["English"],
            "seniority": ["junior"],
            "salary": {"minimum": 5000, "currency": "PLN", "period": "month"},
            "sources": [{"type": "arbeitnow"}, {"type": "remotive"}],
        }
        self.write("local/profile.json", self.profile)

    def write(self, rel, value):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def job(self, **changes):
        return {
            "title": "Junior Customer Support", "company": "Example Company",
            "url": "https://example.invalid/jobs/support", "location": "Poland",
            "remote": True, "description": "Clear communication with customers.",
            **changes,
        }

    def normalized(self, **changes):
        return search_module._normalize(self.job(**changes), "manual")

    def test_nontechnical_junior_role_matches_without_invented_eligibility(self):
        ranked = search_module.rank(self.normalized(), self.profile)
        self.assertEqual(ranked["match_status"], "review")
        self.assertEqual(ranked["score"], 66)
        self.assertIn("Title matches: Customer Support", ranked["reasons"])
        self.assertIn("Location text matches: Poland", ranked["reasons"])
        self.assertTrue(any("authorization" in text for text in ranked["review_flags"]))
        self.assertTrue(any("Salary is unknown" in text for text in ranked["review_flags"]))

    def test_role_terms_are_words_not_substring_and_seniority_is_explicit(self):
        profile = {**self.profile, "target_roles": ["Account"], "seniority": []}
        result = search_module.rank(self.normalized(title="Accountant"), profile)
        self.assertEqual(result["match_status"], "rejected")
        senior = search_module.rank(self.normalized(title="Senior Customer Support"), self.profile)
        self.assertIn("Explicit title seniority outside preferences: senior", senior["rejection_reasons"])

    def test_unknown_geography_is_review_not_worldwide_eligibility(self):
        result = search_module.rank(self.normalized(location="Worldwide"), self.profile)
        self.assertEqual(result["match_status"], "review")
        self.assertTrue(any("Geography is unverified" in text for text in result["review_flags"]))
        self.assertFalse(any("Location text matches" in text for text in result["reasons"]))

    def test_known_exclusion_work_mode_and_comparable_salary_fail(self):
        profile = {**self.profile, "excluded_keywords": ["cold calling"]}
        job = self.normalized(
            description="Cold calling is required.", work_mode="onsite",
            salary={"minimum": 3000, "maximum": 4500, "currency": "PLN", "period": "month"},
        )
        result = search_module.rank(job, profile)
        self.assertEqual(result["match_status"], "rejected")
        self.assertEqual(len(result["rejection_reasons"]), 3)
        job["salary"]["currency"] = "EUR"
        result = search_module.rank(job, profile)
        self.assertFalse(any("salary ceiling" in reason for reason in result["rejection_reasons"]))
        self.assertTrue(any("not comparable" in flag for flag in result["review_flags"]))

    def test_html_is_inert_text(self):
        text = search_module.plain_text(
            "&lt;p&gt;Support customers&lt;/p&gt;<script>sendSecrets()</script>"
            "<style>.x{display:none}</style><ul><li>Answer emails</li></ul>"
        )
        self.assertEqual(text, "Support customers\nAnswer emails")

    def test_public_links_reject_local_private_credentials_and_scripts(self):
        for url in (
            "http://example.invalid/jobs", "https://127.0.0.1/x", "https://10.0.0.1/x",
            "https://[::1]/x", "https://169.254.169.254/x", "https://localhost/x",
            "https://host.internal/x", "https://" + "person:password" + "@example.invalid/x",
            "https://example.invalid:8765/x", "javascript:alert(1)",
            "https://example.invalid\\@localhost/x",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                search_module.public_url(url)
        self.assertEqual(search_module.public_url("https://example.invalid/jobs#top"),
                         "https://example.invalid/jobs")

    def test_dns_private_resolution_is_rejected_before_connection(self):
        answers = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))]
        with patch.object(search_module.socket, "getaddrinfo", return_value=answers), \
                patch.object(search_module, "_PinnedHTTPS") as connection:
            with self.assertRaisesRegex(ValueError, "non-public"):
                search_module.fetch_json("https://remotive.com/api/remote-jobs")
            connection.assert_not_called()

    def test_redirect_cannot_escape_provider_allowlist(self):
        answers = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))]
        response = Mock(status=302)
        response.getheader.return_value = "https://127.0.0.1/private"
        connection = Mock()
        connection.getresponse.return_value = response
        with patch.object(search_module.socket, "getaddrinfo", return_value=answers), \
                patch.object(search_module, "_PinnedHTTPS", return_value=connection) as factory:
            with self.assertRaises(ValueError):
                search_module.fetch_json("https://remotive.com/api/remote-jobs")
            self.assertEqual(factory.call_count, 1)
            connection.close.assert_called_once()

    def test_size_limit_is_enforced_before_read(self):
        answers = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))]
        response = Mock(status=200)
        response.getheader.return_value = str(search_module.MAX_BYTES + 1)
        connection = Mock()
        connection.getresponse.return_value = response
        with patch.object(search_module.socket, "getaddrinfo", return_value=answers), \
                patch.object(search_module, "_PinnedHTTPS", return_value=connection):
            with self.assertRaisesRegex(ValueError, "size limit"):
                search_module.fetch_json("https://remotive.com/api/remote-jobs")
            response.read1.assert_not_called()

    def test_provider_adapter_keeps_remotive_source_url_and_no_profile_query(self):
        payload = {"jobs": [{
            "title": "Junior Customer Support", "company_name": "Example Company",
            "url": "https://remotive.com/remote-jobs/customer-support/example-123",
            "candidate_required_location": "Worldwide", "description": "<p>Help people.</p>",
            "publication_date": "2026-01-01T12:00:00", "salary": "$30,000",
        }]}
        with patch.object(search_module, "fetch_json", return_value=payload) as fetch:
            rows = search_module._fetch_source({"type": "remotive"})
        fetch.assert_called_once_with("https://remotive.com/api/remote-jobs")
        self.assertEqual(rows[0]["url"], payload["jobs"][0]["url"])
        self.assertEqual(rows[0]["location"], "Worldwide")
        self.assertTrue(rows[0]["remote"])

    def test_greenhouse_skips_prospect_posts_and_keeps_full_description(self):
        payload = {"jobs": [
            {"internal_job_id": None, "title": "General interest"},
            {"internal_job_id": 1, "title": "Junior Customer Support",
             "absolute_url": "https://example.invalid/jobs/2",
             "location": {"name": "Poland"}, "content": "<p>Answer emails.</p>"},
        ]}
        with patch.object(search_module, "fetch_json", return_value=payload):
            rows = search_module._fetch_source({"type": "greenhouse", "board": "example"})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["description"], "<p>Answer emails.</p>")
        self.assertEqual(rows[0]["published_at"], "")

    def test_all_provider_failures_are_explicit_and_preserve_manual_jobs_and_history(self):
        imported = self.write("jobs-to-import.json", [self.job()])
        search_module.import_jobs(self.root, imported)
        application = self.write("local/applications/history.json", {"status": "applied", "notes": "Follow up"})
        before = application.read_bytes()
        with patch.object(search_module, "_fetch_source", side_effect=OSError("offline")):
            result = search_module.search(self.root)
        self.assertEqual(result["status"], "failed")
        self.assertTrue(result["partial_failure"])
        self.assertFalse(result["no_results"])
        self.assertEqual([job["source"] for job in result["jobs"]], ["manual"])
        self.assertEqual(application.read_bytes(), before)
        self.assertEqual(len(json.loads((self.root / "local/imported-jobs.json").read_text())), 1)

    def test_partial_failure_retains_previous_source_results_as_stale(self):
        with patch.object(search_module, "_fetch_source",
                          side_effect=[[self.job()], [self.job(url="https://example.invalid/jobs/second")]]):
            first = search_module.search(self.root)
        for cache in (self.root / "local/source-cache").glob("*.json"):
            cache.unlink()
        with patch.object(search_module, "_fetch_source",
                          side_effect=[OSError("offline"), []]):
            result = search_module.search(self.root)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(len(first["jobs"]), 2)
        self.assertEqual(len(result["jobs"]), 1)
        self.assertEqual(result["jobs"][0]["source"], "arbeitnow")
        self.assertTrue(result["jobs"][0]["stale"])

    def test_failed_source_stale_data_is_labelled_and_cache_avoids_refetch(self):
        self.profile["sources"] = [{"type": "remotive"}]
        self.write("local/profile.json", self.profile)
        with patch.object(search_module, "_fetch_source", return_value=[self.job()]) as fetch:
            search_module.search(self.root)
            cached = search_module.search(self.root)
            self.assertEqual(fetch.call_count, 1)
        self.assertEqual(cached["sources"][0]["status"], "cached")
        cache = self.root / "local/source-cache/remotive.json"
        cache.write_text('{"timestamp": 0}', encoding="utf-8")
        with patch.object(search_module, "_fetch_source", side_effect=OSError("offline")):
            failed = search_module.search(self.root)
        self.assertEqual(failed["status"], "failed")
        self.assertTrue(failed["jobs"][0]["stale"])
        self.assertTrue(any("earlier run" in flag for flag in failed["jobs"][0]["review_flags"]))

    def test_import_validates_whole_batch_before_writing_and_rejected_records_survive(self):
        bad = self.write("bad.json", [self.job(), self.job(url="https://localhost/private")])
        with self.assertRaises(ValueError):
            search_module.import_jobs(self.root, bad)
        self.assertFalse((self.root / "local/imported-jobs.json").exists())
        imported = self.write("jobs.json", [self.job(title="Accountant")])
        first = search_module.import_jobs(self.root, imported)
        self.assertTrue(first["no_results"])
        self.assertEqual(len(first["rejected"]), 1)
        self.profile["target_roles"] = ["Accountant"]
        self.profile["sources"] = []
        self.write("local/profile.json", self.profile)
        result = search_module.search(self.root)
        self.assertEqual(result["status"], "not_configured")
        self.assertEqual(result["jobs"][0]["title"], "Accountant")

    def test_empty_or_malformed_provider_payload_is_not_silent_success(self):
        with patch.object(search_module, "fetch_json", return_value={"error": "unavailable"}):
            result = search_module.search(self.root)
        self.assertEqual(result["status"], "failed")
        self.assertTrue(result["no_results"])
        with patch.object(search_module, "_fetch_source", return_value=[]):
            result = search_module.search(self.root)
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["no_results"])
        self.assertFalse(result["partial_failure"])


if __name__ == "__main__":
    unittest.main()
