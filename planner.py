import re


TEST_FOCUS = re.compile(r"\b(?:tests?|testing|coverage|pytest|unittest)\b", re.IGNORECASE)
MAINTAINABILITY_FOCUS = re.compile(
    r"\b(?:maintain\w*|readab\w*|refactor\w*|complexity|technical debt)\b",
    re.IGNORECASE,
)


PLANS = {
    "general": [
        ("fetch_repository", "Fetch repository metadata and file tree"),
        ("select_files", "Select relevant repository files"),
        ("inspect_files", "Inspect selected files for code-quality signals"),
        ("summarize", "Summarize findings"),
    ],
    "tests": [
        ("fetch_repository", "Fetch repository metadata and file tree"),
        ("select_files", "Identify source and test files"),
        ("inspect_files", "Check for obvious tests and inspect selected source/test files for quality signals"),
        ("summarize", "Summarize test-related findings"),
    ],
    "maintainability": [
        ("fetch_repository", "Fetch repository metadata and file tree"),
        ("select_files", "Select source and dependency files"),
        ("inspect_files", "Inspect selected files for maintainability signals"),
        ("summarize", "Summarize maintainability findings"),
    ],
}


def create_plan(goal):
    if TEST_FOCUS.search(goal):
        focus = "tests"
    elif MAINTAINABILITY_FOCUS.search(goal):
        focus = "maintainability"
    else:
        focus = "general"
    return {"focus": focus, "steps": PLANS[focus]}
