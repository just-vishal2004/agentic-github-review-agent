import base64
import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


class GitHubAPIError(Exception):
    pass


class GitHubAPI:
    def __init__(self, timeout=10, retries=2, opener=urlopen, sleeper=time.sleep):
        self.timeout = timeout
        self.retries = retries
        self.opener = opener
        self.sleeper = sleeper

    def _get(self, url):
        request = Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "simple-repo-reviewer"})
        for attempt in range(self.retries + 1):
            try:
                with self.opener(request, timeout=self.timeout) as response:
                    return response.read()
            except HTTPError as exc:
                transient = exc.code == 429 or 500 <= exc.code <= 599
                if not transient or attempt >= self.retries:
                    status = exc.code
                    exc.close()
                    raise GitHubAPIError(f"GitHub API returned HTTP {status} for {url}") from exc
                retry_after = exc.headers.get("Retry-After", "")
                exc.close()
                try:
                    delay = min(float(retry_after), 2.0) if retry_after else 0.5 * (attempt + 1)
                except ValueError:
                    delay = 0.5 * (attempt + 1)
                self.sleeper(delay)
            except (URLError, TimeoutError) as exc:
                if attempt >= self.retries:
                    raise GitHubAPIError(f"Could not reach GitHub: {exc}") from exc
                self.sleeper(0.5 * (attempt + 1))
        raise GitHubAPIError(f"GitHub request failed for {url}")

    def _json(self, url):
        try:
            return json.loads(self._get(url))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise GitHubAPIError("GitHub returned invalid JSON") from exc

    def get_repository(self, owner, repo):
        return self._json(f"https://api.github.com/repos/{quote(owner)}/{quote(repo)}")

    def get_tree(self, owner, repo, branch):
        encoded_branch = quote(branch, safe="")
        result = self._json(f"https://api.github.com/repos/{quote(owner)}/{quote(repo)}/git/trees/{encoded_branch}?recursive=1")
        if result.get("truncated"):
            raise GitHubAPIError("Repository tree is too large for this bounded review.")
        return result.get("tree", [])

    def get_file(self, owner, repo, path):
        encoded_path = "/".join(quote(part, safe="") for part in path.split("/"))
        result = self._json(f"https://api.github.com/repos/{quote(owner)}/{quote(repo)}/contents/{encoded_path}")
        if result.get("encoding") != "base64":
            raise GitHubAPIError(f"Unsupported content encoding for {path}")
        try:
            data = base64.b64decode(result["content"])
            if b"\x00" in data:
                raise GitHubAPIError(f"Binary content skipped: {path}")
            return data.decode("utf-8")
        except (KeyError, ValueError, UnicodeDecodeError) as exc:
            raise GitHubAPIError(f"Could not decode {path}") from exc
