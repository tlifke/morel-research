#!/usr/bin/env node
// pi-clean-sdk — minimal pi harness via the SDK, for scripted experiments.
//
// Builds an AgentSession with:
//   - no project context files (AGENTS.md / CLAUDE.md)
//   - no skills, no extensions, no prompt templates
//   - a replacement system prompt (skips the default template and its
//     hardcoded "Be concise in your responses" guideline entirely)
//
// Usage:
//   node scripts/pi-clean-sdk.mjs "your prompt"
//   PI_CLEAN_SYSTEM_PROMPT="..." node scripts/pi-clean-sdk.mjs "your prompt"
//   PI_CLEAN_SESSION_DIR=/tmp/sessions node scripts/pi-clean-sdk.mjs "..."
//   PI_CLEAN_TOOL_DESCRIPTIONS=1 node scripts/pi-clean-sdk.mjs "..."
//
// The resolved system prompt is printed to stderr for verification; the
// assistant's reply streams to stdout.

import { buildToolDescriptions } from "./pi-tool-descriptions.mjs";

// Default: a single space. Truthy for pi's `if (customPrompt)` check (so the
// default template — with "Be concise" — stays off) while saying nothing.
// An empty env value also resolves to " " (|| treats "" as unset), so an
// accidentally empty PI_CLEAN_SYSTEM_PROMPT can never restore the template.
const MINIMAL_SYSTEM_PROMPT = process.env.PI_CLEAN_SYSTEM_PROMPT || " ";

const prompt = process.argv[2];
if (!prompt) {
  console.error('usage: node scripts/pi-clean-sdk.mjs "prompt"');
  process.exit(1);
}

const cwd = process.cwd();

// Same loader path pi-clean uses; import resolved at the bottom via loadPi().
const { loadPi } = await import("./pi-load.mjs");
const pi = await loadPi();

let systemPrompt = MINIMAL_SYSTEM_PROMPT;
if (process.env.PI_CLEAN_TOOL_DESCRIPTIONS === "1") {
  systemPrompt += "\n\n" + (await buildToolDescriptions(cwd));
}

const services = await pi.createAgentSessionServices({
  cwd,
  resourceLoaderOptions: {
    noContextFiles: true,
    noSkills: true,
    noExtensions: true,
    noPromptTemplates: true,
    systemPrompt,
  },
});

for (const d of services.diagnostics) {
  console.error(`[pi-clean-sdk] ${d.type}: ${d.message}`);
}

const sessionManager = pi.SessionManager.create(
  cwd,
  process.env.PI_CLEAN_SESSION_DIR || undefined,
);
const { session } = await pi.createAgentSessionFromServices({
  services,
  sessionManager,
});

// Record the exact system prompt + run config INSIDE the session file at
// startup (pi does not store the system prompt in sessions natively — session
// .jsonl files carry messages only). Custom entries do not participate in LLM
// context, so this is pure metadata that travels with the session through
// forks/resumes/copies.
sessionManager.appendCustomEntry("pi-clean-experiment", {
  recordedAt: new Date().toISOString(),
  piVersion: pi.VERSION,
  systemPrompt: session.systemPrompt,
  systemPromptChars: session.systemPrompt.length,
  model: session.model ? `${session.model.provider}/${session.model.id}` : null,
  toolDescriptionsIncluded: process.env.PI_CLEAN_TOOL_DESCRIPTIONS === "1",
  sessionDir: process.env.PI_CLEAN_SESSION_DIR || null,
});

// Verification: show exactly what system prompt the session will send.
console.error(`[pi-clean-sdk] system prompt (${session.systemPrompt.length} chars):`);
console.error("---8<---");
console.error(session.systemPrompt);
console.error("---8<---");

// Stream assistant text to stdout as messages complete.
session.subscribe((event) => {
  if (event.type === "message_end" && event.message.role === "assistant") {
    for (const part of event.message.content) {
      if (part.type === "text") process.stdout.write(part.text + "\n");
    }
  }
});

await session.prompt(prompt);
