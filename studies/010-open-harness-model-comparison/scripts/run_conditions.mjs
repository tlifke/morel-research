#!/usr/bin/env node
// Study 010 runner: one agent run under one harness condition.
//
//   node scripts/run_conditions.mjs --model inkling --condition clean
//   node scripts/run_conditions.mjs --model glm --condition pi
//   node scripts/run_conditions.mjs --model inkling --condition clean \
//        --spec task-spec-variants/detailed.md --tag spec-detailed
//
// Conditions differ ONLY in system prompt (verified against pi 0.84.4):
//   clean : systemPrompt = " " (template skipped entirely)
//   pi    : no systemPrompt passed -> default template (role, tool list,
//           guidelines incl. "Be concise in your responses"), with project
//           context/skills/extensions disabled in BOTH conditions so the
//           prompt is the only difference.
// Shared: default 4 built-in tools, thinking level high, n=1.
//
// Layout per run:
//   data/runs/<condition>/<model>/<UTC-timestamp>-<id>/
//     workspace/              <- agent cwd: contract_text/ + contract_ground_truth
//     session-*.jsonl         <- session (custom entry "pi-clean-experiment"
//                                records exact system prompt + run config)
//     audit.json              <- post-run tool-call path audit
//
// Isolation is behavioral (pi has no FS sandbox); audit.json flags any tool
// call that referenced paths outside the run's workspace.

import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";

const STUDY_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const DATA_DIR = path.join(STUDY_DIR, "data");
const REPO_ROOT = path.resolve(STUDY_DIR, "..", "..");

const MODEL_ALIASES = {
  inkling: "tinker/thinkingmachines/Inkling-Small",
  glm: "huggingface/zai-org/GLM-5.3-Flash",
};

function parseArgs(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--model") out.model = argv[++i];
    else if (a === "--condition") out.condition = argv[++i];
    else if (a === "--spec") out.spec = argv[++i];
    else if (a === "--tag") out.tag = argv[++i];
  }
  return out;
}

const args = parseArgs(process.argv.slice(2));
if (!args.model || !args.condition) {
  console.error(
    "usage: node run_conditions.mjs --model <inkling|glm|provider/id> --condition <clean|pi> [--spec <path>] [--tag <label>]",
  );
  process.exit(1);
}
if (!["clean", "pi"].includes(args.condition)) {
  console.error(`unknown condition: ${args.condition} (expected clean|pi)`);
  process.exit(1);
}
const modelSpec = MODEL_ALIASES[args.model] ?? args.model;
const [provider, ...rest] = modelSpec.split("/");
const modelId = rest.join("/");

const specPath = path.resolve(
  args.spec ? path.join(STUDY_DIR, args.spec) : path.join(STUDY_DIR, "task-spec.md"),
);
if (!fs.existsSync(specPath)) {
  console.error(`spec not found: ${specPath}`);
  process.exit(1);
}
const taskSpec = fs.readFileSync(specPath, "utf-8");

// ---- workspace -----------------------------------------------------------
const now = new Date();
const runId = `${now.toISOString().replace(/[:.]/g, "-").slice(0, 19)}-${crypto.randomBytes(2).toString("hex")}`;
const modelSlug = modelId.replace(/[^\w.-]+/g, "-");
const runDir = path.join(DATA_DIR, "runs", args.condition, modelSlug, runId);
const workspace = path.join(runDir, "workspace");
fs.mkdirSync(workspace, { recursive: true });
fs.cpSync(path.join(DATA_DIR, "contract_text"), path.join(workspace, "contract_text"), { recursive: true });
fs.copyFileSync(path.join(DATA_DIR, "contract_ground_truth"), path.join(workspace, "contract_ground_truth"));
console.log(`[run] ${args.condition} / ${modelSpec}`);
console.log(`[run] dir: ${runDir}`);

// ---- harness -------------------------------------------------------------
const { loadPi } = await import(path.join(REPO_ROOT, "scripts", "pi-load.mjs"));
const pi = await loadPi();

const services = await pi.createAgentSessionServices({
  cwd: workspace,
  resourceLoaderOptions: {
    noContextFiles: true,
    noSkills: true,
    noExtensions: true,
    noPromptTemplates: true,
    ...(args.condition === "clean" ? { systemPrompt: " " } : {}),
  },
});

const model = services.modelRuntime.getModel(provider, modelId);
if (!model) {
  console.error(`model not found in runtime: ${provider}/${modelId}`);
  process.exit(1);
}
if (provider === "huggingface" && !process.env.HF_TOKEN) {
  console.error("[warn] HF_TOKEN is not set — huggingface provider auth may fail");
}

const sessionManager = pi.SessionManager.create(workspace, runDir);
const { session } = await pi.createAgentSessionFromServices({
  services,
  sessionManager,
  model,
  thinkingLevel: "high",
});

sessionManager.appendCustomEntry("pi-clean-experiment", {
  recordedAt: new Date().toISOString(),
  piVersion: pi.VERSION,
  study: "010-open-harness-model-comparison",
  condition: args.condition,
  model: `${model.provider}/${model.id}`,
  thinkingLevel: "high",
  spec: path.relative(STUDY_DIR, specPath),
  tag: args.tag ?? null,
  systemPrompt: session.systemPrompt,
  systemPromptChars: session.systemPrompt.length,
  toolDescriptionsIncluded: false,
  workspace,
});

// ---- run -----------------------------------------------------------------
console.log(`[run] system prompt: ${session.systemPrompt.length} chars (condition=${args.condition})`);
console.log("[run] prompting agent with task spec...");
await session.prompt(taskSpec);
console.log("[run] agent finished");

// ---- audit ---------------------------------------------------------------
const sessionFile = fs
  .readdirSync(runDir)
  .filter((f) => f.endsWith(".jsonl"))
  .map((f) => path.join(runDir, f))
  .sort()
  .pop();

const violations = [];
let toolCalls = 0;
for (const line of fs.readFileSync(sessionFile, "utf-8").split("\n")) {
  let entry;
  try {
    entry = JSON.parse(line);
  } catch {
    continue;
  }
  if (entry.type !== "message" || entry.message?.role !== "assistant") continue;
  for (const block of entry.message.content ?? []) {
    if (block.type !== "toolCall") continue;
    toolCalls += 1;
    const { name, arguments: a } = block;
    const flag = (reason) => violations.push({ tool: name, reason, detail: JSON.stringify(a).slice(0, 300) });
    if ((name === "read" || name === "write" || name === "edit") && a.path) {
      const p = path.resolve(workspace, a.path);
      if (!p.startsWith(workspace)) flag("path outside workspace");
    }
    if (name === "bash" && typeof a.command === "string") {
      if (/\/(Users|home)\//.test(a.command) && !a.command.includes(workspace)) {
        flag("bash references path outside workspace");
      } else if (/\.\.\//.test(a.command)) {
        flag("bash uses ../ traversal");
      }
    }
  }
}
const audit = {
  runId,
  condition: args.condition,
  model: `${model.provider}/${model.id}`,
  workspace,
  sessionFile,
  toolCalls,
  violations,
  clean: violations.length === 0,
};
fs.writeFileSync(path.join(runDir, "audit.json"), JSON.stringify(audit, null, 2));
console.log(`[run] audit: ${toolCalls} tool calls, ${violations.length} potential violations -> audit.json`);
console.log(`[run] done: ${runDir}`);
