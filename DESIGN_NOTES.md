# Design Notes

## Design decisions

After URL validation, a deterministic planner uses goal keywords to choose a general, tests, or maintainability focus. It produces executable steps, and the workflow follows them. The selected focus changes which files are prioritized. This goal-dependent planner is limited to repository review and does not interpret arbitrary instructions. The visible plan makes the sequence straightforward to explain.

Python's standard library covers the current needs: `argparse` for the CLI, `urllib` for GitHub requests, and standard JSON and text processing. An LLM or agent framework would add setup and less predictable behavior without helping with this narrow workflow.

Responsibilities are split across three operations. The GitHub API client retrieves metadata, the tree, and file contents. File selection chooses a bounded set of README, manifest, and source paths while filtering common generated and vendor paths. Deterministic checks look for missing README or obvious tests, TODO/FIXME markers, broad `except Exception` handling, and long files.

The API client retries transient HTTP 429 and 5xx responses and network or timeout errors a limited number of times. The recovery demonstration injects an HTTP 503 through a fixture-backed opener attached to that same client. The shared retry path handles the error, then the opener serves local fixture data. This exercises recovery without presenting the injected response as a real GitHub outage or depending on network access.

## Limitations

The checks are simple signals and can produce false positives, especially for TODO words used in documentation. Only up to 20 selected files are fetched for inspection, and oversized or unavailable files are marked skipped. Unauthenticated GitHub API access can be rate limited; the client does not specially handle GitHub's HTTP 403 rate-limit responses.

Planning depends on a small set of keywords rather than broad language understanding. The checks do not understand code semantics, execute repository code, or judge whether a finding matters in context. They cover a small set of languages and patterns.

## What I would do differently with more time

I would first improve contextual checks and make skipped or rate-limited API results easier to interpret. I would broaden language-specific checks only alongside a representative repository set for evaluation. Optional LLM-assisted analysis could be explored later, with deterministic checks retained and model findings clearly separated. I would measure its usefulness and false-positive rate before making it part of the normal workflow.

## Testing and validation

Automated tests cover focus selection, plan execution order, URL validation, file selection and checks, retry behavior, partial results, and oversized-file accounting. The offline recovery demonstration injects one labeled 503, verifies the retry path, and reviews the fixture repository through the normal workflow.
