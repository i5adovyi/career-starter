import importlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from careerkit.roles import match_titles

search_module = importlib.import_module("careerkit.search")


class RoleMatchingTests(unittest.TestCase):
    def test_synonyms_and_translations_return_explainable_evidence(self):
        for target, title, phrase, canonical in (
            ("Customer Support", "Customer Service Representative", "customer service representative",
             "Customer Support"),
            ("Customer Support", "Kundenberater (m/w/d)", "kundenberater", "Customer Support"),
            ("Customer Support", "Specjalista ds. obsługi klienta", "specjalista ds obsługi klienta",
             "Customer Support"),
            ("Customer Support", "Conseillère clientèle", "conseillère clientèle", "Customer Support"),
            ("Customer Support", "Chargé de Support Client", "chargé de support client",
             "Customer Support"),
            ("Customer Support", "Chargée de Support Client", "chargée de support client",
             "Customer Support"),
            ("Customer Support", "Фахівець з підтримки клієнтів", "фахівець з підтримки клієнтів",
             "Customer Support"),
            ("Customer Support Representative", "Mitarbeiter im Kundenservice (m/w/d)",
             "mitarbeiter im kundenservice", "Customer Support"),
            ("Бухгалтер", "Finanzbuchhalter (m/w/d)", "finanzbuchhalter", "Accountant"),
            ("Operations Assistant", "Operations Coordinator", "operations coordinator",
             "Operations Assistant"),
            ("Асистент операційного відділу", "Operations Assistant", "operations assistant",
             "Operations Assistant"),
        ):
            with self.subTest(target=target, title=title):
                self.assertEqual(match_titles(title, [target]), [{
                    "requested_role": target, "matched_phrase": phrase,
                    "kind": "synonym_translation", "canonical_role": canonical,
                }])

    def test_unknown_roles_keep_exact_word_boundary_fallback(self):
        self.assertEqual(match_titles("Senior Museum Curator", ["Museum Curator"]), [{
            "requested_role": "Museum Curator", "matched_phrase": "Museum Curator",
            "kind": "exact", "canonical_role": "Museum Curator",
        }])
        for target, title in (
            ("Account", "Accountant"), ("Support", "Supporter"),
            ("Museum Curator", "Museum Director"), ("SRE", "Site Reliability Engineer"),
            ("Technical Customer Support", "Customer Service Representative"),
        ):
            with self.subTest(target=target, title=title):
                self.assertEqual(match_titles(title, [target]), [])

    def test_professions_do_not_expand_to_similar_but_different_roles(self):
        for target, title in (
            ("Customer Support", "IT Support"),
            ("Customer Support", "Technical Customer Support Specialist"),
            ("Customer Support", "Technischer Kundensupport"),
            ("Technical Support", "Customer Service Representative"),
            ("Project Manager", "Product Manager"),
            ("Product Manager", "Projektmanager"),
            ("Account Manager", "Accountant"),
            ("Accountant", "Assistant Accountant"),
            ("Accountant", "Assistant comptable"),
            ("Business Analyst", "Data Analyst"),
        ):
            with self.subTest(target=target, title=title):
                self.assertEqual(match_titles(title, [target]), [])

    def test_individual_roles_do_not_expand_to_management_exact_or_alias_titles(self):
        for title in (
            "Customer Support Manager", "Head of Customer Care", "Customer Service Director",
            "Teamleiter Kundenservice", "Kierownik obsługa klienta",
            "Керівник підтримка клієнтів", "Responsable service client",
        ):
            with self.subTest(title=title):
                self.assertEqual(match_titles(title, ["Customer Support Specialist"]), [])
        self.assertEqual(match_titles("Marketing Manager", ["Marketing Specialist"]), [])
        self.assertEqual(match_titles("Operations Manager", ["Operations Assistant"]), [])

    def test_broad_role_queries_do_not_imply_a_staff_level_restriction(self):
        for target, title in (
            ("Marketing", "Junior Marketing Manager"),
            ("Customer Support", "Customer Support Manager"),
            ("Customer Support", "Head of Customer Service"),
        ):
            with self.subTest(target=target, title=title):
                ranked = search_module.rank(
                    {"title": title, "description": "", "location": "Poland"},
                    {"target_roles": [target]},
                )
                self.assertEqual(ranked["match_status"], "review")
                self.assertEqual(ranked["title_matches"][0]["requested_role"], target)

    def test_requested_management_level_is_preserved_across_aliases(self):
        matched = match_titles("Customer Service Manager", ["Customer Support Manager"])
        self.assertEqual(matched, [{
            "requested_role": "Customer Support Manager", "matched_phrase": "customer service",
            "kind": "synonym_translation", "canonical_role": "Customer Support",
        }])
        self.assertEqual(match_titles("Customer Service", ["Customer Support Manager"]), [])
        self.assertEqual(match_titles("Head of Customer Service", ["Customer Support Manager"]), [])
        intrinsic = match_titles("Projektmanager (m/w/d)", ["Project Manager"])
        self.assertEqual(intrinsic[0]["canonical_role"], "Project Manager")

    def test_requested_seniority_survives_translation_and_unstated_level_remains_unknown(self):
        for title in ("Senior Kundenservice", "Старший фахівець з підтримки клієнтів"):
            with self.subTest(title=title):
                self.assertEqual(match_titles(title, ["Junior Customer Support"]), [])
        matched = match_titles("Młodszy specjalista ds. obsługi klienta", ["Junior Customer Support"])
        self.assertEqual(matched[0]["canonical_role"], "Customer Support")
        self.assertEqual(match_titles("Kundenservice", ["Junior Customer Support"])[0]["kind"],
                         "synonym_translation")

    def test_slash_alternatives_do_not_require_a_combined_title(self):
        target = "Customer Support / Operations Assistant"
        matches = match_titles("Operations Coordinator", [target])
        self.assertEqual(matches, [{
            "requested_role": target, "matched_phrase": "operations coordinator",
            "kind": "synonym_translation", "canonical_role": "Operations Assistant",
        }])
        self.assertEqual(match_titles("UX Researcher", ["UI/UX Designer"]), [])

    def test_ranking_preserves_exact_reasons_and_other_preference_filters(self):
        profile = {
            "target_roles": ["Customer Support"], "seniority": ["junior"],
            "work_modes": ["remote"], "locations": ["Poland"], "keywords": ["communication"],
            "excluded_keywords": ["cold calling"],
        }
        job = {
            "title": "Junior Customer Support", "description": "Communication",
            "location": "Poland", "remote": True,
        }
        exact = search_module.rank(job, profile)
        self.assertEqual(exact["score"], 66)
        self.assertIn("Title matches: Customer Support", exact["reasons"])
        alias = search_module.rank({**job, "title": "Młodszy specjalista ds. obsługi klienta"}, profile)
        self.assertEqual(alias["score"], 66)
        self.assertEqual(alias["match_status"], "review")
        self.assertEqual(alias["title_matches"][0]["canonical_role"], "Customer Support")
        self.assertIn("Title alias matches: Customer Support → specjalista ds obsługi klienta",
                      alias["reasons"])
        excluded = search_module.rank({**job, "title": "Junior Kundenservice",
                                       "description": "Cold calling"}, profile)
        self.assertEqual(excluded["rejection_reasons"], ["Excluded terms: cold calling"])
        senior = search_module.rank({**job, "title": "Starszy specjalista ds obsługi klienta"}, profile)
        self.assertEqual(senior["rejection_reasons"],
                         ["Explicit title seniority outside preferences: senior"])

    def test_search_persists_alias_evidence_and_reranks_cached_jobs_after_role_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "local").mkdir()
            profile = {
                "confirmed": True, "target_roles": ["Customer Support"], "weekly_hours": 4,
                "locations": ["Poland"], "work_modes": ["remote"],
                "sources": [{"type": "arbeitnow"}],
            }
            profile_path = root / "local/profile.json"
            profile_path.write_text(json.dumps(profile), encoding="utf-8")
            rows = [{
                "title": title, "company": "Example Company",
                "url": "https://example.invalid/jobs/" + str(index),
                "location": "Poland", "remote": True, "description": "Communication with clients.",
            } for index, title in enumerate(("Kundenservice", "Operations Coordinator", "IT Support"))]
            with patch.object(search_module, "_fetch_source", return_value=rows) as fetch:
                first = search_module.search(root)
                self.assertEqual([job["title"] for job in first["jobs"]], ["Kundenservice"])
                persisted = json.loads((root / "local/jobs.json").read_text(encoding="utf-8"))
                self.assertEqual(persisted["jobs"][0]["title_matches"], [{
                    "requested_role": "Customer Support", "matched_phrase": "kundenservice",
                    "kind": "synonym_translation", "canonical_role": "Customer Support",
                }])
                profile["target_roles"] = ["Operations Assistant"]
                profile_path.write_text(json.dumps(profile), encoding="utf-8")
                second = search_module.search(root)
                self.assertEqual(fetch.call_count, 1)
                self.assertEqual([job["title"] for job in second["jobs"]], ["Operations Coordinator"])
                self.assertEqual(second["sources"][0]["status"], "cached")


if __name__ == "__main__":
    unittest.main()
