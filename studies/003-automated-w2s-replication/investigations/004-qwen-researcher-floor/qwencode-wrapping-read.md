# 4c — QwenCode wrapping read

Sources read:

- `QwenLM/qwen-code` @ `331f45e9` (`packages/core/src`, esp. `core/prompts.ts`,
  `core/openaiContentGenerator/converter.ts`,
  `core/openaiContentGenerator/streamingToolCallParser.ts`,
  `core/openaiContentGenerator/provider/*.ts`).
- `QwenLM/Qwen-Agent` @ `31a4d36d` (`qwen_agent/llm/fncall_prompts/nous_fncall_prompt.py`,
  `qwen_agent/llm/function_calling.py`).
- Qwen docs: `qwen.readthedocs.io/en/latest/framework/function_call.html`.
- HF model cards for `Qwen/Qwen3-Coder-30B-A3B-Instruct` and
  `Qwen/Qwen3-Coder-480B-A35B-Instruct` (`qwen3coder_tool_parser.py`).

## 1. What QwenCode actually does

- **Wire protocol is OpenAI chat-completions.** The single canonical content
  generator under `core/openaiContentGenerator/` produces requests with
  `tools=[{type:"function", function:{name,description,parameters}}]` and
  expects `choices[].message.tool_calls[]` back. Native `tool_calls`,
  identical to the OpenAI dialect. No XML, no `<tool_call>` tags on the wire
  for the default model path. Anthropic Messages is a *separate* converter
  used only when the user explicitly points the CLI at an Anthropic endpoint.
- **One streaming parser handles fragmentation, not format.**
  `streamingToolCallParser.ts` reconstructs `tool_calls` arguments JSON
  arriving in chunks across SSE deltas; it does index-collision resolution
  and JSON repair (auto-close unclosed strings). It does *not* recognise
  `<tool_call>` XML, JSON-in-markdown, `<function_call>` tags, or any
  Qwen-specific text format. Models that don't emit native `tool_calls`
  simply produce zero tool calls — the parser has nothing to repair into.
- **System prompt is a long Claude-Code-style brief** (`prompts.ts`,
  ~1176 lines, `getCoreSystemPrompt`). It opens with "You are Qwen Code…
  utilizing your available tools" and exhaustively names canonical tool
  identifiers (`ToolNames.TODO_WRITE`, `ToolNames.SHELL`, `ToolNames.READ_FILE`,
  `ToolNames.GREP`, `ToolNames.GLOB`, `ToolNames.EDIT`, `ToolNames.WRITE_FILE`,
  `ToolNames.ASK_USER_QUESTION`, …). Sample excerpt:

  ```
  - **Path Construction:** Before using any file system tool (e.g.,
    ${ToolNames.READ_FILE}' or '${ToolNames.WRITE_FILE}'), you must
    construct the full absolute path for the file_path argument.
  ```

  ```
  - **Tools vs. Text:** Use tools for actions, text output *only* for
    communication. Do not add explanatory comments within tool calls or
    code blocks unless specifically part of the required code/command
    itself.
  ```

  i.e. it pins tool names hard, and it explicitly warns against shell-as-
  markdown — the exact failure mode we saw with qwen3:4b/8b in 003.

- **Provider shims are per-vendor, not per-model.** `provider/dashscope.ts`,
  `deepseek.ts`, `mistral.ts`, etc. configure `baseURL`, auth, max tokens,
  reasoning-content handling. None inject a text-format tool-call parser.
  The qwen-code working assumption is *the endpoint serves native
  `tool_calls`*; if it doesn't, qwen-code breaks the same way our shim does
  (see qwen-code issue #176, "Tool calling does not work with local model
  qwen3-30b-a3b").

- **Qwen-Agent (separate repo) is where the text-format parsing lives.**
  `nous_fncall_prompt.py` ships a `<tool_call>{json}</tool_call>` system-
  prompt template plus a regex-based parser that recovers tool calls from
  the model's text output. Used when the inference backend doesn't support
  native function calling (vLLM without the qwen3_xml parser, raw HF
  transformers, etc.). Template excerpt:

  ```
  For each function call, return a json object with function name and
  arguments within <tool_call></tool_call> XML tags:
  <tool_call>
  {"name": <function-name>, "arguments": <args-json-object>}
  </tool_call>
  ```

  This is the *Qwen-native* idiom, and it's a strict superset of one of the
  fallbacks qwen3:4b emitted to us (`<function_call>{json}</function_call>`).

- **Qwen3-Coder uses yet a third format** when run through its HF reference
  parser: nested-XML, not JSON-in-XML —
  `<tool_call><function=NAME><parameter=KEY>VALUE</parameter>…</function></tool_call>`.
  vLLM ships `--tool-call-parser qwen3_xml` to translate this back to
  OpenAI `tool_calls`. Qwen3-Coder is a separate finetune lineage from
  qwen3 / qwen3.5 chat models; this format does not apply to the 4B-class
  models we tested.

## 2. Contrast with our Claude-SDK-shaped shim

| Dimension | Our shim (Anthropic-shaped, via Ollama) | QwenCode (OpenAI-shaped, direct) | Qwen-Agent nous (text-mode) |
|---|---|---|---|
| Tool request shape | `tools=[{name,description,input_schema}]` (Anthropic) | `tools=[{type:"function",function:{name,description,parameters}}]` (OpenAI) | Same schemas, rendered into the system prompt as `<tools>...</tools>` |
| Tool response shape | `ToolUseBlock{name,input,id}` blocks | `message.tool_calls[].function.{name,arguments}` | Free-text `<tool_call>{json}</tool_call>` parsed by regex |
| Built-in tools | MCP-backed (Bash, Read, Write, etc. via `builtins.py`) | Native TS implementations registered in tool registry | App-defined |
| Text-format fallback | Path A in our shim (parses `<function_call>`, fenced JSON, bare JSON) | None — relies on the endpoint | Primary path |
| System prompt | Upstream Claude-tuned automated-w2s prompt | Long Qwen-Code-specific brief with canonical tool names + anti-narration rules | Standard template + tool descriptions |
| Tool-name binding | Hint patched on as `tool_invocation_hint` | Hard-coded in every prompt section | Names appear in `<tools>` descriptions only |

**Structural differences:** zero. Both qwen-code and our shim are
"native-tool-call wire format + system prompt that names tools." The wire
format is OpenAI vs Anthropic, but Ollama's Anthropic-compat endpoint and
its OpenAI endpoint are both wrappers over the same model output — the
model emits a tool-call special-token sequence and the server translates.
Qwen-Agent's nous mode is the structurally different one, and it lives
*outside* qwen-code.

**Cosmetic differences:** the prompt body. QwenCode's prompt names
`Shell`, `ReadFile`, `WriteFile` in canonical case, dozens of times,
across worked examples. Our upstream automated-w2s prompt names `Bash`,
`Read`, `Write` once each at the top, then talks about research methodology
for the rest. That's the only material delta.

## 3. Reading A vs. Reading B verdict

**Reading A** ("our shim is fine; coerce harder via prompting").

QwenCode is structurally isomorphic to our shim modulo OpenAI-vs-Anthropic
wire dialect — both bet that the model emits native tool-call tokens that
the endpoint translates. QwenCode's *additional* engineering is entirely
prompt-side: name tools constantly, name them in canonical case, give
worked examples, explicitly forbid shell-in-markdown. That maps 1:1 onto
003 cell-2/3 findings: qwen3.5:4b without the patch hallucinates names;
*with* the patch (which names canonical tools) it lands cleanly. The
binding strengthens with prompt density, not with harness shape.

The qwen3 family's narrate-as-markdown failure also has a known QwenCode
counterpart — issue #176 reports exactly this against qwen3-30b-a3b. The
QwenLM team's recommended fix is upgrading to Qwen3-Coder with the
qwen3_xml parser, i.e. a different *model*, not a different *harness*.
Qwen3-Coder happens to also use a different format (nested XML) but that's
a finetune-lineage artifact, not a sign that the OpenAI tool_calls
contract was wrong — it's a sign that qwen3 chat-tuned models at 4B-30B
have unreliable native tool-emission and Alibaba's answer is "use the
coder finetune."

The only place a structurally-different wrapping helps is when you can't
get native tool_calls at all — and the answer there is Qwen-Agent's nous
template, which is text-mode parsing of `<tool_call>` tags. Our shim's
Path A already does the equivalent of this, more permissively (matches
`<function_call>`, fenced JSON, bare JSON, naked tags).

**Verdict: Reading A.** The Claude-SDK protocol shape is not depressing
Qwen's measured capability. What's depressing measured capability is the
prompt: the upstream automated-w2s prompt was tuned for Claude (which
binds tool names lightly because Claude has strong tool-emission priors),
and 4B-class Qwen models need much heavier prompt-side name pinning to
hit the same target. The `tool_invocation_hint` patch is doing the work
QwenCode's whole system prompt does by default.

## 4. Recommendation on 4d

**Collapse 4d to a paragraph.** A Qwen-native harness spike (text-mode
tool-call parsing in the Qwen-Agent nous idiom) would be:

- Slower than what we already have (Path A already catches text-format
  emissions when they happen, but on qwen3.5:4b+patch they don't happen —
  the model emits native `tool_use`).
- Functionally a downgrade from native tool calling, not an upgrade.
- Decoupled from the actual failure (tool-name drift and command-
  recovery), which is a prompt and reasoning problem.

The right follow-on is *not* 4d but a prompt-side experiment along the
QwenCode lines: pin tool names harder, add canonical-case worked examples,
add an explicit anti-narration clause to the system prompt (Qwen-Code's
"Tools vs. Text" line). That's an extension of 4b, not a new
investigation.

If 4b's 5-patch budget exhausts without progress *and* the failures look
shape-coupled (e.g. we see Qwen routinely emit valid `<tool_call>` tags
that the shim wouldn't accept), revisit. Until then, 4d is a paragraph.

## Things I made up that you should review

- The claim "QwenCode is structurally isomorphic modulo OpenAI/Anthropic
  wire dialect" treats Ollama's Anthropic-compat endpoint as a faithful
  translation of the same underlying model output. That's been true in
  our gate-3/4 results but I didn't independently verify against Ollama's
  source.
- I'm reading qwen-code issue #176 as confirming the qwen3-family
  narrate-as-markdown failure is universal, not Ollama-specific. The
  issue title fits; I didn't read every comment.
- Recommendation to collapse 4d assumes 4b's prompt patches can plausibly
  reach the QwenCode prompt's density. If 4b's budget is too tight for
  that, the right call might be to lift QwenCode's system-prompt
  scaffolding wholesale, which is closer in spirit to a harness change.
