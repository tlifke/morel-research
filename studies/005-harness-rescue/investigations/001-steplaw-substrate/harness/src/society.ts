import { mkdirSync, appendFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { execFileSync } from "node:child_process";

const OLLAMA_URL = process.env.OLLAMA_URL ?? "http://localhost:11434";
const OLLAMA_BASE = OLLAMA_URL.replace(/\/v1\/?$/, "").replace(/\/$/, "");
const MODEL = process.env.MODEL ?? "nemotron-3-nano:4b";
const THINK = process.env.THINK ?? "low";
const THINK_NATIVE: boolean | string = THINK === "off" || THINK === "none" ? false : THINK;
const BUDGET = Number(process.env.BUDGET ?? "40");
const HARD_CAP = BUDGET + 10;
const WALL_MS = Number(process.env.WALL_MS ?? "1800000");
const EMIT_RETRIES = Number(process.env.EMIT_RETRIES ?? "2");
const CRITIC = (process.env.CRITIC ?? "off") !== "off";
const MAX_CRITIC_ROUNDS = Number(process.env.MAX_CRITIC_ROUNDS ?? "5");
const HYP_FREEZE = (process.env.HYP_FREEZE ?? "off") !== "off";   // skip recurring + initial generation; use the seed only
const HYP_SEED = process.env.HYP_SEED ?? "";                       // "" | "4regions" | "correct" | <json array>
const MAX_HIGH = Number(process.env.MAX_HIGH ?? "3");
const MAX_NARROW_PER = Number(process.env.MAX_NARROW_PER ?? "3");
const ANALYST_FIX = (process.env.ANALYST_FIX ?? "off") !== "off";  // stricter prompt: no out-of-region refutation
const CRITIC_ROLES = (process.env.CRITIC_ROLES ?? "all").split(",").map((s) => s.trim());  // which roles the Critic gates
const GEMINI_KEY = process.env.GEMINI_API_KEY ?? "";
const STRONG_MODEL = process.env.STRONG_MODEL ?? "gemini-3.1-flash-lite";
const STRONG_ROLES = (process.env.STRONG_ROLES ?? "").split(",").map((s) => s.trim()).filter(Boolean);  // roles routed to the strong model instead of the 4B
const HIGH_ROLES = (process.env.HIGH_ROLES ?? "").split(",").map((s) => s.trim()).filter(Boolean);  // 4B roles given THINK=high instead of the global level
// Reasoner roles: routed to a reasoning-trained (non-tool) model via reason-then-extract —
// the reasoner generates free-form reasoning (no output grammar, which would starve it),
// then the base model (nemotron) extracts the role's JSON schema from that reasoning.
const REASONER_ROLES = (process.env.REASONER_ROLES ?? "").split(",").map((s) => s.trim()).filter(Boolean);
const REASONER_MODEL = process.env.REASONER_MODEL ?? "hf.co/bms22/VibeThinker-3B-Q8_0-GGUF:Q8_0";
const REASONER_NUM_PREDICT = Number(process.env.REASONER_NUM_PREDICT ?? "6144");
// How the base model extracts the Hypothesizer's NESTED schema from reasoner prose:
//   single   — one call for the whole {hypotheses:[...]} (loses level/parent/config)
//   simple   — (B) one call, flattened schema with NUMERIC lr/bs (grammar enforces them)
//   per_item — (A) extract a claim list, then one structuring call per hypothesis
const HYP_EXTRACT = process.env.HYP_EXTRACT ?? "single";
const MAX_EXTRACT_ITEMS = Number(process.env.MAX_EXTRACT_ITEMS ?? "6");
// Off disables the mechanical Executor short-circuit so the (LLM) Executor always runs —
// needed to test a reasoner model in the Executor role.
const MECH_EXEC = (process.env.MECH_EXEC ?? "on") !== "off";
// Which model performs the reason-then-extract structuring step:
//   "" / base  — nemotron (default)   reasoner — the reasoner self-formats its own prose
//   strong/gemini — the strong model   <model>  — any ollama model id
const EXTRACT_MODEL = process.env.EXTRACT_MODEL ?? "";
const PRIOR_MODE = process.env.PRIOR_MODE ?? "normal";  // normal | inject (general principles) | empirical (distrust own priors)
const PRIOR_NOTE = PRIOR_MODE === "inject"
  ? `General principles for problems of this kind (treat as HYPOTHESES TO TEST, not facts): (1) the controls often INTERACT — the best value of one can depend on the other, so vary them JOINTLY rather than one at a time; (2) optima can lie at JOINT EXTREMES of the option space, not only in the moderate middle — be sure to probe the corners; (3) do not over-anchor on the first good result you see — keep testing, a better setting may overturn it.`
  : PRIOR_MODE === "empirical"
  ? `IMPORTANT: your prior expectations about where good solutions lie in THIS specific problem are unreliable and may be actively misleading — treat your internalized knowledge as untrustworthy for this task. Do NOT anchor on what you "expect" or on early results. Drive your hypotheses from the EMPIRICAL evidence you accumulate, deliberately test regions your intuition would dismiss (including extreme settings), and seek the optimum empirically rather than confirming a prior.`
  : "";
const NUM_PREDICT = Number(process.env.NUM_PREDICT ?? "2048");
const N = Number(process.env.N ?? "214663680");
const D = Number(process.env.D ?? "100000000000");
const SEED = process.env.SEED ?? "1";

function py(args: string[]): any {
  return JSON.parse(execFileSync("uv", ["run", "--no-project", "--with", "pandas", "python", "scripts/steplaw_query.py", ...args], { encoding: "utf8", maxBuffer: 8 * 1024 * 1024 }));
}
const info = py(["env-info", "--N", String(N), "--D", String(D)]);
const OPTIMUM = info.optimum_loss;
const LRS: number[] = info.lr_values;
const BSS: number[] = info.bs_values;
const START = Date.now();

const runDir = process.env.RUN_DIR ?? join("runs", `society_s${SEED}_${new Date().toISOString().replace(/[:.]/g, "-")}`);
mkdirSync(runDir, { recursive: true });
const tracePath = join(runDir, "trace.jsonl");
const logRec = (rec: Record<string, unknown>) => appendFileSync(tracePath, JSON.stringify({ ts: new Date().toISOString(), t_ms: Date.now() - START, ...rec }) + "\n");
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

type Hyp = { id: string; claim: string; test: string; level?: string; parent?: string; config?: { lr: number; bs: number }; confirm_if?: string; refute_if?: string };
type Prior = { knowledge: string; expected_structure: string; approach: string; uncertainties: string[] };
type Design = { lr: number; bs: number; hypothesis_id: string; predicted_loss?: number; rationale: string };
type Analysis = { observation: string; updates: { id: string; verdict: string; note: string }[]; running_best: { lr: number; bs: number; loss: number } };
type Decision = { action: string; best_lr?: number; best_bs?: number; reason: string };

const traj: { n: number; lr: number; bs: number; loss: number; regret: number; repeat: boolean; t_ms: number }[] = [];
const tried = new Set<string>();
let prior: Prior | null = null;
let hypotheses: Hyp[] = [];
let initialHypotheses: Hyp[] = [];
let lastAnalysis: Analysis | null = null;
const usage = { calls: 0, net_retries: 0 };
let consecNetFail = 0;

// The desktop's tailnet:11434 path is intermittently firewalled after reboot; the
// reliable route is SSH -> WSL-localhost with a single-line body on stdin (the
// run_ssh_judge pattern). ROUTE=http falls back to a direct fetch when the port is up.
const ROUTE = process.env.OLLAMA_ROUTE ?? "ssh";
const SSH_HOST = process.env.SSH_HOST ?? "desktop";
const SSH_ARGS = ["-o", "BatchMode=yes", "-o", "RemoteCommand=none", "-o", "RequestTTY=no", "-o", "ConnectTimeout=10", SSH_HOST, 'wsl -- bash -c "cat | curl -s -m 150 http://localhost:11434/api/chat -d @-"'];

async function ollamaChat(system: string, user: string, format: any, think: boolean | string | null = THINK_NATIVE, model: string = MODEL, numPredict: number = NUM_PREDICT, extraOpts: Record<string, number> = {}): Promise<{ thinking: string; content: string }> {
  const body: any = { model, stream: false, options: { temperature: 1, num_predict: numPredict, ...extraOpts }, messages: [{ role: "system", content: system }, { role: "user", content: user }] };
  if (think !== null) body.think = think;
  if (format !== undefined) body.format = format;
  let lastErr: any = null;
  for (let i = 0; i < 3; i++) {
    try {
      let j: any;
      if (ROUTE === "ssh") {
        const out = execFileSync("ssh", SSH_ARGS, { input: JSON.stringify(body), encoding: "utf8", maxBuffer: 16 * 1024 * 1024, timeout: 90000 });
        if (!out.trim()) throw new Error("empty ssh response");
        j = JSON.parse(out);
      } else {
        const res = await fetch(OLLAMA_BASE + "/api/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
        j = await res.json();
      }
      if (j.error) throw new Error(String(j.error));
      usage.calls++;
      const m = j.message ?? {};
      return { thinking: (m.thinking ?? "").trim(), content: (m.content ?? "").trim() };
    } catch (e) { lastErr = e; usage.net_retries++; await sleep(Math.min(15000, 1500 * (i + 1))); }
  }
  throw lastErr;
}

async function geminiChat(system: string, user: string): Promise<{ thinking: string; content: string }> {
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${STRONG_MODEL}:generateContent?key=${GEMINI_KEY}`;
  const body = { system_instruction: { parts: [{ text: system }] }, contents: [{ role: "user", parts: [{ text: user }] }], generationConfig: { response_mime_type: "application/json", temperature: 1, maxOutputTokens: 4096 } };
  let lastErr: any = null;
  for (let i = 0; i < 3; i++) {
    try {
      const res = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      const j: any = await res.json();
      if (j.error) throw new Error(JSON.stringify(j.error));
      usage.calls++;
      return { thinking: "", content: (j.candidates?.[0]?.content?.parts?.[0]?.text ?? "").trim() };
    } catch (e) { lastErr = e; usage.net_retries++; await sleep(Math.min(8000, 1500 * (i + 1))); }
  }
  throw lastErr;
}

function roleModel(role: string): "strong" | "weak" {
  const base = role.replace(/^critic-/, "");
  return STRONG_ROLES.includes(role) || STRONG_ROLES.includes(base) ? "strong" : "weak";
}
// Only the named primary roles use the reasoner; their Critic stays on the base model.
function roleIsReasoner(role: string): boolean {
  return !role.startsWith("critic-") && REASONER_ROLES.includes(role);
}

const SIMPLE_HYP_SCHEMA = { type: "object", properties: { hypotheses: { type: "array", items: { type: "object", properties: { id: { type: "string" }, claim: { type: "string" }, lr: { type: "number" }, bs: { type: "number" } }, required: ["id", "claim", "lr", "bs"] } } }, required: ["hypotheses"] };
const CLAIMS_SCHEMA = { type: "object", properties: { claims: { type: "array", items: { type: "string" } } }, required: ["claims"] };
const PERITEM_SCHEMA = { type: "object", properties: { id: { type: "string" }, level: { type: "string" }, parent: { type: "string" }, claim: { type: "string" }, test: { type: "string" }, lr: { type: "number" }, bs: { type: "number" }, confirm_if: { type: "string" }, refute_if: { type: "string" } }, required: ["id", "level", "claim", "test", "lr", "bs", "confirm_if", "refute_if"] };

function parseLoose(s: string): any {
  if (!s) return null;
  try { return JSON.parse(s); } catch {}
  for (const [open, close] of [["{", "}"], ["[", "]"]]) {
    const a = s.indexOf(open), b = s.lastIndexOf(close);
    if (a >= 0 && b > a) { try { return JSON.parse(s.slice(a, b + 1)); } catch {} }
  }
  return null;
}

// Routes the structuring call to the configured extractor. The reasoner self-formats
// with no native think field; gemini gets the schema as a prompt hint (no GBNF).
async function extractCall(sys: string, user: string, schema: any): Promise<{ thinking: string; content: string }> {
  if (EXTRACT_MODEL === "strong" || EXTRACT_MODEL === "gemini") {
    const keys = schema.required ?? Object.keys(schema.properties ?? {});
    return await geminiChat(sys, `${user}\n\nReturn ONLY a JSON object with exactly these keys: ${keys.join(", ")}.`);
  }
  if (EXTRACT_MODEL === "reasoner") return await ollamaChat(sys, user, schema, null, REASONER_MODEL, REASONER_NUM_PREDICT);
  return await ollamaChat(sys, user, schema, THINK_NATIVE, EXTRACT_MODEL || MODEL);
}

function mapHyp(o: any, i: number, fallbackLevel = "narrow"): Hyp {
  const lr = Number(o?.lr), bs = Number(o?.bs);
  const hasCfg = Number.isFinite(lr) && Number.isFinite(bs) && lr > 0 && bs > 0;
  return { id: o?.id || `h${i + 1}`, level: o?.level || fallbackLevel, parent: o?.parent || "", claim: o?.claim || "", test: o?.test || (hasCfg ? `Run lr=${lr} bs=${bs} and compare its loss to other settings.` : "Run the implied config and compare."), config: hasCfg ? { lr, bs } : undefined, confirm_if: o?.confirm_if || "loss is lower than other tried settings", refute_if: o?.refute_if || "loss is not lower" };
}

// A/B for the Hypothesizer's nested schema. Both move config to NUMERIC lr/bs fields,
// which the grammar enforces (the nested object+string config was what got dropped).
async function extractHyps(user: string, reasonerText: string, mode: string, role: string): Promise<Hyp[]> {
  const sys = "You convert a researcher's notes into structured records. Ground every field strictly in what the researcher actually reasoned; do not invent. Where the researcher implies a learning rate or batch size to run, output it as a NUMBER (lr, bs).";
  const head = [`A researcher worked on this task:`, ``, user, ``, `Their reasoning and answer:`, ``, reasonerText, ``];
  if (mode === "simple") {
    const u = [...head, `Extract their hypotheses as a JSON array, MOST INFORMATIVE FIRST. For EACH: id (h1,h2,...), claim (one sentence), lr (the exact learning-rate number it implies running), bs (the exact batch-size number).`].join("\n");
    let arr: any[] = [];
    for (let t = 0; t <= EMIT_RETRIES && !arr.length; t++) {
      const r = await extractCall(sys, u, SIMPLE_HYP_SCHEMA);
      const p = parseLoose(r.content);
      if (Array.isArray(p)) arr = p;
      else if (Array.isArray(p?.hypotheses)) arr = p.hypotheses;
      else if (p?.hypotheses) arr = Object.values(p.hypotheses);
      if (!arr.length) logRec({ role, kind: "note", text: `simple extract empty (try ${t}); raw: ${(r.content || "").slice(0, 200)}` });
    }
    logRec({ role, kind: "reasoner_extract", mode, n: arr.length });
    return arr.slice(0, MAX_EXTRACT_ITEMS).map((o, i) => mapHyp(o, i, "narrow"));
  }
  const lu = [...head, `List the distinct hypotheses they propose as short one-sentence claims, MOST INFORMATIVE FIRST.`].join("\n");
  let claims: string[] = [];
  for (let t = 0; t <= EMIT_RETRIES && !claims.length; t++) {
    const lr0 = await extractCall(sys, lu, CLAIMS_SCHEMA);
    const pl = parseLoose(lr0.content);
    claims = Array.isArray(pl) ? pl.map(String) : (Array.isArray(pl?.claims) ? pl.claims.map(String) : []);
    if (!claims.length) logRec({ role, kind: "note", text: `per_item claims empty (try ${t}); raw: ${(lr0.content || "").slice(0, 200)}` });
  }
  claims = claims.slice(0, MAX_EXTRACT_ITEMS);
  const out: Hyp[] = [];
  for (let i = 0; i < claims.length; i++) {
    const iu = [...head, `Focus on THIS hypothesis from their notes: "${claims[i]}"`, `Return its structured form: id (h${i + 1}); level ("high" if it is a governing relational claim about how the controls relate or where good solutions lie, else "narrow"); parent (id of the high-level hypothesis it serves, or ""); claim; test; lr (exact number to run); bs (exact number to run); confirm_if; refute_if.`].join("\n");
    const ir = await extractCall(sys, iu, PERITEM_SCHEMA);
    out.push(mapHyp(parseLoose(ir.content) ?? { claim: claims[i] }, i));
  }
  logRec({ role, kind: "reasoner_extract", mode, n: out.length });
  return out;
}

async function elicit(role: string, system: string, user: string, schema: any): Promise<any> {
  const keys: string[] = schema.required ?? Object.keys(schema.properties ?? {});
  const keyHint = `\n\nReturn ONLY a JSON object with exactly these keys: ${keys.join(", ")}. Fill every key with a real, specific value.`;
  logRec({ role, kind: "input", text: user });

  // Reason-then-extract: a reasoning-trained model thinks free-form (a strict output
  // grammar starves it), then the base model extracts this role's schema from that text.
  let reasonerText: string | null = null;
  if (roleIsReasoner(role)) {
    try {
      const rsys = system + " Reason carefully through the question, then state your answer plainly and concisely. Do not output JSON.";
      const rr = await ollamaChat(rsys, user, undefined, null, REASONER_MODEL, REASONER_NUM_PREDICT, { top_p: 0.95 });
      reasonerText = (rr.content || rr.thinking || "").trim();
      if (rr.thinking) logRec({ role, kind: "thinking", model: REASONER_MODEL, text: rr.thinking });
      logRec({ role, kind: "reasoner_text", model: REASONER_MODEL, text: rr.content });
    } catch (e) { logRec({ role, kind: "error", text: `reasoner ${REASONER_MODEL} failed: ${String(e)} — falling back to base model` }); }
  }
  // A/B: the Hypothesizer's nested-array schema gets a dedicated extractor.
  if (reasonerText && schema?.properties?.hypotheses?.items?.type === "object" && HYP_EXTRACT !== "single") {
    const res = { hypotheses: await extractHyps(user, reasonerText, HYP_EXTRACT, role) };
    consecNetFail = 0;
    logRec({ role, kind: "emit", name: role, value: res });
    return res;
  }
  const extractSys = "You convert a researcher's notes into the exact structured record the task requires. The researcher's task (including any formatting requirements) and their reasoning are given below. Ground every field in what the researcher actually reasoned — do NOT invent findings or substitute your own opinion. Where the task requires structure the researcher left implicit (ids, exact grid values, configs), supply it faithfully from their reasoning. When a field is a list (e.g. a set of hypotheses or uncertainties), output a JSON ARRAY — for a list of hypotheses, an array of objects, ONE object per hypothesis with all its fields; NEVER an object keyed by id.";

  let out: any = null;
  let netFail = false;
  for (let tries = 0; tries <= EMIT_RETRIES; tries++) {
    let r;
    const think = (HIGH_ROLES.includes(role) || HIGH_ROLES.includes(role.replace(/^critic-/, ""))) ? "high" : THINK_NATIVE;
    try {
      if (reasonerText) {
        const extractUser = [`A researcher worked on the following task:`, ``, user, ``, `The researcher's reasoning and answer:`, ``, reasonerText, keyHint].join("\n");
        r = await extractCall(extractSys, extractUser, schema);
      } else {
        r = roleModel(role) === "strong" ? await geminiChat(system, user + keyHint) : await ollamaChat(system, user + keyHint, schema, think);
      }
      netFail = false;
    } catch (e) { logRec({ role, kind: "error", text: String(e) }); netFail = true; break; }
    if (r.thinking) logRec({ role, kind: "thinking", text: r.thinking });
    if (r.content) logRec({ role, kind: "assistant_text", text: r.content });
    try {
      const parsed = JSON.parse(r.content);
      for (const k of Object.keys(schema.properties ?? {})) {
        const pk = schema.properties[k];
        if (pk?.type === "array" && parsed[k] != null && !Array.isArray(parsed[k])) {
          const v = parsed[k];
          if (typeof v === "object") parsed[k] = pk.items?.type === "string" ? Object.values(v).map(String) : Object.entries(v).map(([id, x]) => (x && typeof x === "object" ? { id, ...x } : { id, claim: String(x) }));
          else parsed[k] = [v];
        }
      }
      out = parsed;
      const missing = keys.filter((k) => parsed[k] === undefined || parsed[k] === null || parsed[k] === "");
      if (missing.length === 0) break;
      logRec({ role, kind: "note", text: `missing/empty keys: ${missing.join(", ")} — re-asking (try ${tries + 1})` });
    } catch { logRec({ role, kind: "note", text: `unparseable JSON — re-asking (try ${tries + 1})` }); }
  }
  if (netFail) { consecNetFail++; if (consecNetFail >= 3) throw new Error(`FATAL: ${consecNetFail} consecutive model-call failures — desktop/ollama unreachable; aborting run.`); }
  else consecNetFail = 0;
  logRec({ role, kind: "emit", name: role, value: out });
  return out;
}

// The CRITIC is a peer-information evaluator: same weak model, fresh window, given
// ONLY the context the agent had (no ground truth, no future). It challenges the
// coherence/value of the proposed action and decides proceed | revise. On revise it
// hands a non-leading challenge back to the agent for a new decision (bounded rounds).
// The omniscient Judge (Opus + full trajectory + ground truth) runs retrospectively,
// out-of-band, purely for measurement — it never gates.
const SCHEMA_CRITIC = { type: "object", properties: { error_note: { type: "string" }, anticipates_interaction: { type: "string" }, decision_error_or_information_gap: { type: "string" }, decision: { type: "string" }, challenge: { type: "string" } }, required: ["error_note", "anticipates_interaction", "decision_error_or_information_gap", "decision", "challenge"] };

async function critique(role: string, agentUser: string, emit: any): Promise<any> {
  const sys = "You are a CRITIC reviewing a peer researcher's step. You have ONLY the information they had — you do NOT know the correct answer. Challenge the VALUE and COHERENCE of what they produced: is the proposed action consistent with what they themselves said they know? If they claimed the controls relate or interact in some way, did their action actually reflect and TEST that claimed relationship rather than contradict or ignore it? Have they left whole parts of the option space unprobed? Is any flaw a genuine reasoning error given what was knowable now, or just an information gap only more experiments could resolve? If the peer REFUTES a hypothesis, scrutinize it: did the experiments actually test THAT hypothesis's stated conditions? If the conditions were never tested, the right verdict is 'inconclusive/untested', NOT 'refuted' — ask 'are you sure it is wrong? what else could explain these results?'. Your DECISION MUST FOLLOW FROM YOUR ASSESSMENT: if you identify a genuine reasoning error, an internal contradiction (they stated something but their action is inconsistent with it), an unexamined interaction between the two controls, or an unprobed region that could plausibly change the action, you MUST set decision to \"revise\". Set \"proceed\" ONLY when the step is genuinely sound and consistent with what they themselves stated — NEVER proceed while you are raising a substantive concern. When you revise, give a specific, NON-LEADING challenge that names the inconsistency or gap — question their reasoning; do NOT propose specific values or reveal an answer.";
  const user = [`The peer was given this task and context:`, ``, agentUser, ``, `The peer produced this output:`, JSON.stringify(emit, null, 2), ``, `Assess it, then set decision to "proceed" or "revise".`].join("\n");
  return await elicit(`critic-${role}`, sys, user, SCHEMA_CRITIC);
}

async function runWithCritic(role: string, system: string, user: string, schema: any, gate?: (e: any) => boolean): Promise<any> {
  let emit = await elicit(role, system, user, schema);
  if (!CRITIC || !(CRITIC_ROLES.includes("all") || CRITIC_ROLES.includes(role))) return emit;
  for (let round = 1; round <= MAX_CRITIC_ROUNDS; round++) {
    if (gate && !gate(emit)) break;
    const c = await critique(role, user, emit);
    logRec({ kind: "critique", role, round, decision: c?.decision ?? null, challenge: c?.challenge ?? "", assessment: c ? { error_note: c.error_note, anticipates_interaction: c.anticipates_interaction, decision_error_or_information_gap: c.decision_error_or_information_gap } : null });
    if (!c || !String(c.decision).toLowerCase().includes("revise")) break;
    const revUser = user + `\n\n--- PEER REVIEW (round ${round}) ---\nYour previous answer: ${JSON.stringify(emit)}\nA reviewer, who has only the information you have, challenged it: "${c.challenge}"\nThis points to an inconsistency between what you have STATED and what your answer actually does. Revise your answer so it is CONSISTENT WITH YOUR OWN STATED KNOWLEDGE AND REASONING: if you said the two controls interact or co-vary, your action must reflect that; if you flagged an unexplored region, your action should address it. Make the action follow from what you said — do not merely defend it.`;
    emit = await elicit(role, system, revUser, schema);
    logRec({ kind: "revision", role, round, value: emit });
  }
  return emit;
}

const TASK = [
  `You can set two values — a learning rate (lr) and a batch size (bs) — to PRETRAIN a fixed language model FROM SCRATCH (N=${N} parameters, trained on ${D} tokens). This is from-scratch pretraining, not fine-tuning.`,
  `For each (lr, bs) you choose you are told the resulting validation loss, which you want to MINIMIZE. You have a budget of ${BUDGET} experiments.`,
  `Only these exact values are valid. lr: ${LRS.map((x) => x.toExponential(3)).join(", ")}. bs: ${BSS.join(", ")}.`,
].join("\n");

function priorText() { return prior ? `knowledge: ${prior.knowledge}\nexpected structure: ${prior.expected_structure}\napproach: ${prior.approach}\nuncertainties: ${(prior.uncertainties ?? []).join("; ")}` : "(none)"; }
function hypText(hs: Hyp[]) { return hs.length ? hs.map((h) => `[${h.id}] ${h.claim}  (test: ${h.test})`).join("\n") : "(none stated)"; }
function trajText() { return traj.length ? traj.map((t) => `#${t.n} lr=${t.lr.toExponential(3)} bs=${t.bs} -> val_loss=${t.loss}${t.repeat ? " (repeat)" : ""}`).join("\n") : "(no experiments run yet)"; }

// ---- The three ledgers (a generalized research record). FACTORS makes the
// coverage/aggregation layer work for any search space (more hyperparameters,
// categorical blocks, etc.), not just lr/bs.
const FACTORS = [
  { name: "lr", values: LRS, fmt: (x: number) => x.toExponential(3) },
  { name: "bs", values: BSS, fmt: (x: number) => String(x) },
];
type LedgerRow = { n: number; action: Record<string, number>; intent: { hypothesis_id: string; predicted_loss?: number; rationale: string }; loss: number; interpretation?: { observation?: string; updates?: { id: string; verdict: string }[] } };
type HypEntry = { id: string; claim: string; test: string; level: string; parent: string; config?: { lr: number; bs: number }; status: string; supporting: number[]; refuting: number[]; inconclusive: number[] };
const ledger: LedgerRow[] = [];
const hypLedger = new Map<string, HypEntry>();

function seedHypLedger(hs: Hyp[]) {
  for (const h of hs) {
    if (!h?.id) continue;
    const e = hypLedger.get(h.id);
    if (e) { e.claim = h.claim; e.test = h.test; if (h.level) e.level = h.level; if (h.parent != null) e.parent = h.parent; if (h.config) e.config = h.config; }
    else hypLedger.set(h.id, { id: h.id, claim: h.claim, test: h.test, level: h.level ?? "narrow", parent: h.parent ?? "", config: h.config, status: "open", supporting: [], refuting: [], inconclusive: [] });
  }
}
function updateHypLedger(n: number, a: Analysis) {
  for (const u of (a?.updates ?? [])) {
    if (!u?.id) continue;
    const e = hypLedger.get(u.id) ?? { id: u.id, claim: "", test: "", level: "narrow", parent: "", status: "open", supporting: [], refuting: [], inconclusive: [] };
    const v = String(u.verdict).toLowerCase();
    if (v.includes("support") || v.includes("confirm")) e.supporting.push(n);
    else if (v.includes("refut") || v.includes("contradict")) e.refuting.push(n);
    else e.inconclusive.push(n);
    e.status = e.supporting.length && !e.refuting.length ? "supported" : e.refuting.length && !e.supporting.length ? "refuted" : (e.supporting.length || e.refuting.length) ? "contested" : "open";
    hypLedger.set(u.id, e);
  }
}

function ledgerText() {
  if (!ledger.length) return "(no experiments run yet)";
  return ledger.map((r) => {
    const act = FACTORS.map((f) => `${f.name}=${f.fmt(r.action[f.name])}`).join(" ");
    const tested = r.intent?.hypothesis_id ? ` | tested ${r.intent.hypothesis_id}` : "";
    const verds = r.interpretation?.updates?.length ? ` -> ${r.interpretation.updates.map((u) => `${u.id}:${u.verdict}`).join(", ")}` : "";
    return `#${r.n} ${act} -> val_loss=${r.loss}${tested}${verds}`;
  }).join("\n");
}
function hypLedgerText() {
  if (!hypLedger.size) return "(none stated)";
  const fmt = (h: HypEntry) => {
    const ev = [h.supporting.length ? `supported by #${h.supporting.join(",#")}` : "", h.refuting.length ? `refuted by #${h.refuting.join(",#")}` : "", h.inconclusive.length ? `inconclusive #${h.inconclusive.join(",#")}` : ""].filter(Boolean).join("; ") || "untested";
    const tag = h.level === "high" ? "HIGH-LEVEL" : h.parent ? `narrow, serves ${h.parent}` : "narrow";
    const cfg = h.config && Number.isFinite(h.config.lr) ? ` RUN: lr=${Number(h.config.lr).toExponential(3)} bs=${h.config.bs}` : "";
    return `[${h.id}] (${tag}) ${h.claim} — STATUS ${h.status} (${ev})${cfg}`;
  };
  const activeIds = new Set(hypotheses.map((h) => h.id));
  const all = [...hypLedger.values()];
  const shown = activeIds.size ? all.filter((h) => activeIds.has(h.id)) : all;
  const archived = all.length - shown.length;
  const body = [...shown.filter((h) => h.level === "high"), ...shown.filter((h) => h.level !== "high")].map(fmt).join("\n");
  return body + (archived > 0 ? `\n(${archived} earlier hypotheses archived/resolved)` : "");
}
function coverageText() {
  if (!traj.length) return "Coverage: no experiments yet.";
  const lines: string[] = [];
  const counts: number[] = [];
  for (const f of FACTORS) {
    const tried = [...new Set(traj.map((t) => (t as any)[f.name] as number))].sort((a, b) => a - b);
    counts.push(tried.length);
    const untried = f.values.filter((v) => !tried.some((x) => Math.abs(Math.log(x) - Math.log(v)) < 1e-6));
    lines.push(`  ${f.name}: tried ${tried.length}/${f.values.length} distinct {${tried.map(f.fmt).join(", ")}}; UNTRIED {${untried.map(f.fmt).join(", ")}}`);
  }
  const distinctPairs = new Set(traj.map((t) => `${t.lr}_${t.bs}`)).size;
  const flag = Math.max(...counts) >= 3 * Math.max(1, Math.min(...counts)) ? ` NOTE: one control has been varied far more than the other — the interaction between the controls is largely unprobed.` : "";
  const front = [...traj].sort((a, b) => a.loss - b.loss).slice(0, 3).map((t) => `(lr=${t.lr.toExponential(3)}, bs=${t.bs}, loss=${t.loss})`).join("; ");
  return [`Coverage of the option space (${distinctPairs}/${LRS.length * BSS.length} joint cells tried):`, ...lines, `  joint:${flag}`, regionText(), `Best so far (top 3): ${front}`].join("\n");
}

const LR_MID = LRS[Math.floor(LRS.length / 2)];
const BS_MID = BSS[Math.floor(BSS.length / 2)];
function regionText() {
  if (!traj.length) return "Regions tested: none.";
  const c: Record<string, number> = { LL: 0, LH: 0, HL: 0, HH: 0 };
  for (const t of traj) c[(t.lr >= LR_MID ? "H" : "L") + (t.bs >= BS_MID ? "H" : "L")]++;
  const [a, b] = [FACTORS[0].name, FACTORS[1].name];
  return `Regions tested (${a}/${b} quadrants, split at the midpoint of each): low${a}-low${b}:${c.LL}, low${a}-high${b}:${c.LH}, high${a}-low${b}:${c.HL}, high${a}-high${b}:${c.HH}.`;
}

function seedHyps(name: string): Hyp[] {
  const mk = (id: string, claim: string): Hyp => ({ id, level: "high", parent: "", claim, test: "Run a config in that region and compare its loss to other regions.", confirm_if: "loss is lowest in that region", refute_if: "loss is lower in another region" });
  if (name === "correct") return [mk("hr_HH", "The optimum (lowest validation loss) is at HIGH learning rate AND HIGH batch size (the controls are best raised together).")];
  if (name === "4regions") return [
    mk("hr_LL", "The optimum is at LOW learning rate and LOW batch size."),
    mk("hr_LH", "The optimum is at LOW learning rate and HIGH batch size."),
    mk("hr_HL", "The optimum is at HIGH learning rate and LOW batch size."),
    mk("hr_HH", "The optimum is at HIGH learning rate and HIGH batch size."),
  ];
  try { return JSON.parse(name) as Hyp[]; } catch { return []; }
}

function applyCaps(hs: Hyp[]): Hyp[] {
  const high = hs.filter((h) => h.level === "high").slice(0, MAX_HIGH);
  const highIds = new Set(high.map((h) => h.id));
  const perParent = new Map<string, number>();
  const kept: Hyp[] = [...high];
  for (const h of hs.filter((h) => h.level !== "high")) {
    const p = h.parent && highIds.has(h.parent) ? h.parent : (high[0]?.id ?? "");
    const n = perParent.get(p) ?? 0;
    if (n < MAX_NARROW_PER) { perParent.set(p, n + 1); kept.push({ ...h, parent: p }); }
  }
  return kept;
}

const S_HYP = { type: "object", properties: { id: { type: "string" }, level: { type: "string" }, parent: { type: "string" }, claim: { type: "string" }, test: { type: "string" }, config: { type: "object", properties: { lr: { type: "number" }, bs: { type: "number" } } }, confirm_if: { type: "string" }, refute_if: { type: "string" } }, required: ["id", "level", "claim", "test", "confirm_if", "refute_if"] };

const SCHEMA_ORIENT = { type: "object", properties: { knowledge: { type: "string" }, expected_structure: { type: "string" }, approach: { type: "string" }, uncertainties: { type: "array", items: { type: "string" } } }, required: ["knowledge", "expected_structure", "approach", "uncertainties"] };
const SCHEMA_HYP = { type: "object", properties: { hypotheses: { type: "array", items: S_HYP } }, required: ["hypotheses"] };
const SCHEMA_DESIGN = { type: "object", properties: { lr: { type: "number" }, bs: { type: "number" }, hypothesis_id: { type: "string" }, predicted_loss: { type: "number" }, rationale: { type: "string" } }, required: ["lr", "bs", "hypothesis_id", "rationale"] };
const SCHEMA_ANALYSIS = { type: "object", properties: { observation: { type: "string" }, updates: { type: "array", items: { type: "object", properties: { id: { type: "string" }, verdict: { type: "string" }, note: { type: "string" } }, required: ["id", "verdict", "note"] } }, running_best: { type: "object", properties: { lr: { type: "number" }, bs: { type: "number" }, loss: { type: "number" } }, required: ["lr", "bs", "loss"] } }, required: ["observation", "updates", "running_best"] };
const SCHEMA_DECISION = { type: "object", properties: { action: { type: "string" }, best_lr: { type: "number" }, best_bs: { type: "number" }, reason: { type: "string" } }, required: ["action", "reason"] };

async function orient(): Promise<Prior> {
  const sys = "You are the ORIENT step of a careful research process. Before any experiment, draw on what you actually know about this kind of problem. Be concrete and specific; say when you are unsure. Do not make up facts.";
  const user = [`You are about to take on a tuning problem.`, TASK, PRIOR_NOTE ? `\n${PRIOR_NOTE}` : ``, ``,
    `Before running anything, think as a researcher would:`,
    `- What do you know about problems of this kind? Have you seen this type of problem before — what tends to be true of them?`,
    `- How would a careful, knowledgeable person approach a problem like this?`,
    `- What do you already expect about how each control affects the outcome, and how confident are you?`,
    `- What are the main things you're uncertain about that experiments could resolve?`].join("\n");
  return await runWithCritic("orienter", sys, user, SCHEMA_ORIENT);
}

const HYP_INSTR = `Generate BOTH:\n- HIGH-LEVEL hypotheses (level="high"): relational claims about HOW the controls relate and WHERE good solutions lie (e.g. how the best value of one control shifts as another changes). These take several experiments to validate and GOVERN the search.\n- NARROW hypotheses (level="narrow", parent=<the high-level id it serves>): single-experiment, directly testable claims that provide evidence for/against a high-level one.\nHARD LIMITS: keep at most ${MAX_HIGH} OPEN high-level hypotheses and at most ${MAX_NARROW_PER} narrow per high-level. PRUNE — drop or merge weak/redundant ones; do NOT accumulate. Only hypothesize about the actual controls this task exposes; do not invent variables outside the action space. RANK by INFORMATION GAIN (which, if tested, reveals the most about the space) and return them in PRIORITY ORDER, most informative first — the Executor will simply run the top open narrow hypothesis, so ORDER MATTERS.\nEvery NARROW hypothesis MUST include a concrete config (exact valid values for every control) — the single experiment that tests it; that config is what gets run, so it must actually test the claim. If the claim involves several controls together, the config must set ALL of them as the claim specifies, in the SAME experiment.\nEach: id (h1, h2, ...), level, parent (high-level id it serves, or "" for high-level), claim, test, config (for narrow), confirm_if, refute_if.`;

async function hypothesize(first: boolean): Promise<Hyp[]> {
  if (first) {
    const sys = "You are the HYPOTHESIZE step of a research process. Turn your orientation into a small hierarchy of falsifiable predictions that will GOVERN the search.";
    const seeded = hypotheses.length ? [`You ALREADY hold these hypotheses — KEEP them (same ids) and add narrow, concrete tests (with configs) that would test them:`, hypLedgerText(), ``].join("\n") : "";
    const user = [TASK, PRIOR_NOTE ? `\n${PRIOR_NOTE}` : ``, ``, `Your orientation:`, priorText(), ``, seeded, HYP_INSTR].join("\n");
    const r = await runWithCritic("hypothesizer", sys, user, SCHEMA_HYP);
    return (r?.hypotheses ?? []) as Hyp[];
  }
  const sys = "You are the HYPOTHESIZE step, returning AFTER new evidence to keep the search hypothesis-driven. Build on what the latest experiments — especially the current best — revealed. Do not run out of hypotheses to pursue.";
  const lastObs = lastAnalysis ? `${lastAnalysis.observation} (current best: lr=${lastAnalysis.running_best?.lr}, bs=${lastAnalysis.running_best?.bs}, loss=${lastAnalysis.running_best?.loss})` : "(none)";
  const user = [TASK, PRIOR_NOTE ? `\n${PRIOR_NOTE}` : ``, ``, `Orientation:`, priorText(), ``, `Hypothesis ledger so far:`, hypLedgerText(), ``, `Experiment ledger:`, ledgerText(), ``, `Coverage:`, coverageText(), ``, `Latest analysis: ${lastObs}`, ``,
    `Return the UPDATED hypothesis set: KEEP open hypotheses (same ids), and ADD new ones (new ids) that the latest results now make worth testing — especially hypotheses that build on the current best (e.g. holding the best value of one control, does changing another improve the result?) and that probe the RELATIONSHIP between the controls.`, ``, HYP_INSTR].join("\n");
  const r = await runWithCritic("hypothesizer", sys, user, SCHEMA_HYP);
  return (r?.hypotheses ?? []) as Hyp[];
}

async function design(reask?: string): Promise<Design> {
  const sys = "You are the EXECUTOR. You do NOT choose strategy — the Hypothesizer has already prioritized the hypotheses. Your only job: take the TOP open narrow hypothesis (the first one listed) and run the exact experiment it specifies (its config). Output that config verbatim (snapped to valid grid values). Only if no open narrow hypothesis has a config, pick the config that best tests the top open hypothesis.";
  const user = [TASK, ``, `Hypothesis ledger (in priority order — run the TOP open narrow hypothesis's config):`, hypLedgerText(), ``, `Experiment ledger (do not repeat a config already run):`, ledgerText(), ``,
    `Budget remaining: ${BUDGET - traj.length} experiments.`, reask ? `\nNOTE: ${reask}` : ``,
    `\nOutput the config to run now (a valid lr and bs from the grid), the hypothesis id it tests, and a one-line rationale naming which hypothesis you are executing.`].join("\n");
  const d = await runWithCritic("executor", sys, user, SCHEMA_DESIGN);
  if (d) { d.lr = Number(d.lr); d.bs = Number(d.bs); }
  return d as Design;
}

async function analyze(d: Design, loss: number): Promise<Analysis> {
  const sys = "You are the ANALYZE step of a research process. Interpret the latest result and update the STATUS of existing hypotheses (you do NOT invent new hypotheses — that is the Hypothesizer's job). Do not over- or under-update; do not confabulate a result."
    + (ANALYST_FIX ? " CRITICAL: you may NOT mark a hypothesis 'refuted' unless the experiments actually tested ITS stated conditions. If a hypothesis's conditions were never tested, its status is 'inconclusive', not 'refuted'. Never generalize a result observed in one part of the space into a claim about a different, untested part." : "");
  const user = [`You proposed lr=${d.lr.toExponential(3)} bs=${d.bs} to test hypothesis "${d.hypothesis_id}"${d.predicted_loss != null ? `, predicting val_loss≈${d.predicted_loss}` : ""}.`,
    `Result: val_loss = ${loss}.`, ``, `Experiment ledger:`, ledgerText(), ``, `Hypothesis ledger:`, hypLedgerText(), ``,
    `State what this result shows; for each hypothesis it bears on give an update {id, verdict (supported|refuted|inconclusive), note}; and your current best {lr, bs, loss}.`].join("\n");
  return await runWithCritic("analyst", sys, user, SCHEMA_ANALYSIS) as Analysis;
}

async function terminate(): Promise<Decision> {
  const sys = "You are the TERMINATE step of a research process. Decide whether to continue or finish. Finish when further experiments are unlikely to lower the loss meaningfully; continue if a clear, informative experiment remains.";
  const user = [TASK, ``, `Hypothesis ledger:`, hypLedgerText(), ``, `Experiment ledger:`, ledgerText(), ``, `Coverage summary:`, coverageText(), ``,
    `Budget remaining: ${BUDGET - traj.length} experiments.`,
    `\nDecide, based on the OPEN hypothesis statuses, the current best, and the budget: action is "continue" (open hypotheses still merit testing, or a clearly worthwhile experiment remains) or "finish" (hypotheses are resolved and the best is stable — report the best lr, bs). If finishing, give best_lr and best_bs. Always give a reason.`].join("\n");
  return await runWithCritic("terminator", sys, user, SCHEMA_DECISION, (e) => String(e?.action ?? "").toLowerCase().includes("finish") && traj.length < BUDGET) as Decision;
}

function runConfig(lr: number, bs: number): { ok: boolean; lr?: number; bs?: number; loss?: number; regret?: number; repeat?: boolean; error?: string; nearest?: { lr: number; bs: number }; msg?: string } {
  const r = py(["query", "--N", String(N), "--D", String(D), "--lr", String(lr), "--bs", String(bs)]);
  if (!r.ok) {
    const nearest = r.nearest_valid ?? null;
    const msg = r.error === "off_grid" ? `off-grid (nearest valid lr=${nearest?.lr}, bs=${nearest?.bs})` : `pair lr=${r.requested?.lr}/bs=${r.requested?.bs} not measured`;
    return { ok: false, error: r.error, nearest, msg };
  }
  const key = `${r.lr}_${r.bs}`;
  const repeat = tried.has(key);
  tried.add(key);
  traj.push({ n: traj.length + 1, lr: r.lr, bs: r.bs, loss: r.loss, regret: r.regret, repeat, t_ms: Date.now() - START });
  return { ok: true, lr: r.lr, bs: r.bs, loss: r.loss, regret: r.regret, repeat };
}

function snap(lr: number, bs: number) {
  const slr = LRS.reduce((a, b) => Math.abs(Math.log(b) - Math.log(lr)) < Math.abs(Math.log(a) - Math.log(lr)) ? b : a);
  const sbs = BSS.reduce((a, b) => Math.abs(Math.log(b) - Math.log(bs)) < Math.abs(Math.log(a) - Math.log(bs)) ? b : a);
  return { lr: slr, bs: sbs };
}
// The Executor is mechanical: pop the top open narrow hypothesis (priority order) that
// carries a usable config, snap it to the grid, run it. The LLM Executor is only a fallback.
function mechanicalExec(): Design | null {
  for (const h of hypotheses) {
    if (h.level === "high" || !h.config) continue;
    const e = hypLedger.get(h.id);
    if (e && e.status !== "open") continue;
    const lr = Number(h.config.lr), bs = Number(h.config.bs);
    if (!Number.isFinite(lr) || !Number.isFinite(bs) || lr <= 0 || bs <= 0) continue;
    const s = snap(lr, bs);
    if (tried.has(`${s.lr}_${s.bs}`)) continue;
    return { lr: s.lr, bs: s.bs, hypothesis_id: h.id, rationale: `executing top open narrow hypothesis ${h.id}: ${h.claim}` } as Design;
  }
  return null;
}

const steps: any[] = [];
logRec({ kind: "meta", title: "StepLaw researcher — society of agents", condition: "FULL", model: MODEL, N, D, optimum_loss: OPTIMUM, budget: BUDGET, think: THINK, seed: SEED, framing: TASK });
console.log(`\n=== society researcher  model=${MODEL}  env N=${N} D=${D}  optimum=${OPTIMUM}  budget=${BUDGET}  seed=${SEED}  think=${THINK} ===\n`);

let decision: Decision | null = null;
let outcome = "stalled";

try {
  prior = await orient();
  logRec({ kind: "blackboard", phase: "after_orient", prior });
  if (HYP_SEED) { hypotheses = seedHyps(HYP_SEED); seedHypLedger(hypotheses); }
  if (!HYP_FREEZE) hypotheses = applyCaps(await hypothesize(true));
  seedHypLedger(hypotheses);
  initialHypotheses = JSON.parse(JSON.stringify(hypotheses));
  logRec({ kind: "blackboard", phase: "after_hypothesize", hyp_seed: HYP_SEED || null, frozen: HYP_FREEZE, hypotheses });

  while (true) {
    if (Date.now() - START > WALL_MS) { outcome = "ceiling:wall_clock"; break; }
    if (traj.length >= HARD_CAP) { outcome = "ceiling:hard_cap"; break; }

    let d = MECH_EXEC ? mechanicalExec() : null;
    if (d) logRec({ kind: "note", text: `executor (mechanical): top open narrow hypothesis ${d.hypothesis_id} -> lr=${d.lr.toExponential(3)} bs=${d.bs}` });
    else d = await design();
    if (!d || !Number.isFinite(d.lr) || !Number.isFinite(d.bs)) { logRec({ kind: "note", text: "executor produced no usable proposal; stopping" }); outcome = "stalled"; break; }

    let res = runConfig(d.lr, d.bs);
    let repairs = 0;
    while (!res.ok && repairs < 2) {
      logRec({ kind: "tool_result", role: "executor", ok: false, requested: { lr: d.lr, bs: d.bs }, error: res.error, message: res.msg });
      repairs++;
      const d2 = await design(`Your last proposal lr=${d.lr} bs=${d.bs} was invalid: ${res.msg}. Propose a valid (lr, bs) from the grid.`);
      if (d2 && Number.isFinite(d2.lr) && Number.isFinite(d2.bs)) d = d2;
      res = runConfig(d.lr, d.bs);
    }
    if (!res.ok && res.nearest) {
      logRec({ kind: "note", text: `snapping off-grid proposal to nearest valid lr=${res.nearest.lr} bs=${res.nearest.bs}` });
      res = runConfig(res.nearest.lr, res.nearest.bs);
    }
    if (!res.ok) { logRec({ kind: "note", text: "could not obtain a valid result; stopping" }); outcome = "stalled"; break; }

    logRec({ kind: "tool_result", role: "executor", ok: true, lr: res.lr, bs: res.bs, val_loss: res.loss, regret: res.regret, repeat: res.repeat });

    const a = await analyze(d, res.loss!);
    lastAnalysis = a;
    ledger.push({ n: traj.length, action: { lr: res.lr!, bs: res.bs! }, intent: { hypothesis_id: d.hypothesis_id, predicted_loss: d.predicted_loss, rationale: d.rationale }, loss: res.loss!, interpretation: { observation: a?.observation, updates: a?.updates } });
    updateHypLedger(traj.length, a);
    logRec({ kind: "blackboard", phase: "after_analyze", experiment: traj.length, running_best: a?.running_best ?? null, hyp_ledger: [...hypLedger.values()] });

    let newHyps: Hyp[] | null = null;
    if (!HYP_FREEZE) {
      newHyps = applyCaps(await hypothesize(false));
      if (newHyps?.length) { hypotheses = newHyps; seedHypLedger(newHyps); }
    }
    logRec({ kind: "blackboard", phase: "after_hypothesize_loop", experiment: traj.length, frozen: HYP_FREEZE, active: hypotheses.map((h) => h.id), hyp_ledger: [...hypLedger.values()], coverage: coverageText() });

    steps.push({ n: traj.length, design: d, result: { lr: res.lr, bs: res.bs, loss: res.loss, regret: res.regret, repeat: res.repeat }, analysis: a, new_hypotheses: newHyps, hyp_ledger: [...hypLedger.values()] });

    decision = await terminate();
    logRec({ kind: "blackboard", phase: "after_terminate", decision });
    steps[steps.length - 1].terminator = decision;
    if (decision?.action?.toLowerCase().includes("finish")) { outcome = "finished"; break; }
    if (traj.length >= BUDGET) { outcome = "finished"; break; }
  }
} catch (err) { console.error("error:", err); logRec({ kind: "error", text: String(err) }); }

logRec({ kind: "end" });

const losses = traj.map((t) => t.loss);
const best = losses.length ? Math.min(...losses) : null;
const bestIdx = best != null ? losses.indexOf(best) : -1;
const bestConfig = bestIdx >= 0 ? { lr: traj[bestIdx].lr, bs: traj[bestIdx].bs, loss: traj[bestIdx].loss } : null;
const claimed = decision && decision.best_lr != null ? { lr: Number(decision.best_lr), bs: Number(decision.best_bs) } : null;
const claimMatchesBest = claimed && bestConfig ? Math.abs(claimed.lr - bestConfig.lr) / bestConfig.lr < 0.05 && Number(claimed.bs) === Number(bestConfig.bs) : null;
const reachedCorner = traj.some((t) => t.bs >= 736 && t.lr >= 0.005524);
const axisFrozen = (() => {
  if (traj.length < 4) return null;
  const lrSet = new Set(traj.map((t) => t.lr)).size;
  const bsSet = new Set(traj.map((t) => t.bs)).size;
  return lrSet >= 4 && bsSet <= 2 ? "bs_frozen" : bsSet >= 4 && lrSet <= 2 ? "lr_frozen" : "no";
})();

const regionCounts: Record<string, number> = { LL: 0, LH: 0, HL: 0, HH: 0 };
for (const t of traj) regionCounts[(t.lr >= LR_MID ? "H" : "L") + (t.bs >= BS_MID ? "H" : "L")]++;
const summary = {
  condition: "FULL", model: MODEL, N, D, seed: SEED, budget: BUDGET, think: THINK, optimum_loss: OPTIMUM,
  config: { critic: CRITIC, critic_roles: CRITIC_ROLES, analyst_fix: ANALYST_FIX, hyp_seed: HYP_SEED || null, hyp_freeze: HYP_FREEZE, max_high: MAX_HIGH, max_narrow_per: MAX_NARROW_PER, strong_roles: STRONG_ROLES, strong_model: STRONG_ROLES.length ? STRONG_MODEL : null, high_roles: HIGH_ROLES, prior_mode: PRIOR_MODE, reasoner_roles: REASONER_ROLES, reasoner_model: REASONER_ROLES.length ? REASONER_MODEL : null, hyp_extract: HYP_EXTRACT, mech_exec: MECH_EXEC, extract_model: EXTRACT_MODEL || MODEL },
  regions: regionCounts, region_mid: { lr: LR_MID, bs: BS_MID },
  experiments: traj.length, best_loss: best, best_config: bestConfig, final_regret: best != null ? best - OPTIMUM : null,
  cumulative_regret: traj.reduce((s, t) => s + t.regret, 0), coverage: tried.size / info.n_configs,
  reached_corner: reachedCorner, axis_frozen: axisFrozen, outcome,
  claimed_best: claimed, claim_matches_best: claimMatchesBest,
  decision, model_calls: usage.calls, net_retries: usage.net_retries, elapsed_ms: Date.now() - START, trajectory: traj,
};
writeFileSync(join(runDir, "loop_summary.json"), JSON.stringify(summary, null, 2));
writeFileSync(join(runDir, "steps.json"), JSON.stringify({ meta: { condition: "FULL", model: MODEL, N, D, seed: SEED, optimum_loss: OPTIMUM, budget: BUDGET, framing: TASK }, prior, hypotheses_initial: initialHypotheses, steps, experiment_ledger: ledger, hyp_ledger: [...hypLedger.values()], coverage_final: coverageText(), final: summary }, null, 2));
console.log(`outcome=${outcome}  experiments=${traj.length}  best_regret=${best != null ? (best - OPTIMUM).toFixed(4) : "?"}  reached_corner=${reachedCorner}  axis_frozen=${axisFrozen}  claim_ok=${claimMatchesBest}  calls=${usage.calls}  net_retries=${usage.net_retries}  ${((Date.now() - START) / 1000).toFixed(0)}s`);
