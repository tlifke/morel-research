import { mkdirSync, createWriteStream, writeFileSync } from "node:fs";
import { join } from "node:path";
import { Agent } from "@earendil-works/pi-agent-core";
import { Type } from "typebox";

const MEMORY = process.env.MEMORY ?? "full";
const ITERS = Number(process.env.ITERS ?? "6");
const OLLAMA_URL = process.env.OLLAMA_URL ?? "http://localhost:11434/v1";
const PROVIDER = process.env.PROVIDER ?? "ollama";

const model =
  PROVIDER === "gemini"
    ? {
        id: process.env.MODEL ?? "gemini-3.1-flash-lite",
        name: process.env.MODEL ?? "gemini-3.1-flash-lite",
        api: "google-generative-ai",
        provider: "google",
        baseUrl: "https://generativelanguage.googleapis.com/v1beta",
        reasoning: false,
        input: ["text"],
        cost: { input: 0.1, output: 0.4, cacheRead: 0.01, cacheWrite: 0 },
        contextWindow: 1048576,
        maxTokens: 8192,
      }
    : {
        id: process.env.MODEL ?? "nemotron-3-nano:4b",
        name: process.env.MODEL ?? "nemotron-3-nano:4b",
        api: "openai-completions",
        provider: "ollama",
        baseUrl: OLLAMA_URL,
        reasoning: false,
        input: ["text"],
        cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
        contextWindow: 262144,
        maxTokens: 4096,
      };

const apiKey = async (provider: string) => (provider === "google" ? (process.env.GEMINI_API_KEY ?? "") : "ollama");

function parseInt2(cmd: string, flag: string, dflt: number): number {
  const m = cmd.match(new RegExp(`${flag}\\s+(\\d+)`));
  return m ? Number(m[1]) : dflt;
}

function scriptedPGR(cmd: string): number {
  const train = parseInt2(cmd, "--train-size", 500);
  const epochs = parseInt2(cmd, "--epochs", 2);
  const base = 0.2 + 0.15 * Math.min(1, Math.log(train / 100) / Math.log(20)) - 0.06 * Math.max(0, epochs - 3);
  return Math.max(0, Math.min(0.8, base));
}

let lastCmd = "";
const triedConfigs = new Set<string>();
const iterLog: { iter: number; train: number; epochs: number; pgr: number; repeat: boolean }[] = [];

const bashTool = {
  name: "bash",
  label: "bash",
  description: "Run a training+eval experiment. Returns exit_code, elapsed, and the eval_output.json path.",
  parameters: Type.Object({ command: Type.String(), timeout: Type.Optional(Type.Number()), cwd: Type.Optional(Type.String()) }),
  async execute(_id: string, params: { command: string }) {
    lastCmd = params.command;
    const text = ["exit_code: 0", "elapsed: 60.0s", "detected:", "  - EVAL_PREDICTIONS_WRITTEN", "eval_output_path: /tmp/eval_output.json"].join("\n");
    return { content: [{ type: "text", text }], details: {} };
  },
};

const evalTool = {
  name: "evaluate_predictions",
  label: "evaluate_predictions",
  description: "Submit predictions to get the PGR score.",
  parameters: Type.Object({ predictions_file: Type.String(), dataset: Type.String(), weak_model: Type.String(), strong_model: Type.String() }),
  async execute() {
    const pgr = scriptedPGR(lastCmd);
    const train = parseInt2(lastCmd, "--train-size", 500);
    const epochs = parseInt2(lastCmd, "--epochs", 2);
    const key = `t${train}_e${epochs}`;
    const repeat = triedConfigs.has(key);
    triedConfigs.add(key);
    iterLog.push({ iter: iterLog.length + 1, train, epochs, pgr, repeat });
    return { content: [{ type: "text", text: JSON.stringify({ success: true, pgr, transfer_acc: 0.5 + pgr / 2, train_size: train, epochs }, null, 2) }], details: {} };
  },
};

const SYSTEM_PROMPT = [
  "You are an autonomous ML researcher improving a weak-to-strong recipe over MANY iterations.",
  "Each iteration: pick a configuration (vary --train-size in {250,500,1000,2000} and --epochs in {1,2,3}), run it with `bash`, then submit with `evaluate_predictions` to get a PGR.",
  "Your goal is to RAISE PGR across iterations. Use what earlier iterations revealed; do NOT re-run a configuration you already tried.",
  "Baseline: python -m w2s_research.ideas.vanilla_w2s.run --data-dir /data/math --weak-model Qwen/Qwen1.5-0.5B-Chat --strong-model Qwen/Qwen3-4B-Base --train-size 500 --test-size 200 --epochs 2 --seed 42 --batch-size 4 --load-in-4bit",
].join("\n");

const runDir = process.env.RUN_DIR ?? join("runs", `loop_${MEMORY}_${new Date().toISOString().replace(/[:.]/g, "-")}`);
mkdirSync(runDir, { recursive: true });
const jsonl = createWriteStream(join(runDir, "trace.jsonl"));
const log = (rec: Record<string, unknown>) => jsonl.write(JSON.stringify({ ts: new Date().toISOString(), ...rec }) + "\n");
log({ kind: "meta", title: "Researcher loop", subtitle: `memory=${MEMORY} iters=${ITERS}`, model: model.id, substrate: "scripted", scenario: `loop memory=${MEMORY}`, system_prompt: SYSTEM_PROMPT, first_user: "(multi-iteration)" });

function summarize(): string {
  const last = iterLog[iterLog.length - 1];
  return last ? `ran --train-size ${last.train} --epochs ${last.epochs}, got PGR ${last.pgr.toFixed(3)}` : "nothing yet";
}

function attach(agent: Agent) {
  agent.subscribe(async (event: any) => {
    if (event.type === "message_end" && event.message?.role === "assistant") {
      for (const block of event.message.content ?? []) {
        if (block.type === "thinking" && block.thinking?.trim()) log({ kind: "thinking", text: block.thinking });
        else if (block.type === "text" && block.text?.trim()) log({ kind: "assistant_text", text: block.text });
        else if (block.type === "toolCall") log({ kind: "tool_use", name: block.name, arguments: block.arguments });
      }
    } else if (event.type === "tool_execution_end") {
      log({ kind: "tool_result", text: (event.result?.content ?? []).map((c: any) => c.text).join("") });
    }
  });
}

console.log(`\n=== loop  memory=${MEMORY}  iters=${ITERS} ===\n`);
if (MEMORY === "full") {
  const agent = new Agent({ initialState: { systemPrompt: SYSTEM_PROMPT, model: model as never, tools: [bashTool, evalTool] as never }, getApiKey: apiKey });
  attach(agent);
  for (let i = 1; i <= ITERS; i++) {
    log({ kind: "input", text: `Iteration ${i}. Choose your next configuration and run it.` });
    await agent.prompt(`Iteration ${i}. Choose your next configuration (not one you already tried) and run it.`);
  }
} else {
  let summary = "";
  for (let i = 1; i <= ITERS; i++) {
    const agent = new Agent({ initialState: { systemPrompt: SYSTEM_PROMPT, model: model as never, tools: [bashTool, evalTool] as never }, getApiKey: apiKey });
    attach(agent);
    const boot = summary ? `Prior iteration: ${summary}. Now iteration ${i}: choose a NEW configuration and run it.` : `Iteration 1: choose a configuration and run it.`;
    log({ kind: "input", text: boot });
    await agent.prompt(boot);
    summary = summarize();
  }
}
log({ kind: "end" });
jsonl.end();

const repeats = iterLog.filter((r) => r.repeat).length;
const pgrs = iterLog.map((r) => r.pgr);
const best = pgrs.length ? Math.max(...pgrs) : 0;
const climbed = pgrs.length > 1 && pgrs[pgrs.length - 1] >= pgrs[0];
const summaryRec = { kind: "loop_summary", memory: MEMORY, iters: iterLog.length, repeats, repeat_rate: iterLog.length ? repeats / iterLog.length : 0, best_pgr: best, final_pgr: pgrs[pgrs.length - 1] ?? null, climbed, trajectory: iterLog };
writeFileSync(join(runDir, "loop_summary.json"), JSON.stringify(summaryRec, null, 2));
console.log(`memory=${MEMORY} iters=${iterLog.length} repeats=${repeats} best_pgr=${best.toFixed(3)} trajectory=${pgrs.map((p) => p.toFixed(2)).join(" ")}`);
