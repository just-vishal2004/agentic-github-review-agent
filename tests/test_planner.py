import unittest

from planner import create_plan


class PlannerTests(unittest.TestCase):
    def test_general_code_quality_goal_uses_general_plan(self):
        plan = create_plan("Review https://github.com/example/project for code quality")
        self.assertEqual(plan["focus"], "general")
        self.assertEqual(plan["steps"][1][1], "Select relevant repository files")
        self.assertEqual(plan["steps"][2][1], "Inspect selected files for code-quality signals")

    def test_tests_goal_uses_tests_plan(self):
        plan = create_plan("Review https://github.com/example/project for test coverage")
        self.assertEqual(plan["focus"], "tests")
        self.assertEqual(plan["steps"][1][1], "Identify source and test files")
        self.assertNotEqual(plan["steps"], create_plan("Review https://github.com/example/project for code quality")["steps"])

    def test_maintainability_goal_uses_maintainability_plan(self):
        plan = create_plan("Review https://github.com/example/project for maintainability")
        self.assertEqual(plan["focus"], "maintainability")
        self.assertEqual(plan["steps"][1][1], "Select source and dependency files")
        self.assertNotEqual(plan["steps"], create_plan("Review https://github.com/example/project for code quality")["steps"])

    def test_unrelated_goal_falls_back_to_general_plan(self):
        plan = create_plan("Summarize the public repository at https://github.com/example/project")
        self.assertEqual(plan, create_plan("Review https://github.com/example/project for code quality"))


if __name__ == "__main__":
    unittest.main()
