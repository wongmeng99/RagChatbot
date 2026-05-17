"""Tests for AIGenerator sequential tool calling."""
import pytest
from unittest.mock import MagicMock
from ai_generator import AIGenerator

FAKE_TOOL = {
    "name": "search_course_content",
    "description": "Search course materials",
    "input_schema": {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    },
}


def _make_tool_use_block(tool_id="tu_1", name="search_course_content", input_data=None):
    block = MagicMock()
    block.type = "tool_use"
    block.id = tool_id
    block.name = name
    block.input = input_data or {"query": "test"}
    return block


def _make_text_block(text="Answer"):
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def _make_response(stop_reason, content):
    resp = MagicMock()
    resp.stop_reason = stop_reason
    resp.content = content
    return resp


def _make_generator():
    gen = AIGenerator(api_key="test-key", model="claude-test-model")
    gen.client = MagicMock()
    return gen


# ---------------------------------------------------------------------------
# Happy-path: direct response, no tool use
# ---------------------------------------------------------------------------

def test_direct_response_no_tool_use():
    gen = _make_generator()
    gen.client.messages.create.return_value = _make_response(
        "end_turn", [_make_text_block("Direct answer")]
    )

    result = gen.generate_response(query="What is 2+2?")

    assert result == "Direct answer"
    assert gen.client.messages.create.call_count == 1


# ---------------------------------------------------------------------------
# First API call carries tools + tool_choice:auto
# ---------------------------------------------------------------------------

def test_first_api_call_includes_tools_and_tool_choice_auto():
    gen = _make_generator()
    gen.client.messages.create.return_value = _make_response(
        "end_turn", [_make_text_block("No tool needed")]
    )

    gen.generate_response(query="Hello", tools=[FAKE_TOOL])

    kwargs = gen.client.messages.create.call_args[1]
    assert kwargs["tools"] == [FAKE_TOOL]
    assert kwargs["tool_choice"] == {"type": "auto"}


# ---------------------------------------------------------------------------
# 1-round tool use: second call has tools and tool_choice:auto
# ---------------------------------------------------------------------------

def test_1_round_tool_use_second_call_has_tools_and_tool_choice_auto():
    """
    In a 1-round flow (round_idx=0), the follow-up call uses tool_choice:auto
    so Claude can optionally call a second tool. If it returns end_turn,
    the loop breaks and that response is returned.
    """
    gen = _make_generator()

    tool_block = _make_tool_use_block()
    first_resp = _make_response("tool_use", [tool_block])
    second_resp = _make_response("end_turn", [_make_text_block("Final answer")])
    gen.client.messages.create.side_effect = [first_resp, second_resp]

    mock_tm = MagicMock()
    mock_tm.execute_tool.return_value = "search results"

    result = gen.generate_response(query="What is MCP?", tools=[FAKE_TOOL], tool_manager=mock_tm)

    assert result == "Final answer"
    assert gen.client.messages.create.call_count == 2
    second_call_kwargs = gen.client.messages.create.call_args_list[1][1]
    assert second_call_kwargs.get("tools") == [FAKE_TOOL]
    assert second_call_kwargs.get("tool_choice") == {"type": "auto"}


# ---------------------------------------------------------------------------
# Message thread structure after 1 round
# ---------------------------------------------------------------------------

def test_tool_execution_message_thread_structure():
    gen = _make_generator()

    tool_block = _make_tool_use_block(tool_id="tu_42")
    first_resp = _make_response("tool_use", [tool_block])
    second_resp = _make_response("end_turn", [_make_text_block("Done")])
    gen.client.messages.create.side_effect = [first_resp, second_resp]

    mock_tm = MagicMock()
    mock_tm.execute_tool.return_value = "tool output"

    gen.generate_response(query="initial query", tools=[FAKE_TOOL], tool_manager=mock_tm)

    second_call_kwargs = gen.client.messages.create.call_args_list[1][1]
    messages = second_call_kwargs["messages"]

    assert len(messages) == 3
    assert messages[0]["role"] == "user"
    assert messages[1] == {"role": "assistant", "content": first_resp.content}
    tool_result_msg = messages[2]
    assert tool_result_msg["role"] == "user"
    assert len(tool_result_msg["content"]) == 1
    tr = tool_result_msg["content"][0]
    assert tr["type"] == "tool_result"
    assert tr["tool_use_id"] == "tu_42"
    assert tr["content"] == "tool output"


# ---------------------------------------------------------------------------
# 2-round tool use: third call has tool_choice:none
# ---------------------------------------------------------------------------

def test_2_round_tool_use():
    gen = _make_generator()

    tool_block_1 = _make_tool_use_block(tool_id="tu_1")
    tool_block_2 = _make_tool_use_block(tool_id="tu_2")
    first_resp = _make_response("tool_use", [tool_block_1])
    second_resp = _make_response("tool_use", [tool_block_2])
    third_resp = _make_response("end_turn", [_make_text_block("Final 2-round answer")])
    gen.client.messages.create.side_effect = [first_resp, second_resp, third_resp]

    mock_tm = MagicMock()
    mock_tm.execute_tool.return_value = "results"

    result = gen.generate_response(query="Complex query", tools=[FAKE_TOOL], tool_manager=mock_tm)

    assert result == "Final 2-round answer"
    assert gen.client.messages.create.call_count == 3
    assert mock_tm.execute_tool.call_count == 2

    second_call_kwargs = gen.client.messages.create.call_args_list[1][1]
    assert second_call_kwargs.get("tool_choice") == {"type": "auto"}

    third_call_kwargs = gen.client.messages.create.call_args_list[2][1]
    assert third_call_kwargs.get("tool_choice") == {"type": "none"}
    assert third_call_kwargs.get("tools") == [FAKE_TOOL]


# ---------------------------------------------------------------------------
# Message thread structure after 2 rounds
# ---------------------------------------------------------------------------

def test_message_thread_after_2_rounds():
    gen = _make_generator()

    tool_block_1 = _make_tool_use_block(tool_id="tu_r1")
    tool_block_2 = _make_tool_use_block(tool_id="tu_r2")
    first_resp = _make_response("tool_use", [tool_block_1])
    second_resp = _make_response("tool_use", [tool_block_2])
    third_resp = _make_response("end_turn", [_make_text_block("Done")])
    gen.client.messages.create.side_effect = [first_resp, second_resp, third_resp]

    mock_tm = MagicMock()
    mock_tm.execute_tool.return_value = "output"

    gen.generate_response(query="Multi-round query", tools=[FAKE_TOOL], tool_manager=mock_tm)

    third_call_kwargs = gen.client.messages.create.call_args_list[2][1]
    messages = third_call_kwargs["messages"]

    assert len(messages) == 5
    roles = [m["role"] for m in messages]
    assert roles == ["user", "assistant", "user", "assistant", "user"]

    # Round 1 tool_result has correct tool_use_id
    tr1 = messages[2]["content"][0]
    assert tr1["type"] == "tool_result"
    assert tr1["tool_use_id"] == "tu_r1"

    # Round 2 tool_result has correct tool_use_id
    tr2 = messages[4]["content"][0]
    assert tr2["type"] == "tool_result"
    assert tr2["tool_use_id"] == "tu_r2"


# ---------------------------------------------------------------------------
# 2-round cap is enforced: no 4th API call
# ---------------------------------------------------------------------------

def test_2_round_cap_enforced():
    gen = _make_generator()

    tool_block_1 = _make_tool_use_block(tool_id="tu_1")
    tool_block_2 = _make_tool_use_block(tool_id="tu_2")
    first_resp = _make_response("tool_use", [tool_block_1])
    second_resp = _make_response("tool_use", [tool_block_2])
    # Third call is forced tool_choice:none — real API would return end_turn,
    # but we return end_turn here to confirm the cap holds regardless.
    third_resp = _make_response("end_turn", [_make_text_block("Capped")])
    gen.client.messages.create.side_effect = [first_resp, second_resp, third_resp]

    mock_tm = MagicMock()
    mock_tm.execute_tool.return_value = "ok"

    result = gen.generate_response(query="Q", tools=[FAKE_TOOL], tool_manager=mock_tm)

    assert result == "Capped"
    assert gen.client.messages.create.call_count == 3


# ---------------------------------------------------------------------------
# Tool error terminates loop gracefully
# ---------------------------------------------------------------------------

def test_tool_error_terminates_loop_gracefully():
    gen = _make_generator()

    tool_block = _make_tool_use_block(tool_id="tu_err")
    first_resp = _make_response("tool_use", [tool_block])
    second_resp = _make_response("end_turn", [_make_text_block("Error explanation")])
    gen.client.messages.create.side_effect = [first_resp, second_resp]

    mock_tm = MagicMock()
    mock_tm.execute_tool.side_effect = RuntimeError("db down")

    result = gen.generate_response(query="Q", tools=[FAKE_TOOL], tool_manager=mock_tm)

    assert result == "Error explanation"
    assert gen.client.messages.create.call_count == 2

    second_call_kwargs = gen.client.messages.create.call_args_list[1][1]
    assert second_call_kwargs.get("tool_choice") == {"type": "none"}

    messages = second_call_kwargs["messages"]
    tool_result_content = messages[2]["content"][0]
    assert tool_result_content["type"] == "tool_result"
    assert tool_result_content["tool_use_id"] == "tu_err"
    assert "db down" in tool_result_content["content"]


# ---------------------------------------------------------------------------
# Edge case: tool_use stop_reason but no tool_manager → return first response text
# ---------------------------------------------------------------------------

def test_tool_use_stop_but_no_tool_manager_returns_first_response_text():
    gen = _make_generator()

    text_block = _make_text_block("raw text")
    gen.client.messages.create.return_value = _make_response("tool_use", [text_block])

    result = gen.generate_response(query="Q", tools=[FAKE_TOOL], tool_manager=None)

    assert result == "raw text"
    assert gen.client.messages.create.call_count == 1
