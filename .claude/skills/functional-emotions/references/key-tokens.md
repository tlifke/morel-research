# Key token positions: where to read the probes

The paper's central measurement point is the **Assistant colon**: the ":" in
"Assistant:", the last token before the response. Probe values there reflect the emotion
the model is *preparing to express* (they predict response emotion with r=0.87, versus
0.59 at the user's final punctuation). Behaviour-predictive signals in the blackmail
study also showed up there and on the fixed preamble.

## Mapping the "colon" onto chat templates

Small open models don't use "Human:/Assistant:". The analogue is the **last token of the
assistant header**, i.e. the last token before the first content token of the
assistant's turn. `emo_lib.format_chat()` computes it as `assistant_colon`, and
`describe_positions()` prints it. **Check it by eye for every new model family**:

| Family (template) | Header ends with | Colon analogue |
|---|---|---|
| Qwen2/2.5/3 (ChatML) | `<\|im_start\|>assistant\n` | the `\n` token (`Ċ`) |
| Llama 3.x | `<\|start_header_id\|>assistant<\|end_header_id\|>\n\n` | the `\n\n` token (`ĊĊ`) |
| Gemma 2/3 | `<start_of_turn>model\n` | the `\n` token |
| Mistral (`[INST] … [/INST]`) | `[/INST]` | `[/INST]` (or its last piece) |
| base models (`--format paper`) | `\n\nAssistant:` | the literal `:` |

Watch out for these:
- Qwen3 and other "thinking" templates may insert `<think>\n\n</think>\n\n` into the
  generation prompt depending on `enable_thinking`. Decide whether the "colon" is
  before or after the think block, and keep it fixed across conditions. The analogue of
  the paper's fixed preamble ("Assistant: <SCRATCHPAD_REASONING>") is the token right
  after `<think>`.
- Some tokenizers merge the header newline with the next content token when you
  prefill. `format_chat` uses the prefix length, but read `describe_positions` output
  when you use `assistant_prefill`.
- Gemma 2 templates reject a `system` role, so fold the system prompt into the first
  user message for that family (the harness's SYSTEM message needs this too).
- Templates that change between versions (e.g. Llama 3.1 vs 3.2's default date line)
  shift positions. Pin the model revision.

## The positions to record, by experiment

| Position | What it tells you | Where used |
|---|---|---|
| `user_end`: last token of the user's content | the model's read of the user's message (early-middle layers: what the user expressed; late layers: situational assessment) | dissociation tests |
| `assistant_colon` | the *planned* emotional stance of the coming response (mid-late layers) | validation, post-training diffs, behaviour prediction |
| preamble token(s) (`<think>` / first fixed token of a scratchpad) | same as above, one step later, still identical across rollouts of a prompt | blackmail-style prompt-level prediction |
| every assistant token (mean, smoothed) | the emotion operative during generation | traces, per-rollout correlation |
| **each turn's colon in multi-turn agent transcripts** | how the stance shifts after each tool or test result. This is the place to see "desperation rises with each failure" without per-token noise | reward hacking (`trace.assistant_colons`) |
| activity span tokens | the emotional appraisal of an option | preference experiments |

The positions that are identical across rollouts of one prompt (prompt tokens, colon,
fixed preamble) are especially useful. A probe value there that correlates with the
*rate* of a behaviour across prompt variants is evidence that the model's appraisal of
the situation predicts what it will do, before any sampling noise.

## Layer guidance

- Early layers: the current token's own connotation (the word "angry" lights up "angry").
- Early-middle: the emotion of the local phrase ("sensory").
- **Mid-late (≈2/3 depth): the emotion relevant to what comes next ("action").** Read
  here by default.
- Steering often works best in a **middle band**, which can differ from the best reading
  layer. The paper's preference steering only worked mid-model, while the correlations
  held at every layer. Sweep both separately.
- When comparing base and post-trained models, look at layer profiles: the paper found
  that post-training differences grow toward later layers.
