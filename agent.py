import argparse
import base64
import io
import json
import re
import sys
from email.message import Message
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlparse

from github_api import GitHubAPI, GitHubAPIError
from planner import create_plan
from review import MAX_FILE_BYTES, inspect_files, select_files


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "demo_repo.json"


GITHUB_URL_RE = re.compile(r"https?://github\.com/[^\s<>\"')]+", re.IGNORECASE)


def extract_repository(goal):
    urls = GITHUB_URL_RE.findall(goal)
    usable = []
    for value in urls:
        value = value.rstrip(".,!?;:")
        parsed = urlparse(value)
        match = re.fullmatch(r"/([^/]+)/([^/]+)/?", parsed.path)
        if (
            parsed.scheme.lower() == "https"
            and parsed.hostname
            and parsed.hostname.lower() == "github.com"
            and not parsed.query
            and not parsed.fragment
            and match
        ):
            owner, repo = match.groups()
            if owner not in {"login", "settings", "features"}:
                usable.append((owner, repo))
    if len(usable) != 1:
        raise ValueError("Goal must contain exactly one public GitHub repository URL in the form https://github.com/OWNER/REPOSITORY.")
    return usable[0]


def run_review(goal, api=None, output=print):
    owner, repo = extract_repository(goal)
    output("Goal:")
    output(goal)
    output("Preflight:")
    output(f"Repository: {owner}/{repo}")
    plan = create_plan(goal)
    focus = plan["focus"]
    output(f"Review focus: {focus}")
    output("Plan:")
    for number, (action, description) in enumerate(plan["steps"], 1):
        output(f"{number}. {description}")

    api = api or GitHubAPI()
    paths = []
    selected = []
    file_contents = {}
    skipped_files = []
    findings = []
    result = None

    for number, (action, description) in enumerate(plan["steps"], 1):
        output(f"\nStep {number}: {description}...")
        if action == "fetch_repository":
            metadata = api.get_repository(owner, repo)
            tree = api.get_tree(owner, repo, metadata["default_branch"])
            paths = [entry["path"] for entry in tree if entry.get("type") == "blob"]
        elif action == "select_files":
            selected = select_files(paths, focus=focus)
            output(f"Selected {len(selected)} files for review.")
        elif action == "inspect_files":
            for path in selected:
                try:
                    content = api.get_file(owner, repo, path)
                    if len(content.encode("utf-8")) > MAX_FILE_BYTES:
                        reason = "file exceeds review size limit"
                        skipped_files.append({"path": path, "reason": reason})
                        output(f"Skipping {path}: {reason}")
                    else:
                        file_contents[path] = content
                except GitHubAPIError as exc:
                    reason = str(exc).split(" for https://", 1)[0][:160]
                    skipped_files.append({"path": path, "reason": reason})
                    output(f"Skipping {path}: {reason}")
            findings = inspect_files(paths, file_contents)
        elif action == "summarize":
            finding_count = len(findings)
            finding_label = "finding" if finding_count == 1 else "findings"
            result = {
                "repository": f"{owner}/{repo}",
                "url": f"https://github.com/{owner}/{repo}",
                "review_status": "partial" if skipped_files else "complete",
                "summary": f"Reviewed {len(file_contents)} files and found {finding_count} {finding_label}.",
                "files_requested": len(selected),
                "files_reviewed": len(file_contents),
                "files_skipped": skipped_files,
                "findings": findings,
                "limitations": ["Review uses bounded deterministic checks and does not assess runtime behavior or full project context."],
            }
            output(f"Reviewed {len(file_contents)} files; found {finding_count} {finding_label}.\n")
            output(json.dumps(result, indent=2))
    return result


def build_demo_api(output=print):
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    state = {"attempts_by_url": {}, "injected_failures": 0, "successful_responses": 0}
    retry_notice_printed = False

    def opener(request, timeout):
        nonlocal retry_notice_printed
        url = request.full_url
        attempts = state["attempts_by_url"].get(url, 0) + 1
        state["attempts_by_url"][url] = attempts
        if state["injected_failures"] == 0:
            state["injected_failures"] += 1
            output("[DEMO] Injected HTTP 503 (fixture transport, not GitHub)")
            headers = Message()
            raise HTTPError(url, 503, "injected demo failure", headers, None)

        parsed = urlparse(url)
        prefix = "/repos/demo-owner/demo-repo"
        if parsed.path == prefix:
            payload = fixture["repository"]
        elif parsed.path == prefix + "/git/trees/main":
            payload = {"truncated": False, "tree": fixture["tree"]}
        elif parsed.path.startswith(prefix + "/contents/"):
            path = parsed.path[len(prefix + "/contents/"):]
            content = fixture["files"].get(path)
            if content is None:
                raise HTTPError(url, 404, "fixture path not found", Message(), None)
            encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
            payload = {"encoding": "base64", "content": encoded}
        else:
            raise HTTPError(url, 404, "fixture endpoint not found", Message(), None)

        state["successful_responses"] += 1
        if not retry_notice_printed:
            output("[SUCCESS] Request completed with fixture data")
            retry_notice_printed = True
        return io.BytesIO(json.dumps(payload).encode("utf-8"))

    def retry_notice(delay):
        output("[RETRY] Retrying request")

    return GitHubAPI(opener=opener, sleeper=retry_notice), state


def run_recovery_demo(output=print):
    output("Running offline recovery demo with a fixture-backed repository.")
    api, _ = build_demo_api(output)
    result = run_review("Review https://github.com/demo-owner/demo-repo", api=api, output=output)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Review a public GitHub repository from a natural-language goal.")
    parser.add_argument("goal", nargs="?", help='Natural-language goal containing one repository URL, e.g. "Review https://github.com/psf/requests"')
    parser.add_argument("--demo-recovery", action="store_true", help="Run the offline injected-failure recovery demonstration")
    args = parser.parse_args(argv)
    try:
        if args.demo_recovery:
            run_recovery_demo()
        elif args.goal:
            run_review(args.goal)
        else:
            parser.error("provide a goal containing a repository URL, or use --demo-recovery")
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except GitHubAPIError as exc:
        print(f"GitHub review failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
