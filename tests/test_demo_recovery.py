import unittest

from agent import build_demo_api, run_review


class RecoveryDemoTests(unittest.TestCase):
    def test_injected_503_retries_and_returns_complete_fixture_review(self):
        events = []
        api, state = build_demo_api(output=events.append)
        result = run_review("Review https://github.com/demo-owner/demo-repo", api=api, output=lambda message: None)

        metadata_url = "https://api.github.com/repos/demo-owner/demo-repo"
        self.assertEqual(state["injected_failures"], 1)
        self.assertEqual(state["attempts_by_url"][metadata_url], 2)
        self.assertGreater(state["successful_responses"], 0)
        self.assertEqual(result["review_status"], "complete")
        self.assertEqual(result["files_requested"], 3)
        self.assertEqual(result["files_reviewed"], 3)
        self.assertEqual(result["files_skipped"], [])
        self.assertIn("[DEMO] Injected HTTP 503", events[0])
        self.assertEqual(events[1], "[RETRY] Retrying request")
        self.assertEqual(events[2], "[SUCCESS] Request completed with fixture data")
        self.assertLess(events.index("[DEMO] Injected HTTP 503 (fixture transport, not GitHub)"), events.index("[RETRY] Retrying request"))

    def test_demo_failure_is_reported_instead_of_silently_ignored(self):
        events = []
        api, state = build_demo_api(output=events.append)
        result = run_review("Review https://github.com/demo-owner/demo-repo", api=api, output=lambda message: None)

        self.assertEqual(state["injected_failures"], 1)
        self.assertTrue(any("not GitHub" in event for event in events))
        self.assertEqual(result["repository"], "demo-owner/demo-repo")


if __name__ == "__main__":
    unittest.main()
