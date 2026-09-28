from unittest.mock import patch

from infrai_client import InfraiClient, InfraiError


class FakeResponse:
    def __init__(self, status_code, envelope, headers=None):
        self.status_code = status_code
        self._envelope = envelope
        self.headers = headers or {}

    def json(self):
        return self._envelope


def test_tokens_client_reads_error_envelope_before_status():
    client = InfraiClient(api_key="test-key")
    response = FakeResponse(
        400,
        {
            "ok": False,
            "data": None,
            "error": {"code": "INVALID_ARGUMENT", "message": "bad input"},
            "metadata": {},
        },
    )

    with patch("httpx.request", return_value=response):
        try:
            client.ai_tokens_count({"model": "auto", "input": "hello"})
        except InfraiError as exc:
            assert exc.code == "INVALID_ARGUMENT"
            assert exc.status_code == 400
        else:
            raise AssertionError("Expected InfraiError")
