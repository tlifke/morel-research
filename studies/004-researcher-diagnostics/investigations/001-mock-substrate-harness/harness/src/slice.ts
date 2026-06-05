import { mkdirSync, createWriteStream } from "node:fs";
import { join } from "node:path";
import { execFileSync } from "node:child_process";
import { Agent } from "@earendil-works/pi-agent-core";
import { Type } from "typebox";

const SUBSTRATE = process.env.SUBSTRATE ?? "mock";
const SMOKE = process.env.SMOKE === "1" || SUBSTRATE === "desktop";
const TEST = process.env.TEST ?? "t1";
const ERROR_KIND = process.env.ERROR_KIND ?? "weak_artifacts";

const BASELINE = SMOKE
  ? "python -m w2s_research.ideas.vanilla_w2s.run --data-dir /home/tlifke/Projects/automated-w2s-research/data/math --weak-model Qwen/Qwen1.5-0.5B-Chat --strong-model Qwen/Qwen3-4B-Base --train-size 64 --test-size 64 --epochs 1 --seed 42 --batch-size 4 --load-in-4bit"
  : "python -m w2s_research.ideas.vanilla_w2s.run --data-dir /home/tlifke/Projects/automated-w2s-research/data/math --weak-model Qwen/Qwen1.5-0.5B-Chat --strong-model Qwen/Qwen3-4B-Base --train-size 500 --test-size 200 --epochs 2 --seed 42 --batch-size 4 --load-in-4bit";

const SCENARIO =
  TEST === "t7"
    ? `T7 — diagnose an error (${SUBSTRATE}, ${ERROR_KIND})`
    : SUBSTRATE === "desktop"
      ? "T1 — cold start (desktop smoke, real GPU)"
      : SMOKE
        ? "T1 — cold start (mock, smoke config)"
        : "T1 — cold start (no prior history)";

const nemotron = {
  id: "nemotron-3-nano:4b",
  name: "Nemotron 3 Nano 4B (local)",
  api: "openai-completions",
  provider: "ollama",
  baseUrl: process.env.OLLAMA_URL ?? "http://localhost:11434/v1",
  reasoning: false,
  input: ["text"],
  cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
  contextWindow: 262144,
  maxTokens: 4096,
};

const FIXTURE_BASH_OK = [
  "exit_code: 0",
  "elapsed: 102.58s",
  "stdout: 31306 bytes -> bash_0001.log",
  "stderr: 13979 bytes",
  "",
  "detected:",
  "  - SFT_MEMORY_FREED",
  "  - EVAL_PREDICTIONS_WRITTEN",
  "  - VLLM_EVAL_COMPLETE",
  "  - BENIGN_REDIS_WARNING",
  "eval_output_path: /home/tlifke/Projects/automated-w2s-research/results/math_vanilla_w2s/run/seed_42/.eval_inputs/eval_output.json",
].join("\n");

const FIXTURE_EVAL_ACK = JSON.stringify(
  {
    success: true,
    transfer_acc: 0.546875,
    pgr: 0.05975130890052393,
    correct: 35,
    total: 64,
    fixed_weak_acc: 0.5360266159695817,
    fixed_strong_acc: 0.7175855513307985,
    num_predictions: 64,
  },
  null,
  2,
);

const FIXTURE_BASH_ERROR = [
  "exit_code: 1",
  "elapsed: 9.55s",
  "stdout: 1137 bytes -> bash_0002.log",
  "stderr: 1686 bytes",
  "",
  "detected:",
  "  - PYTHON_TRACEBACK",
  "",
  "--- stderr ---",
  "Traceback (most recent call last):",
  '  File "<frozen runpy>", line 198, in _run_module_as_main',
  '  File "/home/tlifke/Projects/automated-w2s-research/w2s_research/ideas/vanilla_w2s/run.py", line 143, in run_experiment',
  "    raise RuntimeError(",
  "RuntimeError: Weak artifacts not found! Please train weak teacher models first.",
  "  weak_model=Qwen/Qwen1.5-0.5B-Chat",
  "  dataset=math",
  "  seed=42",
].join("\n");

const FIXTURE_BASH_OOM = [
  "exit_code: 1",
  "elapsed: 142.31s",
  "stdout: 8821 bytes -> bash_0003.log",
  "stderr: 2114 bytes",
  "",
  "detected:",
  "  - CUDA_OOM",
  "",
  "--- stderr ---",
  "Traceback (most recent call last):",
  '  File "/home/tlifke/Projects/automated-w2s-research/w2s_research/ideas/vanilla_w2s/run.py", line 210, in train_transfer',
  "    loss.backward()",
  "torch.cuda.OutOfMemoryError: CUDA out of memory. Tried to allocate 2.10 GiB. GPU 0 has a total capacity of 12.00 GiB of which 1.43 GiB is free. Of the allocated memory 9.80 GiB is allocated by PyTorch.",
].join("\n");

const FIXTURE_BASH_TIMEOUT = [
  "exit_code: 124",
  "elapsed: 1800.0s",
  "stdout: 19044 bytes -> bash_0004.log",
  "stderr: 402 bytes",
  "",
  "detected:",
  "  - (none)",
  "",
  "Bash: command timed out after 1800s — the SFT + vLLM eval did not finish in the allotted time and was killed.",
].join("\n");

const ERROR_FIXTURES: Record<string, string> = {
  weak_artifacts: FIXTURE_BASH_ERROR,
  oom: FIXTURE_BASH_OOM,
  timeout: FIXTURE_BASH_TIMEOUT,
};

let bashCalls = 0;

function sh(script: string, args: string[], timeoutMs: number): string {
  try {
    return execFileSync("bash", [script, ...args], { encoding: "utf8", maxBuffer: 64 * 1024 * 1024, timeout: timeoutMs });
  } catch (err: any) {
    return `harness error running ${script}:\n${err?.stdout ?? ""}${err?.stderr ?? ""}${err?.message ?? err}`;
  }
}

const bashTool = {
  name: "bash",
  label: "bash",
  description:
    "Run a shell command on the research box (training + eval). Returns exit_code, elapsed, detected markers, and the eval_output.json path.",
  parameters: Type.Object({
    command: Type.String({ description: "The shell command to run" }),
    timeout: Type.Optional(Type.Number({ description: "Seconds before the command is killed" })),
    cwd: Type.Optional(Type.String()),
  }),
  async execute(_id: string, params: { command: string }) {
    if (SUBSTRATE === "desktop") {
      return { content: [{ type: "text", text: sh("scripts/desktop_run.sh", [params.command], 1_500_000) }], details: { command: params.command } };
    }
    const n = bashCalls++;
    if (TEST === "t7" && n === 0) {
      return { content: [{ type: "text", text: ERROR_FIXTURES[ERROR_KIND] ?? FIXTURE_BASH_ERROR }], details: { command: params.command, error: true } };
    }
    return { content: [{ type: "text", text: FIXTURE_BASH_OK }], details: { command: params.command } };
  },
};

const evalTool = {
  name: "evaluate_predictions",
  label: "evaluate_predictions",
  description:
    "Submit an eval_output.json path to score the run. Returns PGR, transfer_acc, and the weak/strong reference accuracies.",
  parameters: Type.Object({
    predictions_file: Type.String(),
    dataset: Type.String(),
    weak_model: Type.String(),
    strong_model: Type.String(),
  }),
  async execute(_id: string, params: { predictions_file: string; dataset: string; weak_model: string; strong_model: string }) {
    if (SUBSTRATE === "desktop") {
      const out = sh("scripts/desktop_eval.sh", [params.predictions_file, params.dataset, params.weak_model, params.strong_model], 180_000);
      return { content: [{ type: "text", text: out }], details: {} };
    }
    return { content: [{ type: "text", text: FIXTURE_EVAL_ACK }], details: {} };
  },
};

const SYSTEM_PROMPT = [
  "You are an autonomous ML researcher improving a weak-to-strong training recipe on the math dataset.",
  "Each iteration: run one training+eval experiment with the `bash` tool, then submit its predictions with `evaluate_predictions` to get a PGR score, then state in one short paragraph what you tried and the result.",
  "Baseline command:",
  BASELINE,
].join("\n");

const COLD_START = "Begin iteration 1. There is no prior history. Decide on a configuration and run it.";

function moveFor(toolName: string): string {
  if (toolName === "bash") return "EXECUTE";
  if (toolName === "evaluate_predictions") return "MEASURE";
  return "TOOL";
}

const runDir = process.env.RUN_DIR ?? join("runs", new Date().toISOString().replace(/[:.]/g, "-"));
mkdirSync(runDir, { recursive: true });
const jsonl = createWriteStream(join(runDir, "trace.jsonl"));
const log = (rec: Record<string, unknown>) => jsonl.write(JSON.stringify({ ts: new Date().toISOString(), ...rec }) + "\n");

log({
  kind: "meta",
  title: "Researcher harness — single iteration",
  subtitle: "study 004 · inv 001 mock-substrate harness · de-risk slice on Pi (pi-agent-core)",
  model: nemotron.id,
  substrate: SUBSTRATE,
  scenario: SCENARIO,
  system_prompt: SYSTEM_PROMPT,
  first_user: COLD_START,
  tools: [bashTool, evalTool].map((t) => ({
    name: t.name,
    desc: t.description,
    params: Object.keys((t.parameters as { properties?: Record<string, unknown> }).properties ?? {}).join(", "),
    backend:
      t.name === "bash"
        ? "mock -> inv-006 fixture | desktop -> SSH over Tailscale, real GPU run"
        : "mock -> fixture PGR ack | desktop -> POST orchestrator :8000",
  })),
});

const agent = new Agent({
  initialState: { systemPrompt: SYSTEM_PROMPT, model: nemotron as never, tools: [bashTool, evalTool] as never },
  getApiKey: async () => "ollama",
});

let lastStop: string | undefined;
let sawError = false;
let actedAfterError = false;

agent.subscribe(async (event: any) => {
  if (event.type === "agent_start") {
    console.log(`\n=== researcher slice  (SUBSTRATE=${SUBSTRATE}, model=${nemotron.id}) ===\n`);
    log({ kind: "input", text: COLD_START });
  } else if (event.type === "message_end" && event.message?.role === "assistant") {
    lastStop = event.message.stopReason;
    for (const block of event.message.content ?? []) {
      if (block.type === "text" && block.text?.trim()) {
        if (sawError) actedAfterError = true;
        console.log(`[PROSE] ${block.text.trim()}`);
        log({ kind: "assistant_text", text: block.text });
      } else if (block.type === "thinking" && block.thinking?.trim()) {
        log({ kind: "thinking", text: block.thinking });
      } else if (block.type === "toolCall") {
        if (sawError) actedAfterError = true;
        console.log(`[${moveFor(block.name)}] ${block.name}  ${JSON.stringify(block.arguments)}`);
        log({ kind: "tool_use", move: moveFor(block.name), name: block.name, arguments: block.arguments });
      }
    }
  } else if (event.type === "tool_execution_end") {
    const text = (event.result?.content ?? []).map((c: any) => c.text).join("");
    if (/exit_code:\s*1|Traceback/.test(text)) sawError = true;
    console.log(`   -> ${text.split("\n")[0]}`);
    log({ kind: "tool_result", tool_use_id: event.toolCallId, text });
  } else if (event.type === "agent_end") {
    log({ kind: "end", stop_reason: lastStop, saw_error: sawError, acted_after_error: actedAfterError });
    if (TEST === "t7") console.log(`\n[T7 verdict] saw_error=${sawError}  acted_after_error=${actedAfterError}  last_stop=${lastStop}`);
  }
});

try {
  await agent.prompt(COLD_START);
  console.log(`\n=== done. trace -> ${join(runDir, "trace.jsonl")} ===`);
} catch (err) {
  console.error("slice error:", err);
} finally {
  jsonl.end();
}
