import sys
import os
import pytest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(scope="session")
def mock_rag():
    """Pre-configured MagicMock for a RAGSystem instance."""
    m = MagicMock()
    m.session_manager.create_session.return_value = "session_1"
    m.query.return_value = ("Default answer", [])
    m.get_course_analytics.return_value = {"total_courses": 0, "course_titles": []}
    return m


@pytest.fixture
def inject_rag(mock_rag):
    """Inject mock_rag into app.rag_system and reset call state between tests."""
    import app as app_module

    app_module.rag_system = mock_rag
    mock_rag.reset_mock(side_effect=True)
    mock_rag.session_manager.create_session.return_value = "session_1"
    mock_rag.query.return_value = ("Default answer", [])
    mock_rag.get_course_analytics.return_value = {"total_courses": 0, "course_titles": []}
    yield mock_rag


@pytest.fixture
def client(inject_rag):
    """FastAPI TestClient with the RAG system replaced by a mock."""
    from app import app
    from fastapi.testclient import TestClient

    return TestClient(app, raise_server_exceptions=False)
