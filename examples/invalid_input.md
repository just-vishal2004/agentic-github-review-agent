# Invalid input run

Captured from this actual CLI execution:

```sh
python3 agent.py 'Review https://github.com/octocat/Hello-World/issues/1 for potential code quality issues.'
```

```text
Error: Goal must contain exactly one public GitHub repository URL in the form https://github.com/OWNER/REPOSITORY.
```
