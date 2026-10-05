# Offline recovery demo transcript

Captured from `python3 agent.py --demo-recovery`.

```text
Running offline recovery demo with a fixture-backed repository.
Goal:
Review https://github.com/demo-owner/demo-repo
Preflight:
Repository: demo-owner/demo-repo
Review focus: general
Plan:
1. Fetch repository metadata and file tree
2. Select relevant repository files
3. Inspect selected files for code-quality signals
4. Summarize findings

Step 1: Fetch repository metadata and file tree...
[DEMO] Injected HTTP 503 (fixture transport, not GitHub)
[RETRY] Retrying request
[SUCCESS] Request completed with fixture data

Step 2: Select relevant repository files...
Selected 3 files for review.

Step 3: Inspect selected files for code-quality signals...

Step 4: Summarize findings...
Reviewed 3 files; found 1 finding.

{
  "repository": "demo-owner/demo-repo",
  "url": "https://github.com/demo-owner/demo-repo",
  "review_status": "complete",
  "summary": "Reviewed 3 files and found 1 finding.",
  "files_requested": 3,
  "files_reviewed": 3,
  "files_skipped": [],
  "findings": [
    {
      "severity": "low",
      "file": "src/app.py",
      "line": 2,
      "title": "TODO or FIXME marker",
      "detail": "# TODO: validate the input",
      "suggestion": "Resolve the marker or link it to a tracked issue with clear ownership."
    }
  ],
  "limitations": [
    "Review uses bounded deterministic checks and does not assess runtime behavior or full project context."
  ]
}
```
