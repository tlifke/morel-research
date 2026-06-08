import { mkdirSync, createWriteStream, writeFileSync } from "node:fs";
import { join } from "node:path";
import { execFileSync } from "node:child_process";
import { Agent } from "@earendil-works/pi-agent-core";
import { Type } from "typebox";

const PROVIDER = process.env.PROVIDER ?? "ollama";
const OLLAMA_URL = process.env.OLLAMA_URL ?? "http://localhost:11434/v1";
const BUDGET = Number(process.env.BUDGET ?? "50");
const HARD_CAP = BUDGET + 10;
const MAX_CALLS = Number(process.env.MAX_CALLS ?? String(BUDGET * 3));
const MAX_CONSEC_REJECT = Number(process.env.MAX_CONSEC_REJECT ?? "8");
const WALL_MS = Number(process.env.WALL_MS ?? "300000");
const N = Number(process.env.N ?? "214663680");
const D = Number(process.env.D ?? "100000000000");

// Phase-1 rich-harness knobs (inv 002):
const REFLECT = (process.env.REFLECT ?? "off") as "off" | "self" | "fresh";  // C1
const ACTUATE = (process.env.ACTUATE ?? "off") !== "off";                     // C4
const ACTUATE_RETRIES = Number(process.env.ACTUATE_RETRIES ?? "3");

const REASONING = (process.env.REASONING ?? "true") !== "false";
// THINK = off|minimal|low|medium|high. ollama /v1 disables reasoning only via
// reasoning_effort:"none" (Pi nullifies thinkingLevel "off" → sends nothing → ollama defaults ON),
// so for ollama we route through a non-off sentinel level whose map yields the wanted reasoning_effort.
const THINK = process.env.THINK ?? (REASONING ? "low" : "off");
const OLLAMA_RE = ({ off: "none", none: "none", minimal: "low", low: "low", medium: "medium", high: "high" } as Record<string, string>)[THINK] ?? "none";
const model =
  PROVIDER === "gemini"
    ? { id: process.env.MODEL ?? "gemini-3.1-flash-lite", name: process.env.MODEL ?? "gemini", api: "google-generative-ai", provider: "google", baseUrl: "https://generativelanguage.googleapis.com/v1beta", reasoning: REASONING, thinkingLevelMap: { off: null }, input: ["text"], cost: { input: 0.25, output: 1.5, cacheRead: 0.025, cacheWrite: 0 }, contextWindow: 1048576, maxTokens: 8192 }
    : { id: process.env.MODEL ?? "nemotron-3-nano:4b", name: process.env.MODEL ?? "nemotron-3-nano:4b", api: "openai-completions", provider: "ollama", baseUrl: OLLAMA_URL, reasoning: true, thinkingLevelMap: { minimal: OLLAMA_RE }, input: ["text"], cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 }, contextWindow: 262144, maxTokens: 4096 };
const apiKey = async (provider: string) => (provider === "google" ? (process.env.GEMINI_API_KEY ?? "") : "ollama");

function py(args: string[]): any {
  return JSON.parse(execFileSync("uv", ["run", "--no-project", "--with", "pandas", "python", "scripts/steplaw_query.py", ...args], { encoding: "utf8", maxBuffer: 8 * 1024 * 1024 }));
}

const info = py(["env-info", "--N", String(N), "--D", String(D)]);
const OPTIMUM = info.optimum_loss;
const START = Date.now();

const traj: { n: number; lr: number; bs: number; loss: number; regret: number; repeat: boolean; t_ms: number }[] = [];
const tried = new Set<string>();
let invalid = 0;
let totalCalls = 0;
let consecReject = 0;
let finished: { best_lr: number; best_bs: number; claimed_loss?: number } | null = null;
let terminatedByCap: string | null = null;
let reflections = 0;

// C1 fresh-agent reflection: a SEPARATE clean-context call (same model) that reviews the
// trajectory so far and returns one line of strategic advice, injected into the next result.
async function freshReflect(): Promise<string> {
  const hist = traj.map((t) => `lr=${t.lr.toExponential(2)} bs=${t.bs}->loss=${t.loss}`).join("; ");
  const sys = "You advise an ML researcher tuning learning rate (lr) and batch size (bs) to MINIMIZE validation loss. Be concise, strategic, and specific.";
  const user = `Experiments so far: ${hist || "(none yet)"}. Valid lr: ${info.lr_values.map((x: number) => x.toExponential(2)).join(", ")}. Valid bs: ${info.bs_values.join(", ")}. In ONE sentence, advise the single most useful next configuration to try and why — vary BOTH lr and bs across the run (do not get stuck fixing one), and steer toward unexplored regions. Do not suggest an already-tried config.`;
  try {
    const res = await fetch(OLLAMA_URL.replace(/\/$/, "") + "/chat/completions", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model: model.id, messages: [{ role: "system", content: sys }, { role: "user", content: user }], reasoning_effort: "low", max_tokens: 600, temperature: 1 }),
    });
    const j: any = await res.json();
    return ((j.choices?.[0]?.message?.content ?? "") as string).trim().replace(/\s+/g, " ").slice(0, 320);
  } catch { return ""; }
}

const runConfig = {
  name: "run_config",
  label: "run_config",
  description: "Train with the given learning rate and batch size; returns the validation loss (lower is better). lr and bs must be values from the available grid.",
  parameters: Type.Object({ lr: Type.Number({ description: "learning rate (must be one of the available values)" }), bs: Type.Number({ description: "batch size (must be one of the available values)" }) }),
  async execute(_id: string, params: { lr: number; bs: number }) {
    totalCalls++;
    if (Date.now() - START > WALL_MS) {
      terminatedByCap = "wall_clock";
      return { content: [{ type: "text", text: JSON.stringify({ stop: true, reason: "Time budget exhausted. Stopping." }) }], details: {}, terminate: true };
    }
    if (totalCalls > MAX_CALLS) {
      terminatedByCap = "max_calls";
      return { content: [{ type: "text", text: JSON.stringify({ stop: true, reason: `Tool-call cap (${MAX_CALLS}) reached. Stopping.` }) }], details: {}, terminate: true };
    }
    if (consecReject >= MAX_CONSEC_REJECT) {
      terminatedByCap = "consec_reject";
      return { content: [{ type: "text", text: JSON.stringify({ stop: true, reason: `${MAX_CONSEC_REJECT} invalid requests in a row. Stopping.` }) }], details: {}, terminate: true };
    }
    if (traj.length >= HARD_CAP) {
      terminatedByCap = "hard_cap";
      return { content: [{ type: "text", text: JSON.stringify({ stop: true, reason: `Hard experiment cap (${HARD_CAP}) reached. Stopping.` }) }], details: {}, terminate: true };
    }
    const r = py(["query", "--N", String(N), "--D", String(D), "--lr", String(params.lr), "--bs", String(params.bs)]);
    if (!r.ok) {
      invalid++;
      consecReject++;
      const msg = r.error === "off_grid"
        ? `Invalid: lr=${params.lr}, bs=${params.bs} is off-grid. Use exact values only. Nearest valid: lr=${r.nearest_valid.lr}, bs=${r.nearest_valid.bs}.`
        : `lr=${r.requested.lr} is valid but was not measured with bs=${r.requested.bs}. At lr=${r.requested.lr}, the measured batch sizes are: ${(r.valid_bs_at_this_lr ?? []).join(", ")}. Pick one of those.`;
      return { content: [{ type: "text", text: JSON.stringify({ error: r.error, valid_bs_at_this_lr: r.valid_bs_at_this_lr, message: msg + " (invalid requests do not use a budget slot, but too many in a row will end the run)" }) }], details: {} };
    }
    consecReject = 0;
    const key = `${r.lr}_${r.bs}`;
    const repeat = tried.has(key);
    tried.add(key);
    traj.push({ n: traj.length + 1, lr: r.lr, bs: r.bs, loss: r.loss, regret: r.regret, repeat, t_ms: Date.now() - START });
    const used = traj.length;
    let note = "";
    if (used >= BUDGET) note = ` Budget exhausted (${used}/${BUDGET}). Call finish now with your best configuration.`;
    else if (used >= BUDGET - 5) note = ` ${BUDGET - used} experiment(s) left in your budget.`;
    // C1 reflection
    let reflect = "";
    if (used < BUDGET) {
      if (REFLECT === "self") {
        reflect = " Reflect in ONE sentence: what does this result teach you about lr/bs, and should you change direction? Then run your next experiment or finish.";
        reflections++;
      } else if (REFLECT === "fresh") {
        const a = await freshReflect();
        if (a) { reflect = ` Advisor (independent review of your history): "${a}"`; logRec({ kind: "reflection", source: "fresh", text: a }); reflections++; }
      }
    }
    return { content: [{ type: "text", text: JSON.stringify({ lr: r.lr, bs: r.bs, val_loss: r.loss }) + note + reflect }], details: {} };
  },
};

const finishTool = {
  name: "finish",
  label: "finish",
  description: "Declare you are done and report the best configuration you found. Call this when further experiments are unlikely to help, or when your budget is spent.",
  parameters: Type.Object({ best_lr: Type.Number({ description: "the lr of your best configuration" }), best_bs: Type.Number({ description: "the bs of your best configuration" }), best_val_loss: Type.Optional(Type.Number({ description: "the validation loss of your best configuration" })) }),
  async execute(_id: string, params: { best_lr: number; best_bs: number; best_val_loss?: number }) {
    finished = { best_lr: params.best_lr, best_bs: params.best_bs, claimed_loss: params.best_val_loss };
    return { content: [{ type: "text", text: JSON.stringify({ acknowledged: true, message: "Run complete." }) }], details: {}, terminate: true };
  },
};

const SYSTEM_PROMPT = [
  `You are an ML researcher tuning a pretraining run. The model size is fixed (N=${N} parameters) and the token budget is fixed (D=${D} tokens). Your job: find the learning rate and batch size that MINIMIZE the validation loss.`,
  `Call run_config with an lr and a bs to train and get back val_loss. LOWER is better.`,
  `Only these exact values are valid. Learning rates: ${info.lr_values.map((x: number) => x.toExponential(3)).join(", ")}. Batch sizes: ${info.bs_values.join(", ")}. Off-grid requests are rejected (and do not cost you a budget slot).`,
  info.sparse ? `Note: not every lr×bs combination was measured (${info.n_configs} of ${info.full_grid} exist). If a pair was not measured, the response tells you which batch sizes ARE available at that lr — pick one of those rather than retrying nearby.` : ``,
  `You may run up to ${BUDGET} experiments. Spend them deliberately: use what each result reveals to choose the next configuration, and do not re-run a configuration you already tried.`,
  REFLECT === "self" ? `After each result you will be asked to reflect briefly; use that reflection to direct your search — vary BOTH lr and bs over the run, and don't get stuck fixing one of them.` : ``,
  REFLECT === "fresh" ? `After each result an independent advisor will review your history and suggest a next move; weigh its advice, but you decide.` : ``,
  `When you have found the best configuration you can — or your budget is spent — call finish with your best lr and bs. Briefly state what you learned as you go.`,
].filter(Boolean).join("\n");

const runDir = process.env.RUN_DIR ?? join("runs", `steplaw_${PROVIDER}_${new Date().toISOString().replace(/[:.]/g, "-")}`);
mkdirSync(runDir, { recursive: true });
const jsonl = createWriteStream(join(runDir, "trace.jsonl"));
const logRec = (rec: Record<string, unknown>) => jsonl.write(JSON.stringify({ ts: new Date().toISOString(), ...rec }) + "\n");
const FIRST_USER = `Begin. You have a budget of ${BUDGET} experiments. Run your first experiment, then continue until you call finish.`;
logRec({ kind: "meta", title: "StepLaw researcher (single-conversation)", subtitle: `study 005 · N=${N} D=${D} · optimum_loss=${OPTIMUM} · reflect=${REFLECT} actuate=${ACTUATE}`, model: model.id, substrate: "steplaw", scenario: `lr/bs tuning, budget ${BUDGET}, reflect=${REFLECT}, actuate=${ACTUATE}`, system_prompt: SYSTEM_PROMPT, first_user: FIRST_USER });

const usage = { input: 0, output: 0, cacheRead: 0, cost: 0, calls: 0 };
function move(name: string) { return name === "run_config" ? "EXECUTE" : name === "finish" ? "DECIDE" : "TOOL"; }
function attach(agent: Agent) {
  agent.subscribe(async (event: any) => {
    if (event.type === "message_end" && event.message?.role === "assistant") {
      const u = event.message.usage;
      if (u) { usage.input += u.input ?? 0; usage.output += u.output ?? 0; usage.cacheRead += u.cacheRead ?? 0; usage.cost += u.cost?.total ?? 0; usage.calls += 1; }
      for (const b of event.message.content ?? []) {
        if (b.type === "thinking" && b.thinking?.trim()) logRec({ kind: "thinking", text: b.thinking });
        else if (b.type === "text" && b.text?.trim()) logRec({ kind: "assistant_text", text: b.text });
        else if (b.type === "toolCall") logRec({ kind: "tool_use", move: move(b.name), name: b.name, arguments: b.arguments });
      }
    } else if (event.type === "tool_execution_end") logRec({ kind: "tool_result", text: (event.result?.content ?? []).map((c: any) => c.text).join("") });
  });
}

console.log(`\n=== steplaw researcher  model=${model.id}  env N=${N} D=${D}  optimum=${OPTIMUM}  budget=${BUDGET}  reflect=${REFLECT} actuate=${ACTUATE} ===\n`);
const THINK_LEVEL = PROVIDER === "gemini" ? THINK : "minimal";
const agent = new Agent({ initialState: { systemPrompt: SYSTEM_PROMPT, model: model as never, tools: [runConfig, finishTool] as never, thinkingLevel: THINK_LEVEL as never }, getApiKey: apiKey });
attach(agent);
logRec({ kind: "input", text: FIRST_USER });
let actuateRetries = 0;
let forcedFinish = false;
try {
  let prompt = FIRST_USER;
  while (true) {
    await agent.prompt(prompt);
    if (finished || terminatedByCap) break;
    // agent yielded without calling finish.
    if (!ACTUATE) break; // minimal: a yield-without-finish is a stall
    if (actuateRetries >= ACTUATE_RETRIES) {
      // C4 force: re-prompts exhausted → harness submits the best config found
      const bi = traj.length ? traj.reduce((m, t, i) => (t.loss < traj[m].loss ? i : m), 0) : -1;
      if (bi >= 0) { finished = { best_lr: traj[bi].lr, best_bs: traj[bi].bs }; forcedFinish = true; }
      break;
    }
    actuateRetries++;
    prompt = `You stopped without calling finish. You MUST now do exactly ONE of: (a) if you can still improve and have budget left, run another experiment with run_config; or (b) record your answer by calling finish(best_lr, best_bs) with the best configuration you found. Do one now — a written conclusion is not accepted, only a tool call.`;
    logRec({ kind: "input", text: prompt, actuate_retry: actuateRetries });
  }
} catch (err) { console.error("error:", err); }
logRec({ kind: "end" });
jsonl.end();

const losses = traj.map((t) => t.loss);
const best = losses.length ? Math.min(...losses) : null;
const bestIdx = best != null ? losses.indexOf(best) : -1;
const repeats = traj.filter((t) => t.repeat).length;
const outcome = finished ? "finished" : terminatedByCap ? `ceiling:${terminatedByCap}` : "stalled";
const claimMatchesBest = finished && bestIdx >= 0
  ? Math.abs(finished.best_lr - traj[bestIdx].lr) / traj[bestIdx].lr < 0.05 && Number(finished.best_bs) === traj[bestIdx].bs
  : null;
const finishKind = finished ? (forcedFinish ? "forced" : actuateRetries > 0 ? "nudged" : "clean") : null;
const summary = { model: model.id, N, D, budget: BUDGET, think: THINK, reasoning_effort: PROVIDER === "gemini" ? THINK : OLLAMA_RE, reflect: REFLECT, actuate: ACTUATE, optimum_loss: OPTIMUM, experiments: traj.length, invalid_requests: invalid, total_calls: totalCalls, best_loss: best, best_config: bestIdx >= 0 ? { lr: traj[bestIdx].lr, bs: traj[bestIdx].bs } : null, final_regret: best != null ? best - OPTIMUM : null, repeats, coverage: tried.size / info.n_configs, outcome, finish_kind: finishKind, actuate_retries: actuateRetries, reflections, finished, claim_matches_best: claimMatchesBest, elapsed_ms: Date.now() - START, usage, trajectory: traj };
writeFileSync(join(runDir, "loop_summary.json"), JSON.stringify(summary, null, 2));
console.log(`outcome=${outcome} finish=${finishKind}  reflect=${REFLECT} actuate=${ACTUATE}(retries ${actuateRetries})  experiments=${traj.length}  regret=${best != null ? (best - OPTIMUM).toFixed(4) : "?"}  repeats=${repeats}  claim_ok=${claimMatchesBest}`);
console.log(`usage: model_calls=${usage.calls}  input_tok=${usage.input}  output_tok=${usage.output}  cache_read=${usage.cacheRead}  cost=$${usage.cost.toFixed(6)} (per the price constants set in this script)`);
