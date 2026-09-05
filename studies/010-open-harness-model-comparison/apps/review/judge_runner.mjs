// judge_runner.mjs — runs one pi-clean judging session (SPEC 5).
//
// Usage: node judge_runner.mjs <workspaceCopyDir> <questionsJsonPath> <modelSpec> <outJsonPath>
//
// Writes outJsonPath: {"ok":bool, "model":str, "session_file":str|null,
//                      "verdicts":{code:{value,evidence}}, "error":str|null}
// The final assistant message must end with a JSON object mapping question
// codes to {"value": ..., "evidence": "..."}. We extract the last JSON block.

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const APP_DIR = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(APP_DIR, "..", "..", "..", "..");

const [workspaceDir, questionsPath, modelSpec, outPath] = process.argv.slice(2);
if (!workspaceDir || !questionsPath || !modelSpec || !outPath) {
  console.error("usage: node judge_runner.mjs <workspaceDir> <questionsJson> <modelSpec> <outJson>");
  process.exit(1);
}

const questions = JSON.parse(fs.readFileSync(questionsPath, "utf-8"));
const [provider, ...rest] = modelSpec.split("/");
const modelId = rest.join("/");

function writeOut(obj) {
  fs.writeFileSync(outPath, JSON.stringify(obj, null, 2));
}

const { loadPi } = await import(pathToFileURL(path.join(REPO_ROOT, "scripts", "pi-load.mjs")).href);
let pi;
try {
  pi = await loadPi();
} catch (e) {
  writeOut({ ok: false, model: modelSpec, session_file: null, verdicts: {}, error: `SDK load failed: ${e}` });
  process.exit(1);
}

let services;
try {
  services = await pi.createAgentSessionServices({
    cwd: workspaceDir,
    resourceLoaderOptions: {
      noContextFiles: true,
      noSkills: true,
      noExtensions: true,
      noPromptTemplates: true,
      systemPrompt: " ",
    },
  });
} catch (e) {
  writeOut({ ok: false, model: modelSpec, session_file: null, verdicts: {}, error: `services failed: ${e}` });
  process.exit(1);
}

const model = services.modelRuntime.getModel(provider, modelId);
if (!model) {
  writeOut({ ok: false, model: modelSpec, session_file: null, verdicts: {}, error: `model not found: ${modelSpec}` });
  process.exit(1);
}

const sessionManager = pi.SessionManager.create(workspaceDir);
const { session } = await pi.createAgentSessionFromServices({
  services,
  sessionManager,
  model,
  thinkingLevel: "high",
});

const qLines = questions
  .map((q) => `- code: ${q.code}\n  question: ${q.text}\n  answer type: ${q.value_type === "bool" ? "true/false" : q.value_type === "int_1_5" ? "integer 1-5" : "text"}`)
  .join("\n");

const prompt = `You are judging an application that an AI agent built in this directory (you are currently in it).

Answer the following questions about it. For each question, you must ACTUALLY TRY — read the documentation files, and launch the application yourself by running commands. Do not claim something works without having run it. If launching per the documentation fails, try other reasonable means and record that honestly.

Questions:
${qLines}

Rules:
- Every command you run and its outcome counts as evidence. Be precise about what you ran and what happened.
- If the documentation does not explain how to launch, say so for the docs question.
- If the application does not launch at all after honest attempts, answer false and explain what you tried.
- Judge only from what is in this directory; do not access files outside it.

When you are done, write your verdict to the file VERDICT.json in the current directory (using the write tool) with exactly this shape:
{"verdicts": {"<question_code>": {"value": <true|false|1-5|text>, "evidence": "<commands run and observed outcomes>"}}, "summary": "<one-line overall assessment>"}
Escape quotes inside evidence strings properly. After writing VERDICT.json, your final message should just be the word DONE.`;

const finalTexts = [];
session.subscribe((event) => {
  if (event.type === "message_end" && event.message.role === "assistant") {
    for (const part of event.message.content) {
      if (part.type === "text") finalTexts.push(part.text);
    }
  }
});

let sessionFile = null;
try {
  await session.prompt(prompt);
  const candidates = fs.readdirSync(workspaceDir).filter((f) => f.endsWith(".jsonl"));
  // session manager may write next to cwd or in default location; find newest jsonl in temp dir tree
  const found = [];
  const walk = (dir) => {
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      const p = path.join(dir, e.name);
      if (e.isDirectory()) walk(p);
      else if (e.name.endsWith(".jsonl")) found.push(p);
    }
  };
  walk(workspaceDir);
  sessionFile = found.sort().pop() ?? null;
  void candidates;
} catch (e) {
  writeOut({ ok: false, model: `${model.provider}/${model.id}`, session_file: null, verdicts: {}, error: `session failed: ${e}` });
  process.exit(1);
}

const fullText = finalTexts.join("\n");
let verdicts = {};
let summary = "";
let parseSource = "";

// Strategy 1: the agent was asked to write VERDICT.json (write-tool argument
// escaping is structural, so this is the reliable path).
const verdictFile = path.join(workspaceDir, "VERDICT.json");
if (fs.existsSync(verdictFile)) {
  try {
    const parsed = JSON.parse(fs.readFileSync(verdictFile, "utf-8"));
    verdicts = parsed.verdicts ?? {};
    summary = parsed.summary ?? "";
    parseSource = "VERDICT.json";
  } catch { /* fall through */ }
}

// Strategy 2: balanced-brace scan of the final message (last { backwards).
if (!parseSource) {
  const positions = [];
  for (let i = fullText.length - 1; i >= 0; i--) if (fullText[i] === "{") positions.push(i);
  for (const start of positions) {
    const candidate = balancedBlock(fullText, start);
    if (candidate === null) continue;
    try {
      const obj = JSON.parse(candidate);
      if (obj && typeof obj === "object" && obj.verdicts) {
        verdicts = obj.verdicts;
        summary = obj.summary ?? "";
        parseSource = "final message (balanced scan)";
        break;
      }
    } catch { /* try next position */ }
  }
}

// Strategy 3: per-question salvage regex (tolerates malformed outer JSON).
if (!parseSource) {
  for (const q of questions) {
    const re = new RegExp(`"${q.code}"\\s*:\\s*\\{([\\s\\S]{0,4000}?)\\}(?=\\s*[,}])`);
    const m = fullText.match(re);
    if (!m) continue;
    try {
      const obj = JSON.parse(`{"${q.code}": {${m[1]}}}`);
      if (obj[q.code]) { verdicts[q.code] = obj[q.code]; continue; }
    } catch { /* fallthrough to value regex */ }
    const vm = m[1].match(/"value"\s*:\s*(true|false|\d+)/);
    if (vm) verdicts[q.code] = { value: JSON.parse(vm[1]), evidence: "(salvaged from malformed JSON)" };
  }
  if (Object.keys(verdicts).length > 0) parseSource = "salvage regex";
}

if (!parseSource) {
  writeOut({
    ok: false,
    model: `${model.provider}/${model.id}`,
    session_file: sessionFile,
    verdicts: {},
    error: `no verdict found (VERDICT.json absent, no parseable JSON in final message). Final text: ${fullText.slice(-800)}`,
  });
  process.exit(1);
}

// Returns the substring from `start` through its matching closing brace
// (string-aware), or null if unbalanced.
function balancedBlock(text, start) {
  let depth = 0, inString = false, escape = false;
  for (let i = start; i < text.length; i++) {
    const ch = text[i];
    if (inString) {
      if (escape) escape = false;
      else if (ch === "\\") escape = true;
      else if (ch === '"') inString = false;
      continue;
    }
    if (ch === '"') inString = true;
    else if (ch === "{") depth++;
    else if (ch === "}") {
      depth--;
      if (depth === 0) return text.slice(start, i + 1);
    }
  }
  return null;
}

writeOut({
  ok: true,
  model: `${model.provider}/${model.id}`,
  session_file: sessionFile,
  verdicts,
  summary,
  error: null,
});
