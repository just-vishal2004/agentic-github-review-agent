import unittest

from review import inspect_files, select_files


class ReviewTests(unittest.TestCase):
    def test_select_files_skips_vendor_and_caps_results(self):
        paths = [f"src/file{i}.py" for i in range(25)] + ["vendor/lib/tool.py", "README.md"]
        selected = select_files(paths, limit=5)
        self.assertEqual(len(selected), 5)
        self.assertIn("README.md", selected)
        self.assertNotIn("vendor/lib/tool.py", selected)

    def test_finds_requested_quality_signals(self):
        paths = ["README.md", "src/app.py", "tests/test_app.py"]
        content = "# TODO clean up\ntry:\n    run()\nexcept Exception:\n    pass\n" + ("# line\n" * 500)
        findings = inspect_files(paths, {"src/app.py": content})
        titles = {finding["title"] for finding in findings}
        self.assertEqual(titles, {"TODO or FIXME marker", "Broad Exception handling", "Unusually long file"})
        self.assertTrue(all({"severity", "file", "line", "title", "detail", "suggestion"} <= finding.keys() for finding in findings))

    def test_reports_missing_readme_and_tests(self):
        findings = inspect_files(["src/app.py"], {"src/app.py": "print('hello')"})
        self.assertEqual({item["title"] for item in findings}, {"Missing README", "No obvious tests"})


if __name__ == "__main__":
    unittest.main()
