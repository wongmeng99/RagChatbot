"""
Tests for CourseSearchTool, CourseOutlineTool, and ToolManager.

VectorStore is replaced by MagicMock throughout — no ChromaDB access.
"""

import pytest
from unittest.mock import MagicMock
from search_tools import CourseSearchTool, CourseOutlineTool, ToolManager
from vector_store import SearchResults


def _mock_store():
    return MagicMock()


# ---------------------------------------------------------------------------
# CourseSearchTool.execute — happy path
# ---------------------------------------------------------------------------


def test_execute_returns_formatted_results_and_populates_sources():
    store = _mock_store()
    store.search.return_value = SearchResults(
        documents=["Lesson content about loops"],
        metadata=[{"course_title": "Py", "lesson_number": 1}],
        distances=[0.1],
    )
    store.get_lesson_link.return_value = "http://link/lesson1"

    tool = CourseSearchTool(store)
    result = tool.execute(query="loops")

    assert "[Py - Lesson 1]" in result
    assert "Lesson content about loops" in result
    assert tool.last_sources == [
        {"text": "Py - Lesson 1", "link": "http://link/lesson1"}
    ]
    store.get_lesson_link.assert_called_once_with("Py", 1)


def test_execute_with_course_and_lesson_filter_passes_args_to_search():
    store = _mock_store()
    store.search.return_value = SearchResults(
        documents=["doc"],
        metadata=[{"course_title": "MCP", "lesson_number": 2}],
        distances=[0.2],
    )
    store.get_lesson_link.return_value = None

    tool = CourseSearchTool(store)
    tool.execute(query="protocol details", course_name="MCP", lesson_number=2)

    store.search.assert_called_once_with(
        query="protocol details", course_name="MCP", lesson_number=2
    )


def test_execute_multiple_results_populates_multiple_sources():
    store = _mock_store()
    store.search.return_value = SearchResults(
        documents=["doc1", "doc2"],
        metadata=[
            {"course_title": "CourseA", "lesson_number": 1},
            {"course_title": "CourseA", "lesson_number": 2},
        ],
        distances=[0.1, 0.2],
    )
    store.get_lesson_link.side_effect = ["http://l1", "http://l2"]

    tool = CourseSearchTool(store)
    tool.execute(query="general query")

    assert len(tool.last_sources) == 2
    assert tool.last_sources[0] == {"text": "CourseA - Lesson 1", "link": "http://l1"}
    assert tool.last_sources[1] == {"text": "CourseA - Lesson 2", "link": "http://l2"}


# ---------------------------------------------------------------------------
# CourseSearchTool.execute — empty results
# ---------------------------------------------------------------------------


def test_execute_no_results_returns_message_and_empty_sources():
    store = _mock_store()
    store.search.return_value = SearchResults(documents=[], metadata=[], distances=[])

    tool = CourseSearchTool(store)
    result = tool.execute(query="nothing here")

    assert result.startswith("No relevant content found")
    assert tool.last_sources == []


def test_execute_no_results_with_course_filter_mentions_course():
    store = _mock_store()
    store.search.return_value = SearchResults(documents=[], metadata=[], distances=[])

    tool = CourseSearchTool(store)
    result = tool.execute(query="loops", course_name="MCP")

    assert "MCP" in result
    assert tool.last_sources == []


# ---------------------------------------------------------------------------
# CourseSearchTool.execute — error from VectorStore
# ---------------------------------------------------------------------------


def test_execute_search_error_returns_error_string_not_exception():
    """
    VectorStore.search() returns SearchResults.empty() on ChromaDB errors.
    CourseSearchTool must return that error as a string, never raise.
    This keeps the error flowing as a tool_result string to Claude.
    """
    store = _mock_store()
    store.search.return_value = SearchResults.empty("Search error: chroma internal")

    tool = CourseSearchTool(store)
    result = tool.execute(query="anything")

    assert result == "Search error: chroma internal"
    assert tool.last_sources == []


# ---------------------------------------------------------------------------
# ToolManager lifecycle
# ---------------------------------------------------------------------------


def test_tool_manager_get_last_sources_returns_from_registered_tool():
    store = _mock_store()
    tool = CourseSearchTool(store)
    tm = ToolManager()
    tm.register_tool(tool)

    tool.last_sources = [{"text": "CourseA - Lesson 1", "link": None}]
    assert tm.get_last_sources() == [{"text": "CourseA - Lesson 1", "link": None}]


def test_tool_manager_reset_sources_clears_all_tools():
    store = _mock_store()
    tool = CourseSearchTool(store)
    tm = ToolManager()
    tm.register_tool(tool)

    tool.last_sources = [{"text": "X", "link": "http://x"}]
    tm.reset_sources()

    assert tool.last_sources == []
    assert tm.get_last_sources() == []


def test_tool_manager_get_last_sources_empty_when_no_search_performed():
    store = _mock_store()
    tool = CourseSearchTool(store)
    tm = ToolManager()
    tm.register_tool(tool)

    assert tm.get_last_sources() == []


def test_tool_manager_execute_unknown_tool_returns_error_string():
    """
    Unknown tool names return an error string — they must not raise, because
    the caller places the return value into a tool_result content block.
    """
    tm = ToolManager()
    result = tm.execute_tool("nonexistent_tool", query="x")
    assert result == "Tool 'nonexistent_tool' not found"


def test_tool_manager_get_tool_definitions_includes_registered_tools():
    store = _mock_store()
    tm = ToolManager()
    tm.register_tool(CourseSearchTool(store))
    tm.register_tool(CourseOutlineTool(store))

    defs = tm.get_tool_definitions()
    names = [d["name"] for d in defs]
    assert "search_course_content" in names
    assert "get_course_outline" in names


# ---------------------------------------------------------------------------
# CourseOutlineTool
# ---------------------------------------------------------------------------


def test_course_outline_tool_happy_path():
    store = _mock_store()
    store.get_course_outline.return_value = {
        "title": "MCP Course",
        "course_link": "http://mcp.example.com",
        "lessons": [
            {"lesson_number": 1, "lesson_title": "Introduction"},
            {"lesson_number": 2, "lesson_title": "Deep Dive"},
        ],
    }

    tool = CourseOutlineTool(store)
    result = tool.execute(course_name="MCP")

    assert "Course: MCP Course" in result
    assert "Link: http://mcp.example.com" in result
    assert "Lesson 1: Introduction" in result
    assert "Lesson 2: Deep Dive" in result


def test_course_outline_tool_not_found_returns_message():
    store = _mock_store()
    store.get_course_outline.return_value = None

    tool = CourseOutlineTool(store)
    result = tool.execute(course_name="unknown course")

    assert result == "No course found matching 'unknown course'."
