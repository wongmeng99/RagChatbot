"""Tests for FastAPI endpoint request/response handling."""

import sys
import types
from unittest.mock import MagicMock, patch

# ── Module-level patches (must be installed before app.py is imported) ────────
#
# 1. Replace the 'rag_system' module in sys.modules so that app.py's
#    `from rag_system import RAGSystem` resolves to MagicMock without
#    touching ChromaDB or sentence-transformers.
_fake_rag_module = types.ModuleType("rag_system")
_fake_rag_module.RAGSystem = MagicMock
sys.modules.setdefault("rag_system", _fake_rag_module)

# 2. Patch StaticFiles.__init__ to a no-op so the missing ../frontend
#    directory doesn't raise RuntimeError at import time.
_static_patcher = patch("starlette.staticfiles.StaticFiles.__init__", return_value=None)
_static_patcher.start()

from app import app  # noqa: E402  (imports after patches are in place)

from fastapi.testclient import TestClient  # noqa: E402

# ─────────────────────────────────────────────────────────────────────────────


class TestQueryEndpoint:
    def test_creates_session_when_none_provided(self, client, inject_rag):
        inject_rag.session_manager.create_session.return_value = "session_42"
        inject_rag.query.return_value = ("The answer", [])

        resp = client.post("/api/query", json={"query": "What is Python?"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["answer"] == "The answer"
        assert body["session_id"] == "session_42"
        assert body["sources"] == []
        inject_rag.session_manager.create_session.assert_called_once()

    def test_reuses_provided_session_id(self, client, inject_rag):
        inject_rag.query.return_value = ("Answer", [])

        resp = client.post(
            "/api/query",
            json={"query": "What is Python?", "session_id": "existing-session"},
        )

        assert resp.status_code == 200
        assert resp.json()["session_id"] == "existing-session"
        inject_rag.session_manager.create_session.assert_not_called()

    def test_returns_sources(self, client, inject_rag):
        inject_rag.query.return_value = (
            "Answer with sources",
            [{"text": "Py - Lesson 1", "link": "http://example.com/lesson1"}],
        )

        resp = client.post("/api/query", json={"query": "Tell me about Python"})

        assert resp.status_code == 200
        sources = resp.json()["sources"]
        assert len(sources) == 1
        assert sources[0]["text"] == "Py - Lesson 1"
        assert sources[0]["link"] == "http://example.com/lesson1"

    def test_source_with_null_link(self, client, inject_rag):
        inject_rag.query.return_value = (
            "Answer",
            [{"text": "Course - Lesson 2", "link": None}],
        )

        resp = client.post("/api/query", json={"query": "Tell me about the course"})

        assert resp.status_code == 200
        assert resp.json()["sources"][0]["link"] is None

    def test_rag_exception_returns_500(self, client, inject_rag):
        inject_rag.query.side_effect = RuntimeError("db failed")

        resp = client.post("/api/query", json={"query": "anything"})

        assert resp.status_code == 500
        assert "db failed" in resp.json()["detail"]

    def test_empty_query_string_is_accepted(self, client, inject_rag):
        inject_rag.query.return_value = ("response", [])

        resp = client.post("/api/query", json={"query": ""})

        assert resp.status_code == 200
        inject_rag.query.assert_called_once_with("", "session_1")

    def test_missing_query_field_returns_422(self, client):
        resp = client.post("/api/query", json={})

        assert resp.status_code == 422


class TestCoursesEndpoint:
    def test_returns_course_stats(self, client, inject_rag):
        inject_rag.get_course_analytics.return_value = {
            "total_courses": 3,
            "course_titles": ["Intro to Python", "Advanced ML", "Data Engineering"],
        }

        resp = client.get("/api/courses")

        assert resp.status_code == 200
        body = resp.json()
        assert body["total_courses"] == 3
        assert body["course_titles"] == [
            "Intro to Python",
            "Advanced ML",
            "Data Engineering",
        ]

    def test_returns_empty_catalog(self, client, inject_rag):
        inject_rag.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": [],
        }

        resp = client.get("/api/courses")

        assert resp.status_code == 200
        body = resp.json()
        assert body["total_courses"] == 0
        assert body["course_titles"] == []

    def test_analytics_exception_returns_500(self, client, inject_rag):
        inject_rag.get_course_analytics.side_effect = Exception("analytics error")

        resp = client.get("/api/courses")

        assert resp.status_code == 500
        assert "analytics error" in resp.json()["detail"]


class TestDeleteSessionEndpoint:
    def test_clears_session_and_returns_ok(self, client, inject_rag):
        resp = client.delete("/api/session/my-session-id")

        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
        inject_rag.session_manager.clear_session.assert_called_once_with(
            "my-session-id"
        )

    def test_nonexistent_session_still_returns_ok(self, client, inject_rag):
        # clear_session silently accepts any ID (no-op on unknown sessions)
        resp = client.delete("/api/session/unknown-session")

        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_clear_session_exception_returns_500(self, client, inject_rag):
        # DELETE /api/session has no try/except, so exceptions propagate as 500
        inject_rag.session_manager.clear_session.side_effect = RuntimeError("boom")

        resp = client.delete("/api/session/any-session")

        assert resp.status_code == 500
