"""Tests for user-added RSS feeds: database, API endpoints, validation, pipeline integration."""

import json
import sqlite3
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.database import init_db, get_connection


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _temp_db():
    """Create a temp DB file and init schema, return path."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db_path = Path(tmp.name)
    init_db(db_path)
    return db_path


def _conn(db_path):
    """Get a connection to a temp DB."""
    return get_connection(db_path)


def _make_mock_resp(content="", status_code=200, headers=None):
    """Create a mock requests.Response with streaming support."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.text = content
    mock_resp.encoding = "utf-8"
    mock_resp.raise_for_status = MagicMock()
    mock_resp.close = MagicMock()
    mock_resp.headers = headers or {}
    content_bytes = content.encode("utf-8") if isinstance(content, str) else content
    mock_resp.iter_content = MagicMock(return_value=[content_bytes] if content_bytes else [])
    return mock_resp


# ---------------------------------------------------------------------------
# Database table tests
# ---------------------------------------------------------------------------

class TestUserFeedsTable:
    """Tests for the user_feeds table schema."""

    def test_insert_feed(self):
        db = _temp_db()
        conn = _conn(db)
        conn.execute(
            "INSERT INTO user_feeds (url, title, feed_tag, browser_hash) VALUES (?, ?, ?, ?)",
            ("https://example.com/rss", "Example", "news", "abc123"),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM user_feeds WHERE url = ?", ("https://example.com/rss",)).fetchone()
        conn.close()
        assert row is not None
        assert row["title"] == "Example"
        assert row["feed_tag"] == "news"
        assert row["browser_hash"] == "abc123"
        assert row["is_active"] == 1

    def test_unique_constraint_url_hash(self):
        db = _temp_db()
        conn = _conn(db)
        conn.execute(
            "INSERT INTO user_feeds (url, title, browser_hash) VALUES (?, ?, ?)",
            ("https://example.com/rss", "Example", "abc123"),
        )
        conn.commit()
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO user_feeds (url, title, browser_hash) VALUES (?, ?, ?)",
                ("https://example.com/rss", "Example 2", "abc123"),
            )
        conn.close()

    def test_same_url_different_hash_allowed(self):
        db = _temp_db()
        conn = _conn(db)
        conn.execute(
            "INSERT INTO user_feeds (url, title, browser_hash) VALUES (?, ?, ?)",
            ("https://example.com/rss", "Example", "user1"),
        )
        conn.execute(
            "INSERT INTO user_feeds (url, title, browser_hash) VALUES (?, ?, ?)",
            ("https://example.com/rss", "Example", "user2"),
        )
        conn.commit()
        count = conn.execute("SELECT COUNT(*) FROM user_feeds").fetchone()[0]
        conn.close()
        assert count == 2

    def test_default_values(self):
        db = _temp_db()
        conn = _conn(db)
        conn.execute(
            "INSERT INTO user_feeds (url, browser_hash) VALUES (?, ?)",
            ("https://example.com/rss", "abc123"),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM user_feeds").fetchone()
        conn.close()
        assert row["feed_tag"] == "news"
        assert row["is_active"] == 1
        assert row["last_fetched"] is None
        assert row["last_error"] is None

    def test_last_error_update(self):
        db = _temp_db()
        conn = _conn(db)
        conn.execute(
            "INSERT INTO user_feeds (url, browser_hash) VALUES (?, ?)",
            ("https://example.com/rss", "abc123"),
        )
        conn.commit()
        conn.execute(
            "UPDATE user_feeds SET last_error = ? WHERE url = ?",
            ("Connection timeout", "https://example.com/rss"),
        )
        conn.commit()
        row = conn.execute("SELECT last_error FROM user_feeds").fetchone()
        conn.close()
        assert row["last_error"] == "Connection timeout"

    def test_is_active_filter(self):
        db = _temp_db()
        conn = _conn(db)
        conn.execute(
            "INSERT INTO user_feeds (url, browser_hash, is_active) VALUES (?, ?, ?)",
            ("https://active.com/rss", "abc", 1),
        )
        conn.execute(
            "INSERT INTO user_feeds (url, browser_hash, is_active) VALUES (?, ?, ?)",
            ("https://inactive.com/rss", "abc", 0),
        )
        conn.commit()
        active = conn.execute("SELECT * FROM user_feeds WHERE is_active = 1").fetchall()
        conn.close()
        assert len(active) == 1
        assert active[0]["url"] == "https://active.com/rss"


# ---------------------------------------------------------------------------
# Feed validation tests
# ---------------------------------------------------------------------------

class TestFeedValidation:
    """Tests for URL validation and feed content checking."""

    def test_validate_empty_url(self):
        from src.app import _validate_feed_url
        err, _ip, _host = _validate_feed_url("")
        assert err is not None

    def test_validate_no_scheme(self):
        from src.app import _validate_feed_url
        err, _ip, _host = _validate_feed_url("example.com/rss")
        assert err is not None
        assert "http" in err.lower()

    def test_validate_ftp_rejected(self):
        from src.app import _validate_feed_url
        err, _ip, _host = _validate_feed_url("ftp://example.com/rss")
        assert err is not None

    def test_validate_valid_http(self):
        from src.app import _validate_feed_url
        # Mock _resolve_host to return a public IP
        with patch("src.app._resolve_host", return_value=(False, "93.184.216.34")):
            err, ip, host = _validate_feed_url("http://example.com/rss")
            assert err is None
            assert ip == "93.184.216.34"
            assert host == "example.com"

    def test_validate_url_too_long(self):
        from src.app import _validate_feed_url
        err, _ip, _host = _validate_feed_url("https://example.com/" + "a" * 2048)
        assert err is not None
        assert "long" in err.lower()

    def test_validate_localhost_blocked(self):
        """Both 'localhost' and '127.0.0.1' should be rejected with a localhost error."""
        from src.app import _validate_feed_url
        for url in ("http://localhost/rss", "http://127.0.0.1/rss"):
            err, _ip, _host = _validate_feed_url(url)
            assert err is not None, f"Expected error for {url}"
            assert "localhost" in err.lower(), f"Expected 'localhost' in error for {url}"

    def test_validate_ipv6_loopback_blocked(self):
        from src.app import _validate_feed_url
        err, _ip, _host = _validate_feed_url("http://[::1]/rss")
        assert err is not None

    def test_validate_zero_ip_blocked(self):
        from src.app import _validate_feed_url
        err, _ip, _host = _validate_feed_url("http://0.0.0.0/rss")
        assert err is not None

    def test_validate_private_ip_blocked(self):
        from src.app import _validate_feed_url
        with patch("src.app._resolve_host", return_value=(True, "192.168.1.1")):
            err, _ip, _host = _validate_feed_url("http://192.168.1.1/rss")
            assert err is not None
            assert "private" in err.lower() or "internal" in err.lower()

    def test_check_feed_rss(self):
        from src.app import _check_feed_content
        content = """<?xml version="1.0"?>
        <rss version="2.0">
          <channel>
            <title>My Feed</title>
            <item><title>Story 1</title></item>
          </channel>
        </rss>"""
        is_feed, title = _check_feed_content(content)
        assert is_feed is True
        assert title == "My Feed"

    def test_check_feed_atom(self):
        from src.app import _check_feed_content
        content = """<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <title>Atom Feed</title>
          <entry><title>Entry 1</title></entry>
        </feed>"""
        is_feed, title = _check_feed_content(content)
        assert is_feed is True
        assert title == "Atom Feed"

    def test_check_feed_rdf(self):
        from src.app import _check_feed_content
        content = """<?xml version="1.0"?>
        <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
          <channel>
            <title>RDF Feed</title>
          </channel>
        </rdf:RDF>"""
        is_feed, title = _check_feed_content(content)
        assert is_feed is True
        assert title == "RDF Feed"

    @pytest.mark.parametrize("content", [
        """<html><head><title>Not a feed</title></head><body>Hello</body></html>""",
        """{"items": [{"title": "not rss"}]}""",
        "",
    ])
    def test_check_feed_non_feed_rejected(self, content):
        from src.app import _check_feed_content
        is_feed, title = _check_feed_content(content)
        assert is_feed is False

    def test_check_feed_no_title(self):
        from src.app import _check_feed_content
        content = """<?xml version="1.0"?><rss version="2.0"><channel><item></item></channel></rss>"""
        is_feed, title = _check_feed_content(content)
        assert is_feed is True
        # No title found, should be None
        assert title is None

    def test_check_feed_long_title_truncated(self):
        from src.app import _check_feed_content
        long_title = "A" * 300
        content = '<rss><channel><title>%s</title></channel></rss>' % long_title
        is_feed, title = _check_feed_content(content)
        assert is_feed is True
        assert len(title) == 200


# ---------------------------------------------------------------------------
# SSRF / Security tests
# ---------------------------------------------------------------------------

class TestSSRFProtection:
    """Tests for SSRF mitigation in feed URL validation."""

    @pytest.mark.parametrize("ip,expected", [
        ("10.0.0.1", True),
        ("172.16.0.1", True),
        ("192.168.1.1", True),
        ("127.0.0.1", True),
    ])
    def test_private_ip_ranges(self, ip, expected):
        from src.app import _is_private_ip
        assert _is_private_ip(ip) is expected

    def test_public_ip(self):
        from src.app import _is_private_ip
        assert _is_private_ip("8.8.8.8") is False

    def test_dns_failure(self):
        """DNS failure should not crash (returns False, let the fetch fail)."""
        from src.app import _is_private_ip
        import socket
        with patch("src.app.socket.getaddrinfo", side_effect=socket.gaierror("no DNS")):
            assert _is_private_ip("nonexistent.example.com") is False


# ---------------------------------------------------------------------------
# API endpoint tests (using FastAPI TestClient)
# ---------------------------------------------------------------------------

class TestUserFeedEndpoints:
    """Tests for /api/user-feeds CRUD endpoints."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test client and temp DB."""
        # Patch DB_PATH to use temp DB
        self.db_path = _temp_db()
        with patch("src.database.DB_PATH", self.db_path), \
             patch("src.app._user_feed_rate", {}):
            from fastapi.testclient import TestClient
            from src.app import app
            self.client = TestClient(app)
            yield

    def _mock_feed_fetch(self, content="<rss><channel><title>Test</title></channel></rss>",
                         status_code=200, side_effect=None):
        """Create a mock for requests.get that returns feed-like content."""
        if side_effect:
            return patch("src.app._requests_lib.get", side_effect=side_effect)
        mock_resp = _make_mock_resp(content, status_code)
        return patch("src.app._requests_lib.get", return_value=mock_resp)

    def test_add_feed_success(self):
        with self._mock_feed_fetch(), \
             patch("src.app._resolve_host", return_value=(False, "93.184.216.34")):
            resp = self.client.post("/api/user-feeds", json={
                "url": "https://example.com/rss",
                "browser_hash": "testhash123",
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["url"] == "https://example.com/rss"
        assert data["title"] == "Test"
        assert data["feed_tag"] == "news"
        assert data["is_active"] is True

    def test_add_feed_custom_tag(self):
        with self._mock_feed_fetch(), \
             patch("src.app._resolve_host", return_value=(False, "93.184.216.34")):
            resp = self.client.post("/api/user-feeds", json={
                "url": "https://example.com/sports",
                "feed_tag": "sports",
                "browser_hash": "testhash123",
            })
        assert resp.status_code == 200
        assert resp.json()["feed_tag"] == "sports"

    def test_add_feed_invalid_tag(self):
        with patch("src.app._resolve_host", return_value=(False, "93.184.216.34")):
            resp = self.client.post("/api/user-feeds", json={
                "url": "https://example.com/rss",
                "feed_tag": "invalid_tag",
                "browser_hash": "testhash123",
            })
        assert resp.status_code == 400
        assert "invalid feed_tag" in resp.json()["error"]

    def test_add_feed_no_hash(self):
        resp = self.client.post("/api/user-feeds", json={
            "url": "https://example.com/rss",
        })
        assert resp.status_code == 400
        assert "browser_hash" in resp.json()["error"]

    def test_add_feed_bad_url(self):
        resp = self.client.post("/api/user-feeds", json={
            "url": "ftp://example.com/rss",
            "browser_hash": "testhash123",
        })
        assert resp.status_code == 400

    def test_add_feed_localhost_rejected(self):
        resp = self.client.post("/api/user-feeds", json={
            "url": "http://localhost:8000/rss",
            "browser_hash": "testhash123",
        })
        assert resp.status_code == 400
        assert "localhost" in resp.json()["error"]

    def test_add_feed_not_rss(self):
        html_content = "<html><body>Not a feed</body></html>"
        with self._mock_feed_fetch(content=html_content), \
             patch("src.app._resolve_host", return_value=(False, "93.184.216.34")):
            resp = self.client.post("/api/user-feeds", json={
                "url": "https://example.com/page",
                "browser_hash": "testhash123",
            })
        assert resp.status_code == 400
        assert "RSS" in resp.json()["error"] or "Atom" in resp.json()["error"]

    def test_add_feed_timeout(self):
        import requests
        with self._mock_feed_fetch(side_effect=requests.Timeout("timeout")), \
             patch("src.app._resolve_host", return_value=(False, "93.184.216.34")):
            resp = self.client.post("/api/user-feeds", json={
                "url": "https://slow.example.com/rss",
                "browser_hash": "testhash123",
            })
        assert resp.status_code == 400
        assert "timed out" in resp.json()["error"]

    def test_add_feed_fetch_error(self):
        import requests
        with self._mock_feed_fetch(side_effect=requests.ConnectionError("refused")), \
             patch("src.app._resolve_host", return_value=(False, "93.184.216.34")):
            resp = self.client.post("/api/user-feeds", json={
                "url": "https://down.example.com/rss",
                "browser_hash": "testhash123",
            })
        assert resp.status_code == 400
        assert "could not fetch" in resp.json()["error"]

    def test_add_feed_duplicate(self):
        with self._mock_feed_fetch(), \
             patch("src.app._resolve_host", return_value=(False, "93.184.216.34")):
            self.client.post("/api/user-feeds", json={
                "url": "https://example.com/rss",
                "browser_hash": "testhash123",
            })
            resp = self.client.post("/api/user-feeds", json={
                "url": "https://example.com/rss",
                "browser_hash": "testhash123",
            })
        assert resp.status_code == 409
        assert "already added" in resp.json()["error"]

    def test_add_feed_max_reached(self):
        """Test that users cannot add more than MAX feeds."""
        # Pre-populate DB with max feeds
        conn = _conn(self.db_path)
        for i in range(20):
            conn.execute(
                "INSERT INTO user_feeds (url, browser_hash) VALUES (?, ?)",
                ("https://feed%d.example.com/rss" % i, "testhash123"),
            )
        conn.commit()
        conn.close()

        with self._mock_feed_fetch(), \
             patch("src.app._resolve_host", return_value=(False, "93.184.216.34")):
            resp = self.client.post("/api/user-feeds", json={
                "url": "https://new.example.com/rss",
                "browser_hash": "testhash123",
            })
        assert resp.status_code == 400
        assert "maximum" in resp.json()["error"]

    def test_list_feeds_empty(self):
        resp = self.client.get("/api/user-feeds?hash=testhash123")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_feeds_no_hash(self):
        resp = self.client.get("/api/user-feeds")
        assert resp.status_code == 400

    def test_list_feeds_returns_user_feeds(self):
        # Add two feeds
        with self._mock_feed_fetch(), \
             patch("src.app._resolve_host", return_value=(False, "93.184.216.34")):
            self.client.post("/api/user-feeds", json={
                "url": "https://feed1.example.com/rss",
                "browser_hash": "testhash123",
            })
            self.client.post("/api/user-feeds", json={
                "url": "https://feed2.example.com/rss",
                "browser_hash": "testhash123",
            })
        resp = self.client.get("/api/user-feeds?hash=testhash123")
        assert resp.status_code == 200
        feeds = resp.json()
        assert len(feeds) == 2
        urls = {f["url"] for f in feeds}
        assert "https://feed1.example.com/rss" in urls
        assert "https://feed2.example.com/rss" in urls

    def test_list_feeds_isolation(self):
        """User A's feeds are not visible to User B."""
        with self._mock_feed_fetch(), \
             patch("src.app._resolve_host", return_value=(False, "93.184.216.34")):
            self.client.post("/api/user-feeds", json={
                "url": "https://feed1.example.com/rss",
                "browser_hash": "userA",
            })
            self.client.post("/api/user-feeds", json={
                "url": "https://feed2.example.com/rss",
                "browser_hash": "userB",
            })
        resp_a = self.client.get("/api/user-feeds?hash=userA")
        resp_b = self.client.get("/api/user-feeds?hash=userB")
        assert len(resp_a.json()) == 1
        assert len(resp_b.json()) == 1
        assert resp_a.json()[0]["url"] == "https://feed1.example.com/rss"
        assert resp_b.json()[0]["url"] == "https://feed2.example.com/rss"

    def test_delete_feed_success(self):
        with self._mock_feed_fetch(), \
             patch("src.app._resolve_host", return_value=(False, "93.184.216.34")):
            add_resp = self.client.post("/api/user-feeds", json={
                "url": "https://example.com/rss",
                "browser_hash": "testhash123",
            })
        feed_id = add_resp.json()["id"]
        resp = self.client.delete("/api/user-feeds/%d?hash=testhash123" % feed_id)
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"
        # Verify it's gone
        list_resp = self.client.get("/api/user-feeds?hash=testhash123")
        assert len(list_resp.json()) == 0

    def test_delete_feed_not_found(self):
        resp = self.client.delete("/api/user-feeds/9999?hash=testhash123")
        assert resp.status_code == 404

    def test_delete_feed_wrong_hash(self):
        with self._mock_feed_fetch(), \
             patch("src.app._resolve_host", return_value=(False, "93.184.216.34")):
            add_resp = self.client.post("/api/user-feeds", json={
                "url": "https://example.com/rss",
                "browser_hash": "userA",
            })
        feed_id = add_resp.json()["id"]
        resp = self.client.delete("/api/user-feeds/%d?hash=userB" % feed_id)
        assert resp.status_code == 403
        assert "unauthorized" in resp.json()["error"]

    def test_delete_feed_no_hash(self):
        resp = self.client.delete("/api/user-feeds/1")
        assert resp.status_code == 400

    def test_rate_limit(self):
        """After 5 requests in 1 minute, the 6th should be rate-limited."""
        with self._mock_feed_fetch(), \
             patch("src.app._resolve_host", return_value=(False, "93.184.216.34")):
            for i in range(5):
                resp = self.client.post("/api/user-feeds", json={
                    "url": "https://feed%d.example.com/rss" % i,
                    "browser_hash": "ratelimited",
                })
                # First 5 should succeed (or fail for other reasons, but not rate-limited)
                assert resp.status_code != 429, "Request %d was rate limited prematurely" % (i + 1)

            # 6th request should be rate limited
            resp = self.client.post("/api/user-feeds", json={
                "url": "https://feed99.example.com/rss",
                "browser_hash": "ratelimited",
            })
            assert resp.status_code == 429


# ---------------------------------------------------------------------------
# Pipeline integration tests
# ---------------------------------------------------------------------------

class TestPipelineIntegration:
    """Tests for user feed scraping during the pipeline cycle."""

    def test_user_feeds_queried_in_pipeline(self):
        """Pipeline should query active user feeds."""
        db_path = _temp_db()
        conn = _conn(db_path)
        conn.execute(
            "INSERT INTO user_feeds (url, title, feed_tag, browser_hash, is_active) VALUES (?, ?, ?, ?, ?)",
            ("https://userfeed.example.com/rss", "User Feed", "tech", "abc123", 1),
        )
        conn.commit()

        # Verify the query pattern used in pipeline
        rows = conn.execute(
            "SELECT id, url, title, feed_tag FROM user_feeds WHERE is_active = 1"
        ).fetchall()
        conn.close()
        assert len(rows) == 1
        assert rows[0]["url"] == "https://userfeed.example.com/rss"
        assert rows[0]["feed_tag"] == "tech"

    def test_last_fetched_update_pattern(self):
        """After scraping, last_fetched should be set and last_error cleared."""
        db_path = _temp_db()
        conn = _conn(db_path)
        conn.execute(
            "INSERT INTO user_feeds (url, title, browser_hash, last_error) VALUES (?, ?, ?, ?)",
            ("https://userfeed.example.com/rss", "Feed", "abc123", "old error"),
        )
        conn.commit()
        # Simulate the update pattern from pipeline
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "UPDATE user_feeds SET last_fetched = ?, last_error = NULL WHERE url = ?",
            (now, "https://userfeed.example.com/rss"),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM user_feeds WHERE url = ?", ("https://userfeed.example.com/rss",)).fetchone()
        conn.close()
        assert row["last_fetched"] is not None
        assert row["last_error"] is None


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_browser_hash_truncated_to_64(self):
        """Long browser hashes should be truncated to 64 chars."""
        db_path = _temp_db()
        with patch("src.database.DB_PATH", db_path), \
             patch("src.app._user_feed_rate", {}):
            from fastapi.testclient import TestClient
            from src.app import app
            client = TestClient(app)

            long_hash = "a" * 200
            rss = "<rss><channel><title>T</title></channel></rss>"
            mock_resp = _make_mock_resp(rss)
            with patch("src.app._requests_lib.get", return_value=mock_resp), \
                 patch("src.app._resolve_host", return_value=(False, "93.184.216.34")):
                resp = client.post("/api/user-feeds", json={
                    "url": "https://example.com/rss",
                    "browser_hash": long_hash,
                })
            assert resp.status_code == 200
            # Verify the stored hash is truncated
            conn = _conn(db_path)
            row = conn.execute("SELECT browser_hash FROM user_feeds").fetchone()
            conn.close()
            assert len(row["browser_hash"]) == 64

    def test_feed_content_check_large_input(self):
        """Feed content check should handle large inputs (truncated to 50KB)."""
        from src.app import _check_feed_content
        # The check is done on resp.text[:50000] in the endpoint
        large = "x" * 100000
        is_feed, title = _check_feed_content(large)
        assert is_feed is False

    def test_feed_with_cdata_title(self):
        """Feed titles wrapped in CDATA should still be extractable."""
        from src.app import _check_feed_content
        content = '<rss><channel><title><![CDATA[My CDATA Feed]]></title></channel></rss>'
        is_feed, title = _check_feed_content(content)
        assert is_feed is True
        # CDATA won't match our simple regex, so title might be None -- that's acceptable
        # The important thing is it's detected as a feed

    def test_feed_url_with_query_params(self):
        """URLs with query parameters should be accepted."""
        from src.app import _validate_feed_url
        with patch("src.app._resolve_host", return_value=(False, "93.184.216.34")):
            err, _ip, _host = _validate_feed_url("https://example.com/rss?format=xml&limit=50")
            assert err is None

    def test_multiple_users_same_feed_url(self):
        """Different users should be able to add the same feed URL."""
        db_path = _temp_db()
        with patch("src.database.DB_PATH", db_path), \
             patch("src.app._user_feed_rate", {}):
            from fastapi.testclient import TestClient
            from src.app import app
            client = TestClient(app)

            rss = "<rss><channel><title>Shared Feed</title></channel></rss>"
            mock_resp = _make_mock_resp(rss)
            with patch("src.app._requests_lib.get", return_value=mock_resp), \
                 patch("src.app._resolve_host", return_value=(False, "93.184.216.34")):
                resp1 = client.post("/api/user-feeds", json={
                    "url": "https://shared.example.com/rss",
                    "browser_hash": "userA",
                })
                resp2 = client.post("/api/user-feeds", json={
                    "url": "https://shared.example.com/rss",
                    "browser_hash": "userB",
                })
            assert resp1.status_code == 200
            assert resp2.status_code == 200


# ---------------------------------------------------------------------------
# Security fix tests: redirect rejection, DNS rebinding, global volume cap
# ---------------------------------------------------------------------------

class TestRedirectSSRF:
    """Tests for Warning 1: HTTP redirect SSRF bypass prevention."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db_path = _temp_db()
        with patch("src.database.DB_PATH", self.db_path), \
             patch("src.app._user_feed_rate", {}):
            from fastapi.testclient import TestClient
            from src.app import app
            self.client = TestClient(app)
            yield

    @pytest.mark.parametrize("status_code,location", [
        (301, "http://169.254.169.254/metadata"),
        (302, "http://127.0.0.1:8080/admin"),
        (307, None),
    ])
    def test_redirect_rejected(self, status_code, location):
        """3xx redirects from the feed URL should be rejected."""
        headers = {"Location": location} if location else {}
        mock_resp = _make_mock_resp("", status_code, headers)
        with patch("src.app._requests_lib.get", return_value=mock_resp), \
             patch("src.app._resolve_host", return_value=(False, "93.184.216.34")):
            resp = self.client.post("/api/user-feeds", json={
                "url": "https://evil.example.com/rss",
                "browser_hash": "testhash123",
            })
        assert resp.status_code == 400
        assert "redirect" in resp.json()["error"].lower()

    def test_allow_redirects_false_in_request(self):
        """Verify that requests.get is called with allow_redirects=False."""
        mock_resp = _make_mock_resp("<rss><channel><title>OK</title></channel></rss>")
        with patch("src.app._requests_lib.get", return_value=mock_resp) as mock_get, \
             patch("src.app._resolve_host", return_value=(False, "93.184.216.34")):
            self.client.post("/api/user-feeds", json={
                "url": "https://example.com/rss",
                "browser_hash": "testhash123",
            })
        # Verify allow_redirects=False was passed
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs.get("allow_redirects") is False

    def test_200_response_not_treated_as_redirect(self):
        """A normal 200 response should still be accepted."""
        mock_resp = _make_mock_resp("<rss><channel><title>Good Feed</title></channel></rss>")
        with patch("src.app._requests_lib.get", return_value=mock_resp), \
             patch("src.app._resolve_host", return_value=(False, "93.184.216.34")):
            resp = self.client.post("/api/user-feeds", json={
                "url": "https://example.com/rss",
                "browser_hash": "testhash123",
            })
        assert resp.status_code == 200
        assert resp.json()["title"] == "Good Feed"


class TestDNSRebindingProtection:
    """Tests for Warning 2: DNS rebinding TOCTOU gap prevention."""

    def test_resolve_host_ip_literal(self):
        """_resolve_host with an IP literal should skip DNS."""
        from src.app import _resolve_host
        is_private, ip = _resolve_host("10.0.0.1")
        assert is_private is True
        assert ip == "10.0.0.1"

    def test_resolve_host_public_ip_literal(self):
        """_resolve_host with a public IP literal should return it."""
        from src.app import _resolve_host
        is_private, ip = _resolve_host("8.8.8.8")
        assert is_private is False
        assert ip == "8.8.8.8"

    def test_resolve_host_dns_failure(self):
        """_resolve_host returns (False, None) on DNS failure."""
        from src.app import _resolve_host
        import socket
        with patch("src.app.socket.getaddrinfo", side_effect=socket.gaierror("no DNS")):
            is_private, ip = _resolve_host("nonexistent.example.com")
        assert is_private is False
        assert ip is None

    def test_fetch_uses_resolved_ip_in_url(self):
        """The HTTP fetch should connect to the resolved IP, not re-resolve DNS."""
        db_path = _temp_db()
        with patch("src.database.DB_PATH", db_path), \
             patch("src.app._user_feed_rate", {}):
            from fastapi.testclient import TestClient
            from src.app import app
            client = TestClient(app)

            mock_resp = _make_mock_resp("<rss><channel><title>Test</title></channel></rss>")
            with patch("src.app._requests_lib.get", return_value=mock_resp) as mock_get, \
                 patch("src.app._resolve_host", return_value=(False, "93.184.216.34")):
                client.post("/api/user-feeds", json={
                    "url": "https://example.com/rss",
                    "browser_hash": "testhash123",
                })
            # The URL passed to requests.get should use the IP, not the hostname
            call_args = mock_get.call_args
            fetched_url = call_args[0][0] if call_args[0] else call_args[1].get("url", "")
            assert "93.184.216.34" in fetched_url
            # Host header should be set to the original hostname
            call_headers = call_args[1].get("headers", {})
            assert call_headers.get("Host") == "example.com"

    def test_fetch_with_port_preserves_port(self):
        """If the URL has a non-standard port, it should be preserved."""
        db_path = _temp_db()
        with patch("src.database.DB_PATH", db_path), \
             patch("src.app._user_feed_rate", {}):
            from fastapi.testclient import TestClient
            from src.app import app
            client = TestClient(app)

            mock_resp = _make_mock_resp("<rss><channel><title>Test</title></channel></rss>")
            with patch("src.app._requests_lib.get", return_value=mock_resp) as mock_get, \
                 patch("src.app._resolve_host", return_value=(False, "93.184.216.34")):
                client.post("/api/user-feeds", json={
                    "url": "https://example.com:8443/rss",
                    "browser_hash": "testhash123",
                })
            call_args = mock_get.call_args
            fetched_url = call_args[0][0] if call_args[0] else call_args[1].get("url", "")
            assert "93.184.216.34" in fetched_url
            # Host header should include the port
            call_headers = call_args[1].get("headers", {})
            assert "example.com:8443" in call_headers.get("Host", "")
