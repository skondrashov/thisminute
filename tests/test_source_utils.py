"""Tests for source_utils shared helpers."""

import logging
from unittest.mock import patch, MagicMock

from src.source_utils import fetch_json


# --- fetch_json log_url tests ---

def test_fetch_json_logs_real_url_by_default():
    """Without log_url, the real URL is logged on error."""
    with patch("src.source_utils.urllib.request.urlopen",
               side_effect=Exception("connection refused")):
        with patch("src.source_utils.logger") as mock_logger:
            result = fetch_json("https://example.com/secret?key=abc123")
    assert result == []
    log_call = mock_logger.error.call_args
    assert "https://example.com/secret?key=abc123" in str(log_call)


def test_fetch_json_logs_safe_url_when_provided():
    """With log_url, the safe URL is logged instead of the real one."""
    with patch("src.source_utils.urllib.request.urlopen",
               side_effect=Exception("connection refused")):
        with patch("src.source_utils.logger") as mock_logger:
            result = fetch_json(
                "https://example.com/api?key=SECRET123&email=me@test.com",
                log_url="https://example.com/api?key=REDACTED")
    assert result == []
    log_call = mock_logger.error.call_args
    log_msg = str(log_call)
    assert "REDACTED" in log_msg
    assert "SECRET123" not in log_msg
    assert "me@test.com" not in log_msg


def test_fetch_json_log_url_does_not_affect_request():
    """log_url only affects logging, not the actual HTTP request."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = b'{"data": [1, 2, 3]}'
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("src.source_utils.urllib.request.urlopen",
               return_value=mock_resp) as mock_urlopen:
        result = fetch_json(
            "https://example.com/api?key=REAL_KEY",
            key="data",
            log_url="https://example.com/api?key=REDACTED")

    assert result == [1, 2, 3]
    # Verify the real URL was used for the actual request
    req_obj = mock_urlopen.call_args[0][0]
    assert "REAL_KEY" in req_obj.full_url


def test_fetch_json_log_url_none_key():
    """log_url works correctly when key=None."""
    with patch("src.source_utils.urllib.request.urlopen",
               side_effect=Exception("timeout")):
        with patch("src.source_utils.logger") as mock_logger:
            result = fetch_json(
                "https://example.com/api?key=SECRET",
                key=None,
                log_url="https://example.com/api?key=REDACTED")
    assert result == {}
    log_msg = str(mock_logger.error.call_args)
    assert "SECRET" not in log_msg
    assert "REDACTED" in log_msg
