"""
Tests for VectorStore.

chromadb.PersistentClient and SentenceTransformerEmbeddingFunction are patched
throughout to avoid filesystem access and model downloads.
"""
import pytest
from unittest.mock import MagicMock, patch, call
from vector_store import VectorStore, SearchResults


CHROMA_RESULTS_ONE_DOC = {
    "documents": [["some lesson text"]],
    "metadatas": [[{"course_title": "Python", "lesson_number": 1, "chunk_index": 0}]],
    "distances": [[0.15]],
}

CHROMA_RESULTS_EMPTY = {
    "documents": [[]],
    "metadatas": [[]],
    "distances": [[]],
}


def _make_store():
    """Return a VectorStore with all ChromaDB side-effects patched out."""
    with patch("chromadb.PersistentClient") as mock_client_cls, \
         patch(
             "chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"
         ) as mock_ef_cls:

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection

        store = VectorStore(chroma_path="./fake_db", embedding_model="fake-model", max_results=5)
        # Expose the mock collection on the store so tests can configure it
        store._mock_collection = mock_collection
        return store


# ---------------------------------------------------------------------------
# SearchResults helpers
# ---------------------------------------------------------------------------

def test_search_results_from_chroma_unpacks_nested_lists():
    sr = SearchResults.from_chroma(CHROMA_RESULTS_ONE_DOC)
    assert sr.documents == ["some lesson text"]
    assert sr.metadata == [{"course_title": "Python", "lesson_number": 1, "chunk_index": 0}]
    assert sr.distances == [0.15]
    assert sr.error is None


def test_search_results_from_chroma_empty_outer_list_returns_empty():
    sr = SearchResults.from_chroma({"documents": [], "metadatas": [], "distances": []})
    assert sr.documents == []
    assert sr.metadata == []
    assert sr.distances == []


def test_search_results_empty_factory():
    sr = SearchResults.empty("some error")
    assert sr.error == "some error"
    assert sr.documents == []
    assert sr.is_empty()


# ---------------------------------------------------------------------------
# _build_filter
# ---------------------------------------------------------------------------

def test_build_filter_no_args_returns_none():
    store = _make_store()
    assert store._build_filter(None, None) is None


def test_build_filter_course_only():
    store = _make_store()
    f = store._build_filter("Python Fundamentals", None)
    assert f == {"course_title": "Python Fundamentals"}


def test_build_filter_lesson_only():
    store = _make_store()
    f = store._build_filter(None, 2)
    assert f == {"lesson_number": 2}


def test_build_filter_course_and_lesson():
    store = _make_store()
    f = store._build_filter("Python Fundamentals", 3)
    assert f == {"$and": [{"course_title": "Python Fundamentals"}, {"lesson_number": 3}]}


# ---------------------------------------------------------------------------
# VectorStore.search — filter construction and where= handling
# ---------------------------------------------------------------------------

def test_search_no_filters_passes_where_none_to_chroma():
    """
    When no course_name or lesson_number is given, filter_dict is None and
    VectorStore passes where=None to ChromaDB. This test documents that
    behavior. If ChromaDB 1.0.15 rejects where=None, this test will fail,
    surfacing the secondary bug.
    """
    store = _make_store()
    store.course_content = MagicMock()
    store.course_content.query.return_value = CHROMA_RESULTS_ONE_DOC

    store.search("what is python")

    store.course_content.query.assert_called_once()
    kwargs = store.course_content.query.call_args[1]
    assert kwargs["where"] is None


def test_search_with_course_name_resolved_builds_course_title_filter():
    store = _make_store()
    store.course_content = MagicMock()
    store.course_content.query.return_value = CHROMA_RESULTS_ONE_DOC

    with patch.object(store, "_resolve_course_name", return_value="Python Fundamentals"):
        store.search("loops", course_name="Python")

    kwargs = store.course_content.query.call_args[1]
    assert kwargs["where"] == {"course_title": "Python Fundamentals"}


def test_search_with_course_and_lesson_builds_and_filter():
    store = _make_store()
    store.course_content = MagicMock()
    store.course_content.query.return_value = CHROMA_RESULTS_ONE_DOC

    with patch.object(store, "_resolve_course_name", return_value="Python Fundamentals"):
        store.search("loops", course_name="Python", lesson_number=3)

    kwargs = store.course_content.query.call_args[1]
    assert kwargs["where"] == {
        "$and": [{"course_title": "Python Fundamentals"}, {"lesson_number": 3}]
    }


def test_search_unresolvable_course_returns_error_search_results():
    store = _make_store()
    with patch.object(store, "_resolve_course_name", return_value=None):
        result = store.search("loops", course_name="NonExistentCourse")

    assert result.error == "No course found matching 'NonExistentCourse'"
    assert result.is_empty()


def test_search_chroma_exception_returns_empty_search_results_not_exception():
    """
    If ChromaDB raises during query, VectorStore wraps it in SearchResults.empty().
    This confirms errors do NOT propagate out of search() as exceptions —
    they flow as error strings through the tool_result path to Claude.
    """
    store = _make_store()
    store.course_content = MagicMock()
    store.course_content.query.side_effect = Exception("chroma internal error")

    result = store.search("anything")

    assert result.error == "Search error: chroma internal error"
    assert result.documents == []
    assert result.is_empty()


def test_search_returns_search_results_on_success():
    store = _make_store()
    store.course_content = MagicMock()
    store.course_content.query.return_value = CHROMA_RESULTS_ONE_DOC

    result = store.search("python loops")

    assert result.documents == ["some lesson text"]
    assert result.metadata == [{"course_title": "Python", "lesson_number": 1, "chunk_index": 0}]
    assert result.error is None
    assert not result.is_empty()


def test_search_uses_max_results_as_default_limit():
    store = _make_store()
    store.course_content = MagicMock()
    store.course_content.query.return_value = CHROMA_RESULTS_EMPTY

    store.search("test")

    kwargs = store.course_content.query.call_args[1]
    assert kwargs["n_results"] == 5  # store.max_results


def test_search_custom_limit_overrides_max_results():
    store = _make_store()
    store.course_content = MagicMock()
    store.course_content.query.return_value = CHROMA_RESULTS_EMPTY

    store.search("test", limit=2)

    kwargs = store.course_content.query.call_args[1]
    assert kwargs["n_results"] == 2
