import unittest
from unittest.mock import patch

import agent
from agent import extract_repository, run_review
from github_api import GitHubAPIError
from review import MAX_FILE_BYTES


class FakeAPI:
    def __init__(self, events=None):
        self.events = events

    def get_repository(self, owner, repo):
        if self.events is not None:
            self.events.append(("api", "get_repository"))
        return {"default_branch": "main"}

    def get_tree(self, owner, repo, branch):
        if self.events is not None:
            self.events.append(("api", "get_tree"))
        return [
            {"path": "README.md", "type": "blob"},
            {"path": "pyproject.toml", "type": "blob"},
            {"path": "src/app.py", "type": "blob"},
            {"path": "tests/test_app.py", "type": "blob"},
        ]

    def get_file(self, owner, repo, path):
        if self.events is not None:
            self.events.append(("api", "get_file", path))
        if path == "README.md":
            return "# sample\n"
        if path == "pyproject.toml":
            return "[project]\nname = 'sample'\n"
        return "# TODO: improve\n"


class AgentTests(unittest.TestCase):
    def test_extracts_repository_from_goal(self):
        self.assertEqual(extract_repository("Review https://github.com/psf/requests for quality."), ("psf", "requests"))
        self.assertEqual(extract_repository("Review https://github.com/psf/requests/"), ("psf", "requests"))

    def test_requires_exactly_one_usable_repository(self):
        invalid_goals = (
            "Review this repository",
            "Review https://github.com/psf/requests and https://github.com/pallets/flask",
            "Review https://github.com/psf/requests/issues/123",
            "Review https://github.com/psf/requests/pulls",
            "Review https://github.com/psf/requests/blob/main/file.py",
        )
        for goal in invalid_goals:
            with self.subTest(goal=goal), self.assertRaises(ValueError):
                extract_repository(goal)

    def test_invalid_url_error_explains_expected_input(self):
        with self.assertRaisesRegex(ValueError, "repository URL"):
            extract_repository("Review https://github.com/psf/requests/issues/123")

    def test_prints_plan_before_api_work_and_returns_result(self):
        events = []
        create_plan = agent.create_plan

        def record_planning(goal):
            events.append(("planner", goal))
            return create_plan(goal)

        with patch("agent.create_plan", side_effect=record_planning):
            result = run_review("Review https://github.com/example/project", api=FakeAPI(events), output=events.append)
        preflight = events.index("Preflight:")
        planner_call = next(index for index, event in enumerate(events) if isinstance(event, tuple) and event[0] == "planner")
        plan_finished = events.index("4. Summarize findings")
        first_api_call = next(index for index, event in enumerate(events) if isinstance(event, tuple) and event[0] == "api")
        self.assertLess(preflight, planner_call)
        self.assertLess(planner_call, plan_finished)
        self.assertLess(plan_finished, first_api_call)
        self.assertEqual(result["repository"], "example/project")
        self.assertEqual(result["files_requested"], 4)
        self.assertEqual(result["files_reviewed"], 4)
        self.assertIn("TODO or FIXME marker", {item["title"] for item in result["findings"]})
        self.assertEqual(result["review_status"], "complete")
        self.assertEqual(result["files_skipped"], [])

    def test_tests_focus_changes_plan_and_selected_files(self):
        events = []
        messages = []
        result = run_review(
            "Review https://github.com/example/project for test coverage",
            api=FakeAPI(events),
            output=messages.append,
        )
        self.assertIn("Review focus: tests", messages)
        self.assertIn("2. Identify source and test files", messages)
        fetched_paths = [event[2] for event in events if event[0] == "api" and event[1] == "get_file"]
        self.assertEqual(fetched_paths, ["tests/test_app.py", "src/app.py"])
        self.assertEqual(result["files_requested"], 2)

    def test_maintainability_focus_selects_source_and_manifest_files(self):
        events = []
        messages = []
        result = run_review(
            "Review https://github.com/example/project for maintainability",
            api=FakeAPI(events),
            output=messages.append,
        )
        self.assertIn("Review focus: maintainability", messages)
        self.assertIn("2. Select source and dependency files", messages)
        fetched_paths = [event[2] for event in events if event[0] == "api" and event[1] == "get_file"]
        self.assertEqual(fetched_paths, ["pyproject.toml", "src/app.py"])
        self.assertEqual(result["files_requested"], 2)

    def test_invalid_url_is_rejected_before_planner_runs(self):
        with patch("agent.create_plan") as planner:
            with self.assertRaises(ValueError):
                run_review("Review https://github.com/example/project/issues/1", api=FakeAPI(), output=lambda message: None)
        planner.assert_not_called()

    def test_failed_file_fetch_returns_partial_review(self):
        class PartiallyFailingAPI(FakeAPI):
            def get_file(self, owner, repo, path):
                if path == "src/app.py":
                    raise GitHubAPIError("GitHub API returned HTTP 403 for https://api.github.com/example")
                return super().get_file(owner, repo, path)

        result = run_review("Review https://github.com/example/project", api=PartiallyFailingAPI(), output=lambda message: None)
        self.assertEqual(result["review_status"], "partial")
        self.assertEqual(result["files_requested"], 4)
        self.assertEqual(result["files_reviewed"], 3)
        self.assertEqual(result["files_skipped"], [{"path": "src/app.py", "reason": "GitHub API returned HTTP 403"}])

    def test_oversized_fetched_file_is_skipped_from_review_count(self):
        class OversizedAPI(FakeAPI):
            def get_file(self, owner, repo, path):
                if path == "src/app.py":
                    return "x" * (MAX_FILE_BYTES + 1)
                return super().get_file(owner, repo, path)

        result = run_review("Review https://github.com/example/project", api=OversizedAPI(), output=lambda message: None)
        self.assertEqual(result["review_status"], "partial")
        self.assertEqual(result["files_requested"], 4)
        self.assertEqual(result["files_reviewed"], 3)
        self.assertEqual(result["files_skipped"], [{"path": "src/app.py", "reason": "file exceeds review size limit"}])


if __name__ == "__main__":
    unittest.main()
