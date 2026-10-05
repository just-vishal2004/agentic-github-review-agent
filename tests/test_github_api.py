import io
import unittest
from email.message import Message
from urllib.error import HTTPError

from github_api import GitHubAPI, GitHubAPIError


class FakeResponse:
    def __init__(self, body=b"{}"):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return self.body


def http_error(status):
    headers = Message()
    return HTTPError("https://api.github.com/test", status, "failure", headers, io.BytesIO(b"failure"))


class GitHubAPITests(unittest.TestCase):
    def test_retries_503_then_succeeds(self):
        responses = [http_error(503), FakeResponse(b'{"ok": true}')]
        calls = []

        def opener(request, timeout):
            calls.append((request, timeout))
            response = responses.pop(0)
            if isinstance(response, Exception):
                raise response
            return response

        api = GitHubAPI(retries=2, opener=opener, sleeper=lambda delay: None)
        self.assertEqual(api._get("https://api.github.com/test"), b'{"ok": true}')
        self.assertEqual(len(calls), 2)

    def test_500_exhausts_retry_limit(self):
        calls = []

        def opener(request, timeout):
            calls.append(request)
            raise http_error(500)

        api = GitHubAPI(retries=2, opener=opener, sleeper=lambda delay: None)
        with self.assertRaises(GitHubAPIError) as caught:
            api._get("https://api.github.com/test")
        caught.exception.__cause__.close()
        self.assertEqual(len(calls), 3)

    def test_404_does_not_retry(self):
        calls = []

        def opener(request, timeout):
            calls.append(request)
            raise http_error(404)

        api = GitHubAPI(retries=2, opener=opener, sleeper=lambda delay: None)
        with self.assertRaises(GitHubAPIError) as caught:
            api._get("https://api.github.com/test")
        caught.exception.__cause__.close()
        self.assertEqual(len(calls), 1)

    def test_timeout_retries(self):
        responses = [TimeoutError("timed out"), FakeResponse(b"ok")]
        calls = []

        def opener(request, timeout):
            calls.append(request)
            response = responses.pop(0)
            if isinstance(response, Exception):
                raise response
            return response

        api = GitHubAPI(retries=2, opener=opener, sleeper=lambda delay: None)
        self.assertEqual(api._get("https://api.github.com/test"), b"ok")
        self.assertEqual(len(calls), 2)


if __name__ == "__main__":
    unittest.main()
