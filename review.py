import re


MAX_FILES = 20
MAX_FILE_BYTES = 200_000
LONG_FILE_LINES = 500
SKIP_PARTS = {".git", ".tox", "node_modules", "vendor", "vendors", "third_party", "generated", "dist", "build", "target", "__pycache__", ".venv", "venv", "coverage", "htmlcov", "pods", "bower_components"}
SOURCE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rs", ".rb", ".php", ".c", ".h", ".cpp", ".cs", ".swift", ".kt", ".sh"}


def _is_skipped(path):
    parts = path.lower().split("/")
    return any(part in SKIP_PARTS for part in parts) or any(part.startswith(".") for part in parts)


def _is_readme(path):
    return "/" not in path and path.lower().startswith("readme")


def _is_manifest(path):
    name = path.rsplit("/", 1)[-1].lower()
    return name in {"pyproject.toml", "requirements.txt", "package.json", "go.mod", "cargo.toml", "gemfile", "pom.xml"}


def _is_test(path):
    lower = path.lower()
    basename = lower.rsplit("/", 1)[-1]
    return "/tests/" in f"/{lower}/" or "/test/" in f"/{lower}/" or basename.startswith("test_") or ".test." in basename or ".spec." in basename


def select_files(paths, limit=MAX_FILES, focus="general"):
    candidates = [path for path in paths if not _is_skipped(path)]
    if focus == "tests":
        candidates = [path for path in candidates if _is_test(path) or path.lower().endswith(tuple(SOURCE_SUFFIXES))]
        candidates.sort(key=lambda path: (not _is_test(path), path.lower()))
    elif focus == "maintainability":
        candidates = [path for path in candidates if _is_manifest(path) or (not _is_test(path) and path.lower().endswith(tuple(SOURCE_SUFFIXES)))]
        candidates.sort(key=lambda path: (not _is_manifest(path), path.lower()))
    else:
        candidates = [path for path in candidates if _is_readme(path) or _is_manifest(path) or path.lower().endswith(tuple(SOURCE_SUFFIXES))]
        candidates.sort(key=lambda path: (not _is_readme(path), not _is_manifest(path), path.lower()))
    return candidates[:limit]


def inspect_files(paths, contents):
    findings = []
    if not any(_is_readme(path) for path in paths):
        findings.append({"severity": "medium", "file": None, "line": None, "title": "Missing README", "detail": "No README file was found in the repository tree.", "suggestion": "Add a README describing the project, setup, and basic usage."})
    if not any(_is_test(path) for path in paths):
        findings.append({"severity": "medium", "file": None, "line": None, "title": "No obvious tests", "detail": "No files or directories with common test naming patterns were found.", "suggestion": "Add automated tests for important behavior and edge cases."})

    for path, content in contents.items():
        if len(content.encode("utf-8")) > MAX_FILE_BYTES:
            continue
        lines = content.splitlines()
        for number, line in enumerate(lines, 1):
            if re.search(r"\b(?:TODO|FIXME)\b", line, re.IGNORECASE):
                findings.append({"severity": "low", "file": path, "line": number, "title": "TODO or FIXME marker", "detail": line.strip()[:240], "suggestion": "Resolve the marker or link it to a tracked issue with clear ownership."})
            if re.search(r"\bexcept\s+Exception\b", line):
                findings.append({"severity": "medium", "file": path, "line": number, "title": "Broad Exception handling", "detail": "This line catches Exception, which can hide unrelated errors.", "suggestion": "Catch the expected exception types and handle them explicitly."})
        if len(lines) > LONG_FILE_LINES:
            findings.append({"severity": "low", "file": path, "line": None, "title": "Unusually long file", "detail": f"File contains {len(lines)} lines, above the {LONG_FILE_LINES}-line review threshold.", "suggestion": "Consider splitting distinct responsibilities into smaller modules."})
    return findings
