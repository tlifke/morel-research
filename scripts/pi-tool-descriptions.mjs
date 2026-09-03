#!/usr/bin/env node
// Regenerates the prose "Available tools:" block that pi's default system
// prompt template builds from each tool's `promptSnippet`, in the same format.
//
// Used by pi-clean (PI_CLEAN_TOOL_DESCRIPTIONS=1) and pi-clean-sdk to make
// tool descriptions an experimental toggle; also runnable standalone:
//
//   node scripts/pi-tool-descriptions.mjs

import path from "node:path";
import { pathToFileURL } from "node:url";

const GLOBAL_ROOT =
  "/Users/tylerlifke/.npm-global/lib/node_modules/@earendil-works/pi-coding-agent";

async function loadToolsModule() {
  try {
    // Deep import: createCodingToolDefinitions is not re-exported at the
    // package top level, and package `exports` may block subpath imports —
    // in that case fall back to the global install path directly.
    return await import("@earendil-works/pi-coding-agent/dist/core/tools/index.js");
  } catch {
    return await import(
      pathToFileURL(path.join(GLOBAL_ROOT, "dist/core/tools/index.js")).href
    );
  }
}

/** Build the "Available tools:" block matching pi's default template format. */
export async function buildToolDescriptions(cwd = process.cwd()) {
  const tools = await loadToolsModule();
  const defs = tools.createCodingToolDefinitions(cwd);
  const list = defs
    .filter((d) => typeof d.promptSnippet === "string" && d.promptSnippet.length > 0)
    .map((d) => `- ${d.name}: ${d.promptSnippet}`)
    .join("\n");
  return `Available tools:\n${list}`;
}

// Run as CLI: print the block.
if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href
) {
  console.log(await buildToolDescriptions());
}
