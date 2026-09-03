// Shared loader for the pi SDK: prefers a local dependency, falls back to the
// global npm install. Import from experiment scripts like so:
//
//   const { loadPi } = await import("./pi-load.mjs");
//   const pi = await loadPi();

import path from "node:path";
import { pathToFileURL } from "node:url";

const GLOBAL_ROOT =
  "/Users/tylerlifke/.npm-global/lib/node_modules/@earendil-works/pi-coding-agent";

export async function loadPi() {
  try {
    return await import("@earendil-works/pi-coding-agent");
  } catch {
    return await import(pathToFileURL(path.join(GLOBAL_ROOT, "dist/index.js")).href);
  }
}
