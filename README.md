# GitHub Repository Reviewer

A small read-only CLI that accepts a natural-language review goal, reads a public GitHub repository, and reports a few deterministic code-quality signals as JSON. It uses only the Python standard library and does not need a GitHub token for public repositories.

## Requirements

- Python 3.9 or newer
- Network access to `api.github.com` for live reviews

## Setup

The project uses only the Python standard library, so no package installation is required. Run the commands below from the project directory.

## Run

```sh
python3 agent.py "Review https://github.com/psf/requests for potential code quality issues."
```

To run the offline recovery demonstration, which injects one labeled HTTP 503 into the normal retry path and then serves a small local fixture, run:

```sh
python3 agent.py --demo-recovery
```

The injected failure is part of the fixture transport and is not a response from GitHub. See [the captured transcript](examples/offline_recovery_demo.md).

The argument is a natural-language goal containing exactly one repository URL in the form `https://github.com/OWNER/REPOSITORY`, optionally followed by a trailing slash. For example: `Review https://github.com/psf/requests for potential code quality issues.` GitHub subpages such as issues and file URLs are rejected. After URL preflight, a deterministic keyword planner chooses a general, tests, or maintainability focus, prints a matching plan, and the workflow executes those steps before printing JSON. Goals without a recognized focus use the general review.

The workflow has three operations. The GitHub API client reads repository metadata, the file tree, and selected file contents. File selection chooses at most 20 paths for the detected focus: README, manifests, and source for general reviews; source and test files for tests reviews; and source and dependency manifests for maintainability reviews. It filters common generated, hidden, and vendor paths. Deterministic checks look for a missing README, TODO/FIXME markers, Python-style broad `except Exception` handling, files over 500 lines, and the absence of common test path or filename patterns. Selected binary or non-UTF-8 contents and fetched files over the review size limit are skipped.

API requests have a 10-second timeout. HTTP 429 and 5xx errors, URL errors, and timeouts are retried up to two times. Other HTTP errors, including 403, are not retried. The JSON result reports `review_status` as `complete` or `partial`, numeric `files_requested` and `files_reviewed` counts, and `files_skipped` paths with reasons.

## Run tests

```sh
python3 -m unittest discover -s tests -v
```

The tests use an in-memory fake API for the agent workflow and do not require network access.

## Project documents and transcripts

- [Architecture](ARCHITECTURE.md)
- [Design notes](DESIGN_NOTES.md)
- [Normal review run](examples/normal_run.md), an actual live attempt that received HTTP 403 before producing a review result
- [Invalid input run](examples/invalid_input.md)
- [Offline recovery demo](examples/offline_recovery_demo.md)

The planner uses simple keyword rules. Test-related words select the tests focus; maintainability, readability, refactoring, complexity, or the phrase `technical debt` select maintainability. If both categories appear, the tests focus takes precedence.

## Limitations

These checks are simple signals, not a full code review. They can produce false positives and do not execute repository code, inspect the full project, infer intent, or assess runtime behavior. Planning is deterministic and uses a small set of goal-keyword-selected plan templates for this repository review task. Unauthenticated GitHub API access can be rate limited, and HTTP 403 responses are not specially handled. Large repositories may have truncated trees or exceed the bounded review scope.
