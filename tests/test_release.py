"""Release privacy behavior, using generated synthetic fixtures only."""

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from careerkit.release import DEMO_IMAGE, MANIFEST, check_public, package_public


class PublicReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "starter"
        self.root.mkdir()
        self.write("career.py", 'print("Career starter")\n')
        self.write("README.md", "# Career Starter\n")
        self.entries = [MANIFEST, "career.py", "README.md"]
        self.manifest()
        self.env = patch.dict(os.environ, {"CAREER_PRIVATE_TOKENS": ""})
        self.env.start()
        self.addCleanup(self.env.stop)

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def manifest(self):
        self.write(MANIFEST, json.dumps(self.entries, indent=2) + "\n")

    def test_package_contains_exact_reviewed_sources_and_no_private_state(self):
        self.write("local/profile.json", '{"name": "Private Fixture"}')
        self.write(".git/config", "private remote")
        self.write("__pycache__/module.pyc", "cache")
        self.write("dist/earlier.zip", "old archive")
        self.assertEqual(check_public(self.root), [])

        output = self.root / "dist" / "release.zip"
        self.assertEqual(package_public(self.root, output), output)
        with zipfile.ZipFile(output) as archive:
            self.assertEqual(set(archive.namelist()), set(self.entries))
            for name in self.entries:
                self.assertEqual(archive.read(name), (self.root / name).read_bytes())
        self.assertEqual(check_public(self.root), [])

    def test_unlisted_source_or_document_blocks_packaging(self):
        self.write("notes.md", "Candidate draft")
        issues = check_public(self.root)
        self.assertTrue(any("notes.md: file is not in" in issue for issue in issues))
        output = self.root / "dist" / "release.zip"
        with self.assertRaises(ValueError):
            package_public(self.root, output)
        self.assertFalse(output.exists())

    def test_package_accepts_only_the_reviewed_demo_image(self):
        reviewed = (Path(__file__).resolve().parents[1] / DEMO_IMAGE).read_bytes()
        image = self.root / DEMO_IMAGE
        image.parent.mkdir(parents=True)
        image.write_bytes(reviewed)
        self.entries.append(DEMO_IMAGE)
        self.manifest()

        archive_path = package_public(self.root, self.root / "dist" / "demo.zip")
        with zipfile.ZipFile(archive_path) as archive:
            self.assertEqual(archive.read(DEMO_IMAGE), reviewed)

        image.write_bytes(reviewed + b"extra data")
        with self.assertRaisesRegex(ValueError, "differs from the reviewed demo screenshot"):
            package_public(self.root, self.root / "dist" / "changed.zip")

    def test_ci_workflow_receives_the_public_text_scan(self):
        workflow = ".github/workflows/ci.yml"
        self.write(workflow, "# " + "candidate" + "@" + "real-mail.org")
        self.entries.append(workflow)
        self.manifest()
        self.assertEqual(check_public(self.root), [f"{workflow}: non-example email address."])

    def test_manifest_rejects_runtime_paths_traversal_and_binary_files(self):
        for entry in ("local/profile.json", "../private.md", "/outside.md",
                      "docs\\notes.md", "docs/./notes.md", "templates/cv.pdf",
                      "docs/demo/other.png", ".github/workflows/other.yml"):
            with self.subTest(entry=entry):
                self.entries = [MANIFEST, "career.py", "README.md", entry]
                self.manifest()
                self.assertTrue(any("not an allowed public source path" in issue
                                    for issue in check_public(self.root)))

    def test_invalid_missing_duplicate_or_nontext_manifest_fails_closed(self):
        for content in ("{", "{}", '["career.py"]',
                        json.dumps([MANIFEST, MANIFEST, "career.py", "README.md"])):
            with self.subTest(content=content):
                self.write(MANIFEST, content)
                self.assertTrue(check_public(self.root))
        (self.root / MANIFEST).unlink()
        self.assertTrue(check_public(self.root))

    def test_missing_source_and_nontext_source_are_detected(self):
        (self.root / "career.py").unlink()
        self.assertTrue(any("career.py: listed public source file is missing" in issue
                            for issue in check_public(self.root)))
        (self.root / "career.py").write_bytes(b"\xff\xfe")
        self.assertTrue(any("readable UTF-8 text" in issue
                            for issue in check_public(self.root)))

    def test_contact_paths_and_credentials_fail_without_echoing_values(self):
        fixtures = [
            ("person" + "@" + "real-mail.org", "non-example email"),
            ("C:" + "\\Users\\" + "candidate\\resume.md", "personal home path"),
            ("/" + "home/" + "candidate/resume.md", "personal home path"),
            ("AK" + "IA" + "X" * 16, "possible credential"),
            ("gh" + "p_" + "x" * 36, "possible credential"),
            ("-----BEGIN " + "PRIVATE KEY-----", "possible credential"),
            ('api_' + 'key = "' + "x" * 28 + '"', "possible credential"),
            ("https:" + "//fixture:pass@" + "test.invalid", "possible credential"),
        ]
        for value, expected in fixtures:
            with self.subTest(expected=expected):
                self.write("README.md", value)
                issues = check_public(self.root)
                self.assertTrue(any(expected in issue for issue in issues), issues)
                self.assertNotIn(value, "\n".join(issues))

    def test_reserved_example_contacts_are_allowed(self):
        self.write("README.md", "\n".join((
            "candidate@example.com", "candidate@example.org",
            "candidate@example.net", "candidate@example.test",
        )))
        self.assertEqual(check_public(self.root), [])

    def test_private_tokens_are_optional_case_insensitive_and_not_reported(self):
        token = "Synthetic Candidate Identity"
        self.write("README.md", token.upper())
        self.assertEqual(check_public(self.root), [])
        with patch.dict(os.environ, {"CAREER_PRIVATE_TOKENS": json.dumps([token])}):
            issues = check_public(self.root)
        self.assertEqual(issues, ["README.md: private identity token."])
        self.assertNotIn(token, "\n".join(issues))

    def test_invalid_private_token_config_fails_closed(self):
        for value in ("not json", "{}", '[""]', "[42]"):
            with self.subTest(value=value):
                with patch.dict(os.environ, {"CAREER_PRIVATE_TOKENS": value}):
                    self.assertTrue(any("CAREER_PRIVATE_TOKENS" in issue
                                        for issue in check_public(self.root)))

    def test_existing_archive_remains_byte_identical(self):
        output = self.root / "dist" / "release.zip"
        output.parent.mkdir()
        output.write_bytes(b"existing archive")
        with self.assertRaises(FileExistsError):
            package_public(self.root, output)
        self.assertEqual(output.read_bytes(), b"existing archive")

    def test_output_must_be_zip_and_inside_root_only_under_dist(self):
        with self.assertRaises(ValueError):
            package_public(self.root, self.root / "release.txt")
        with self.assertRaises(ValueError):
            package_public(self.root, self.root / "release.zip")
        self.assertFalse((self.root / "release.zip").exists())

    def test_symlink_to_private_content_is_refused(self):
        target = self.write("local/private.md", "private material")
        docs = self.root / "docs"
        if os.name == "nt":
            # Directory junctions work for ordinary Windows accounts on 3.10+.
            import _winapi
            _winapi.CreateJunction(str(target.parent), str(docs))
        else:
            docs.mkdir()
            (docs / "private.md").symlink_to(target)
        self.entries.append("docs/private.md")
        self.manifest()
        self.assertTrue(any("symbolic links are not allowed" in issue
                            for issue in check_public(self.root)))
        with self.assertRaises(ValueError):
            package_public(self.root, self.root / "dist" / "release.zip")


if __name__ == "__main__":
    unittest.main()
