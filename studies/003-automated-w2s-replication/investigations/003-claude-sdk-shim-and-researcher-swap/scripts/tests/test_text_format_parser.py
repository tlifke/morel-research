import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claude_agent_sdk_shim.parser import extract_tool_calls, synthesize_tool_use_blocks
from claude_agent_sdk_shim.types import ToolUseBlock


def _assert(cond, msg):
    if not cond:
        raise AssertionError(msg)


def test_function_call_tag():
    text = (
        "I'll evaluate.\n"
        '<function_call>{"name": "evaluate_predictions", '
        '"arguments": {"dataset": "math", "predictions": [0,1,0]}}</function_call>\n'
        "done."
    )
    residual, calls = extract_tool_calls(text)
    _assert(len(calls) == 1, f"expected 1 call, got {len(calls)}")
    _assert(calls[0]["name"] == "evaluate_predictions", calls[0])
    _assert(calls[0]["arguments"]["dataset"] == "math", calls[0])
    _assert("function_call" not in residual, residual)


def test_tool_call_tag_qwen_style():
    text = '<tool_call>{"name": "get_leaderboard", "arguments": {}}</tool_call>'
    residual, calls = extract_tool_calls(text)
    _assert(len(calls) == 1, calls)
    _assert(calls[0]["name"] == "get_leaderboard", calls[0])
    _assert(residual == "", repr(residual))


def test_fenced_json():
    text = (
        "Going to call this:\n"
        "```json\n"
        '{"name": "Bash", "arguments": {"command": "ls /tmp"}}\n'
        "```\n"
    )
    residual, calls = extract_tool_calls(text)
    _assert(len(calls) == 1, calls)
    _assert(calls[0]["name"] == "Bash", calls[0])
    _assert(calls[0]["arguments"]["command"] == "ls /tmp", calls[0])


def test_bare_json_with_known_tools():
    text = (
        "Let me try this.\n"
        '{"name": "Read", "arguments": {"file_path": "/tmp/x.txt"}}\n'
        "Now I'll read it."
    )
    residual, calls = extract_tool_calls(text, known_tool_names={"Read", "Write"})
    _assert(len(calls) == 1, calls)
    _assert(calls[0]["name"] == "Read", calls[0])


def test_bare_json_filtered_when_unknown():
    text = '{"name": "MysteryTool", "arguments": {"foo": "bar"}}'
    _, calls = extract_tool_calls(text, known_tool_names={"Read"})
    _assert(len(calls) == 0, calls)


def test_parameters_key_alias():
    text = '<function_call>{"name": "Write", "parameters": {"file_path": "/tmp/a", "content": "hi"}}</function_call>'
    _, calls = extract_tool_calls(text)
    _assert(len(calls) == 1, calls)
    _assert(calls[0]["arguments"]["file_path"] == "/tmp/a", calls[0])


def test_arguments_as_stringified_json():
    text = '<function_call>{"name": "Bash", "arguments": "{\\"command\\": \\"echo hi\\"}"}</function_call>'
    _, calls = extract_tool_calls(text)
    _assert(len(calls) == 1, calls)
    _assert(calls[0]["arguments"]["command"] == "echo hi", calls[0])


def test_multiple_calls_in_one_text():
    text = (
        '<function_call>{"name": "Read", "arguments": {"file_path": "/a"}}</function_call>\n'
        'Then:\n'
        '<function_call>{"name": "Write", "arguments": {"file_path": "/b", "content": "x"}}</function_call>'
    )
    residual, calls = extract_tool_calls(text)
    _assert(len(calls) == 2, calls)
    _assert([c["name"] for c in calls] == ["Read", "Write"], calls)


def test_synthesize_returns_tool_use_blocks():
    text = '<function_call>{"name": "Bash", "arguments": {"command": "true"}}</function_call>'
    residual, blocks = synthesize_tool_use_blocks(text)
    _assert(len(blocks) == 1, blocks)
    _assert(isinstance(blocks[0], ToolUseBlock), blocks[0])
    _assert(blocks[0].id.startswith("toolu_synth_"), blocks[0].id)
    _assert(blocks[0].name == "Bash", blocks[0])


def test_no_match_returns_text_unchanged():
    text = "Just plain prose with no calls."
    residual, calls = extract_tool_calls(text)
    _assert(calls == [], calls)
    _assert(residual == text, repr(residual))


def test_ignores_non_tool_json():
    text = '{"foo": "bar", "baz": 1}'
    _, calls = extract_tool_calls(text, known_tool_names={"Read"})
    _assert(calls == [], calls)


def test_function_key_alias():
    text = '<function_call>{"function": "evaluate_predictions", "arguments": {"dataset": "math"}}</function_call>'
    _, calls = extract_tool_calls(text)
    _assert(len(calls) == 1, calls)
    _assert(calls[0]["name"] == "evaluate_predictions", calls[0])
    _assert(calls[0]["arguments"]["dataset"] == "math", calls[0])


def test_real_qwen_failure_payload():
    text = (
        "I will evaluate now.\n"
        "{\n"
        '  "name": "evaluate_predictions",\n'
        '  "arguments": {\n'
        '    "dataset": "math",\n'
        '    "predictions": [0,1,0,1,0],\n'
        '    "weak_model": "Qwen/Qwen1.5-0.5B-Chat",\n'
        '    "strong_model": "Qwen/Qwen3-4B-Base"\n'
        "  }\n"
        "}"
    )
    _, calls = extract_tool_calls(text, known_tool_names={"evaluate_predictions"})
    _assert(len(calls) == 1, calls)
    _assert(calls[0]["name"] == "evaluate_predictions", calls[0])
    _assert(calls[0]["arguments"]["predictions"] == [0, 1, 0, 1, 0], calls[0])


def main():
    tests = [
        test_function_call_tag,
        test_tool_call_tag_qwen_style,
        test_fenced_json,
        test_bare_json_with_known_tools,
        test_bare_json_filtered_when_unknown,
        test_parameters_key_alias,
        test_arguments_as_stringified_json,
        test_function_key_alias,
        test_multiple_calls_in_one_text,
        test_synthesize_returns_tool_use_blocks,
        test_no_match_returns_text_unchanged,
        test_ignores_non_tool_json,
        test_real_qwen_failure_payload,
    ]
    failed = 0
    for t in tests:
        try:
            t()
        except Exception as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
    if failed:
        print(f"{failed}/{len(tests)} failed")
        sys.exit(1)
    print(f"ALL {len(tests)} PASS")


if __name__ == "__main__":
    main()
