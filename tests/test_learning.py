"""Learning decisions and preservation, using isolated synthetic candidate data."""

import tempfile
import unittest
from pathlib import Path

from careerkit import workspace


class LearningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        workspace.init(self.root)
        self.profile = {
            "confirmed": True, "target_roles": ["Operations Assistant"],
            "locations": ["Germany"], "work_modes": ["remote"], "languages": [],
            "skills": [], "weekly_hours": 3, "learning_goals": [], "sources": [],
        }
        self.save_profile()
        self.save_cv("Prepared Excel reports for weekly operations reviews.")

    def save_profile(self):
        workspace.write_json(self.root / "local/profile.json", self.profile)

    def save_cv(self, *claims):
        workspace.write_text(self.root / "local/master.md", "# Example Candidate\n\n" + "\n".join(claims))
        workspace.write_json(self.root / "local/evidence.json", {"claims": [
            {"id": f"E{index}", "text": text, "source": "Synthetic candidate CV", "confirmed": True}
            for index, text in enumerate(claims, 1)
        ]})

    def save_jobs(self, *descriptions):
        jobs = [{
            "id": f"J{index}", "title": "Operations Assistant",
            "url": f"https://example.org/jobs/operations-{index}", "description": description,
            "match_status": "review",
        } for index, description in enumerate(descriptions, 1)]
        workspace.write_json(self.root / "local/jobs.json", {"jobs": jobs, "searched_at": "2026-01-01"})
        return jobs

    def generate(self):
        result = workspace.learn(self.root)
        report = workspace.read_json(self.root / result["analysis_path"])
        plan = (self.root / result.get("suggestion_path", result["path"])).read_text(encoding="utf-8")
        return result, report, plan

    def test_same_vacancy_different_cv_changes_starting_point_and_first_approach(self):
        self.save_jobs("Requirements: Excel skills.")
        _, report, experienced_plan = self.generate()
        topic = report["priorities"][0]
        self.assertEqual(topic["skill_id"], "spreadsheets")
        self.assertEqual(topic["status"], "documented")
        self.assertEqual(topic["mode"], "work_sample")
        self.assertEqual(topic["candidate_evidence"][0]["id"], "E1")
        self.assertIn("independent work sample", experienced_plan)
        self.save_cv("Coordinated appointments for a fictional service team.")
        result, report, unknown_plan = self.generate()
        self.assertTrue(result["updated"])
        self.assertEqual(report["priorities"][0]["status"], "unknown")
        self.assertEqual(report["priorities"][0]["mode"], "assessment")
        self.assertEqual(report["priorities"][0]["candidate_evidence"], [])
        self.assertIn("not a missing skill", unknown_plan)
        self.assertIn("First attempt", unknown_plan)

    def test_answering_customer_questions_is_documented_support_work_not_just_a_title(self):
        self.save_jobs("Requirements: Customer support experience.")
        for claim in (
            "Answered customer questions by email and maintained a support request spreadsheet.",
            "Answered customer questions by email.",
        ):
            with self.subTest(claim=claim):
                self.save_cv("Customer Support Specialist", claim)
                _, report, _ = self.generate()
                support = report["priorities"][0]
                self.assertEqual(support["skill_id"], "customer_support")
                self.assertEqual(support["status"], "documented")
                documented = [item for item in support["candidate_evidence"] if item["status"] == "documented"]
                self.assertEqual([(item["id"], item["text"]) for item in documented], [("E2", claim)])

    def test_vacancy_requirements_choose_different_specific_exercises_with_citations(self):
        self.save_jobs("Requirements\nExcel and SQL skills.", "You will prepare Excel reports.")
        _, report, plan = self.generate()
        spreadsheet, sql = report["priorities"]
        self.assertEqual(spreadsheet["skill_id"], "spreadsheets")
        self.assertEqual(spreadsheet["requirement_job_count"], 2)
        self.assertEqual(sql["skill_id"], "sql")
        self.assertIn("joins", sql["exercise"])
        self.assertIn("pivot table", spreadsheet["exercise"])
        self.assertEqual(sql["requirements"][0]["snippet"], "Excel and SQL skills.")
        self.assertIn("https://example.org/jobs/operations-1", plan)
        self.save_jobs("Requirements: Zendesk experience.")
        _, report, plan = self.generate()
        self.assertEqual([x["skill_id"] for x in report["priorities"]], ["crm"])
        self.assertIn("five fictional contacts", report["priorities"][0]["exercise"])
        self.assertNotIn("pivot table", plan)

    def test_negated_future_and_partial_claims_never_become_completed_work(self):
        self.save_cv("Never used SQL.", "I plan to learn Python.", "Excel")
        self.save_jobs("Requirements: SQL, Python and Excel skills.")
        _, report, _ = self.generate()
        by_skill = {x["skill_id"]: x for x in report["priorities"]}
        self.assertEqual(by_skill["sql"]["status"], "self_reported_gap")
        self.assertEqual(by_skill["sql"]["mode"], "practice")
        self.assertEqual(by_skill["python"]["status"], "unknown")
        self.assertEqual(by_skill["python"]["mode"], "assessment")
        self.assertEqual(by_skill["spreadsheets"]["status"], "partial")
        self.assertEqual(by_skill["spreadsheets"]["mode"], "assessment")

    def test_negation_about_errors_or_tool_features_does_not_invent_a_skill_gap(self):
        self.save_cv("Used SQL with no errors.", "Created Excel spreadsheets without macros.")
        self.save_jobs("Requirements: SQL and Excel.")
        _, report, _ = self.generate()
        self.assertEqual({x["status"] for x in report["priorities"]}, {"documented"})
        self.save_cv("No experience with SQL.", "Excel knowledge is not clear.")
        _, report, _ = self.generate()
        by_skill = {x["skill_id"]: x for x in report["priorities"]}
        self.assertEqual(by_skill["sql"]["status"], "self_reported_gap")
        self.assertEqual(by_skill["spreadsheets"]["status"], "unknown")

    def test_french_requirement_section_excludes_benefit_mentions(self):
        self.save_jobs("Profil recherché\nExcel\nAvantages\nPython")
        _, report, _ = self.generate()
        self.assertEqual([x["skill_id"] for x in report["priorities"]], ["spreadsheets"])
        self.assertEqual(report["priorities"][0]["requirements"][0]["snippet"], "Excel")

    def test_company_mentions_optional_absence_and_stale_jobs_do_not_create_requirements(self):
        jobs = self.save_jobs("About us\nWe create Python tools.\nRequirements\nExcel\nBenefits\nWe prepare German classes.",
                              "No SQL experience required.", "Requirements: Zendesk experience.")
        jobs[-1]["stale"] = True
        jobs.append({**jobs[-1], "id": "J-rejected", "stale": False, "match_status": "rejected"})
        workspace.write_json(self.root / "local/jobs.json", {"jobs": jobs})
        _, report, _ = self.generate()
        self.assertEqual(report["job_sample_count"], 2)
        self.assertEqual(report["excluded_stale_jobs"], 1)
        self.assertEqual([x["skill_id"] for x in report["priorities"]], ["spreadsheets"])

    def test_requirement_negation_applies_to_its_skill_not_other_requirements(self):
        self.save_jobs("Requirements: SQL is required, no Python experience needed.",
                       "Requirements: Excel skills without macros.",
                       "Requirements: Zendesk experience is not required.")
        _, report, _ = self.generate()
        self.assertEqual({x["skill_id"] for x in report["priorities"]}, {"sql", "spreadsheets"})
        by_skill = {x["skill_id"]: x for x in report["priorities"]}
        self.assertEqual(by_skill["sql"]["requirement_job_count"], 1)
        self.assertEqual(by_skill["spreadsheets"]["requirement_job_count"], 1)
        self.assertEqual(by_skill["sql"]["requirements"][0]["job_id"], "J1")
        self.assertEqual(by_skill["spreadsheets"]["requirements"][0]["job_id"], "J2")

    def test_shared_terminal_negation_covers_the_skill_list_but_preserves_positive_clauses(self):
        self.save_jobs(
            "Requirements: Python and SQL experience are not required.",
            "Requirements: SQL is required, no Python experience needed.",
            "Requirements: Excel and Zendesk skills are not needed.",
            "Requirements: SQL is required but Python and Excel skills are not required.",
            "Requirements: SQL required, Python experience not needed.",
            "Requirements: No Python and SQL experience required.",
            "Requirements: Python and SQL experience are not required for this role.",
            "Requirements: Python and Excel are not needed for this role, SQL is required.",
        )
        _, report, _ = self.generate()
        self.assertEqual([x["skill_id"] for x in report["priorities"]], ["sql"])
        sql = report["priorities"][0]
        self.assertEqual(sql["requirement_job_count"], 4)
        self.assertEqual([source["job_id"] for source in sql["requirements"]], ["J2", "J4", "J5", "J8"])

    def test_candidate_goals_take_priority_maximum_three_and_share_real_budget(self):
        self.profile.update(weekly_hours=1.1, learning_goals=[
            {"skill": "Spreadsheets", "reason": "Make reports easier to explain."},
            {"skill": "Botanical illustration", "reason": "Prepare a small portfolio."},
        ])
        self.save_profile()
        self.save_jobs("Requirements: Excel, SQL, Python and Zendesk skills.")
        _, report, plan = self.generate()
        self.assertEqual(len(report["priorities"]), 3)
        self.assertEqual(sum(x["minutes"] for x in report["priorities"]), 66)
        self.assertEqual(report["priorities"][0]["skill"], "Spreadsheets")
        self.assertEqual(report["priorities"][1]["skill"], "Botanical illustration")
        self.assertEqual(report["priorities"][1]["requirement_job_count"], 0)
        self.assertIn("Operations Assistant", report["priorities"][1]["exercise"])
        self.assertIn("Botanical illustration", report["priorities"][1]["exercise"])
        self.assertIn("specialist checks", report["priorities"][1]["exercise"])
        self.assertIn("Prepare a small portfolio.", plan)
        self.assertEqual(report["unrecognized_goals"], ["Botanical illustration"])

    def test_ukrainian_requirements_and_cv_generate_ukrainian_plan_with_evidence(self):
        self.profile["learning_language"] = "uk"
        self.save_profile()
        self.save_cv("Використовувала Excel для звітів.")
        self.save_jobs("Вимоги\nДосвід роботи з електронними таблицями та Excel.")
        _, report, plan = self.generate()
        self.assertEqual(report["priorities"][0]["status"], "documented")
        self.assertTrue(plan.startswith("# План навчання"))
        self.assertIn("Перший крок", plan)
        self.assertIn("E1", plan)
        self.assertIn("зведеною таблицею", plan)

    def test_zero_hours_keeps_topics_paused_without_scheduled_first_action(self):
        self.profile["weekly_hours"] = 0
        self.save_profile()
        self.save_jobs("Requirements: Excel and SQL.")
        _, report, plan = self.generate()
        self.assertEqual({x["mode"] for x in report["priorities"]}, {"paused"})
        self.assertEqual(sum(x["minutes"] for x in report["priorities"]), 0)
        self.assertIn("Learning is paused", plan)
        self.assertNotIn("First action (", plan)

    def test_no_jobs_or_recognized_skills_have_honest_role_specific_fallback(self):
        _, report, plan = self.generate()
        self.assertEqual(report["job_sample_count"], 0)
        self.assertEqual(report["priorities"][0]["skill_id"], "requirement_review")
        self.assertEqual(report["priorities"][0]["status"], "unknown")
        self.assertIn("No current review leads", plan)
        self.save_jobs("Requirements: Maintain ISO certification documentation.")
        _, report, plan = self.generate()
        self.assertIn("ISO certification", plan)
        self.assertEqual(report["priorities"][0]["requirements"][0]["job_id"], "J1")

    def test_unrecognized_requirement_keeps_its_source_url_separate_from_quoted_text(self):
        self.save_jobs("Requirements: Operate a fictional orbital simulator.")
        _, report, plan = self.generate()
        requirement = report["unrecognized_requirements"][0]
        self.assertEqual(requirement["snippet"], "Operate a fictional orbital simulator.")
        url = "https://example.org/jobs/operations-1"
        self.assertIn(f"- Operations Assistant — {url}\n  > Operate a fictional orbital simulator.", plan)
        self.assertNotIn(url + ":", plan)
        self.assertEqual([line for line in plan.splitlines() if url in line],
                         [f"- Operations Assistant — {url}", f"- Operations Assistant — {url}"])

    def test_unchanged_generated_plan_is_stable_and_new_inputs_refresh_it(self):
        self.save_jobs("Requirements: Excel.")
        result, report, initial = self.generate()
        initial_hash = report["input_sha256"]
        self.assertTrue(result["updated"])
        jobs = workspace.read_json(self.root / "local/jobs.json")
        jobs["searched_at"] = "2026-12-31"
        workspace.write_json(self.root / "local/jobs.json", jobs)
        result, report, repeated = self.generate()
        self.assertFalse(result["updated"])
        self.assertEqual(report["input_sha256"], initial_hash)
        self.assertEqual(repeated, initial)
        self.save_jobs("Requirements: SQL.")
        result, report, changed = self.generate()
        self.assertTrue(result["updated"])
        self.assertFalse(result["preserved"])
        self.assertNotEqual(report["input_sha256"], initial_hash)
        self.assertIn("SQL", changed)
        self.assertNotIn("pivot table", changed)

    def test_existing_manual_plan_and_edited_suggestions_are_never_overwritten(self):
        original = "# My plan\n\nPersonal progress and notes."
        workspace.write_text(self.root / "local/learning-plan.md", original)
        self.save_jobs("Requirements: Excel.")
        result, _, suggested = self.generate()
        self.assertTrue(result["preserved"])
        self.assertEqual(result["suggestion_path"], "local/learning-plan.suggested.md")
        self.assertIn("pivot table", suggested)
        self.assertEqual((self.root / result["path"]).read_text(encoding="utf-8"), original)
        workspace.write_text(self.root / result["suggestion_path"], "Candidate annotations on suggestion")
        self.save_jobs("Requirements: SQL.")
        result, _, suggested = self.generate()
        self.assertRegex(result["suggestion_path"], r"local/learning-plan\.suggested-[a-f0-9]+\.md")
        self.assertIn("joins", suggested)
        self.assertEqual((self.root / "local/learning-plan.suggested.md").read_text(encoding="utf-8"),
                         "Candidate annotations on suggestion")
        self.assertEqual((self.root / result["path"]).read_text(encoding="utf-8"), original)
        state = workspace.read_json(self.root / "local/learning-plan-state.json")
        self.assertEqual(state["suggestion_path"], result["suggestion_path"])

    def test_editing_generated_plan_changes_future_runs_to_suggestions(self):
        self.save_jobs("Requirements: Excel.")
        self.generate()
        workspace.write_text(self.root / "local/learning-plan.md", "Progress: finished the spreadsheet.")
        self.save_jobs("Requirements: SQL.")
        result, _, suggested = self.generate()
        self.assertTrue(result["preserved"])
        self.assertIn("joins", suggested)
        self.assertEqual((self.root / result["path"]).read_text(encoding="utf-8"),
                         "Progress: finished the spreadsheet.")


if __name__ == "__main__":
    unittest.main()
