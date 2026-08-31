import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { readFile } from "node:fs/promises";
import { extname, resolve } from "node:path";

const HF_ROUTER =
  process.env.HF_ROUTER_URL ?? "https://router.huggingface.co/v1/chat/completions";
const HF_MODELS =
  process.env.HF_MODELS_URL ?? "https://router.huggingface.co/v1/models";

const MIME: Record<string, string> = {
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".gif": "image/gif",
  ".webp": "image/webp",
};

let visionCache: Set<string> | undefined;

async function visionModels(token: string, signal: AbortSignal): Promise<Set<string> | undefined> {
  if (visionCache) return visionCache;
  try {
    const res = await fetch(HF_MODELS, {
      signal,
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) return undefined;
    const data = await res.json();
    const ids = (data?.data ?? [])
      .filter((m: any) => (m?.architecture?.input_modalities ?? []).includes("image"))
      .map((m: any) => m.id);
    visionCache = new Set(ids);
    return visionCache;
  } catch {
    return undefined;
  }
}

async function buildImagePart(imagePath: string) {
  const abs = resolve(imagePath);
  const mime = MIME[extname(abs).toLowerCase()];
  if (!mime) {
    throw new Error(`Unsupported image type '${extname(abs)}' (need png/jpg/gif/webp)`);
  }
  const b64 = (await readFile(abs)).toString("base64");
  return { type: "image_url", image_url: { url: `data:${mime};base64,${b64}` } };
}

const DEFAULT_MODELS = [
  "Qwen/Qwen3.8-27B",
  "deepseek-ai/DeepSeek-V4-Pro",
  "thinkingmachines/Inkling-Small",
];

type Answer = { model: string; answer: string; ok: boolean; truncated?: boolean };

const MIN_TOKENS = 2048;
const RETRY_STATUS = new Set([408, 425, 429, 500, 502, 503, 504]);
const MAX_ATTEMPTS = 3;
const REQUEST_TIMEOUT_MS = 120_000;

const sleep = (ms: number, signal: AbortSignal) =>
  new Promise<void>((res, rej) => {
    const t = setTimeout(res, ms);
    signal.addEventListener("abort", () => { clearTimeout(t); rej(new Error("aborted")); }, { once: true });
  });

function firstNonBlank(...vals: unknown[]): string | undefined {
  for (const v of vals) {
    if (typeof v === "string" && v.trim() !== "") return v.trim();
  }
  return undefined;
}

async function askModel(
  model: string,
  question: string,
  token: string,
  maxTokens: number,
  signal: AbortSignal,
  imageParts?: unknown[],
): Promise<Answer> {
  let lastTransient = "";
  for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
  try {
    const res = await fetch(HF_ROUTER, {
      method: "POST",
      signal: AbortSignal.any([signal, AbortSignal.timeout(REQUEST_TIMEOUT_MS)]),
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model,
        messages: [
          {
            role: "user",
            content: imageParts?.length
              ? [{ type: "text", text: question }, ...imageParts]
              : question,
          },
        ],
        max_tokens: maxTokens,
      }),
    });

    const raw = await res.text();
    if (!res.ok) {
      const detail = `HTTP ${res.status}: ${raw.slice(0, 300)}`;
      if (RETRY_STATUS.has(res.status) && attempt < MAX_ATTEMPTS) {
        lastTransient = detail;
        await sleep(1000 * 2 ** (attempt - 1), signal);
        continue;
      }
      return { model, answer: detail, ok: false };
    }

    const data = JSON.parse(raw);
    const choice = data?.choices?.[0];
    if (!choice) {
      const apiErr = data?.error?.message ?? data?.error;
      return {
        model,
        answer: apiErr ? `API error: ${apiErr}` : `Unexpected response: ${raw.slice(0, 400)}`,
        ok: false,
      };
    }

    const msg = choice.message;
    const reason = choice.finish_reason ?? "unknown";
    const answer = firstNonBlank(msg?.content);
    if (answer) return { model, answer, ok: true, truncated: reason === "length" };

    const thinking = firstNonBlank(msg?.reasoning_content, msg?.reasoning);
    if (thinking) {
      return {
        model,
        answer:
          reason === "length"
            ? `[truncated: budget consumed by reasoning, no final answer emitted]\n\n${thinking}`
            : thinking,
        ok: reason !== "length",
        truncated: reason === "length",
      };
    }

    return { model, answer: `Empty response (finish_reason=${reason})`, ok: false };
  } catch (e: any) {
    if (signal.aborted) return { model, answer: "Cancelled", ok: false };
    const timedOut = e?.name === "TimeoutError" || e?.name === "AbortError";
    const detail = timedOut
      ? `Timed out after ${REQUEST_TIMEOUT_MS / 1000}s`
      : `${e?.name ?? "Error"}: ${e?.message ?? String(e)}`;
    if (attempt < MAX_ATTEMPTS) {
      lastTransient = detail;
      try {
        await sleep(1000 * 2 ** (attempt - 1), signal);
      } catch {
        return { model, answer: "Cancelled", ok: false };
      }
      continue;
    }
    return { model, answer: detail, ok: false };
  }
  }
  return {
    model,
    answer: `Failed after ${MAX_ATTEMPTS} attempts. Last error: ${lastTransient}`,
    ok: false,
  };
}

export default function (pi: ExtensionAPI) {
  pi.registerCommand("survey-llm", {
    description: "Survey 3 HF models. Usage: /survey-llm what are best practices?",
    handler: async (args, ctx) => {
      const q = args?.trim();
      if (!q) {
        ctx.ui.notify("Usage: /survey-llm <question>", "warning");
        return;
      }
      await ctx.sendUserMessage(
        `Use the survey_llms tool to ask each model this question, then summarize where they agree and disagree:\n\n${q}`,
      );
    },
  });

  pi.registerTool({
    name: "survey_llms",
    label: "Survey LLMs",
    description:
      "Ask the same question to several Hugging Face router models and collect their answers side by side.",
    parameters: Type.Object({
      question: Type.String(),
      models: Type.Optional(Type.Array(Type.String())),
      maxTokens: Type.Optional(Type.Number()),
      imagePath: Type.Optional(
        Type.String({ description: "Local path to a png/jpg/gif/webp to send with the question." }),
      ),
      imagePaths: Type.Optional(
        Type.Array(Type.String(), {
          description: "Several local images to send together, e.g. tiles of one tall page.",
        }),
      ),
    }),
    async execute(toolCallId, params, signal, onUpdate, ctx) {
      const token = process.env.HF_TOKEN;
      if (!token) {
        return {
          content: [
            {
              type: "text",
              text: "HF_TOKEN is not set in this process. Export it before launching pi (pi does not read .env).",
            },
          ],
          isError: true,
          details: {},
        };
      }

      const models = params.models?.length ? params.models : DEFAULT_MODELS;
      const requested = params.maxTokens ?? 2048;
      const maxTokens = Math.max(requested, MIN_TOKENS);
      const notes: string[] = [];
      if (maxTokens !== requested) {
        notes.push(
          `maxTokens raised ${requested} -> ${maxTokens}; these are reasoning models and reasoning tokens share the budget.`,
        );
      }

      onUpdate?.({
        content: [{ type: "text", text: `Querying ${models.length} models...` }],
      });

      const paths = [
        ...(params.imagePath ? [params.imagePath] : []),
        ...(params.imagePaths ?? []),
      ];
      let imageParts: unknown[] = [];
      let capable: Set<string> | undefined;
      if (paths.length) {
        try {
          imageParts = await Promise.all(paths.map(buildImagePart));
        } catch (e: any) {
          return {
            content: [{ type: "text", text: `Could not read image: ${e.message}` }],
            isError: true,
            details: {},
          };
        }
        if (paths.length > 1) notes.push(`Sending ${paths.length} images per model.`);
        capable = await visionModels(token, signal);
        if (!capable) notes.push("Could not fetch model modalities; sending images to every model.");
      }

      const results = await Promise.all(
        models.map(async (m) => {
          const sendImage = imageParts.length > 0 && (!capable || capable.has(m));
          if (imageParts.length > 0 && capable && !capable.has(m)) {
            return {
              model: m,
              answer: "Skipped: model is text-only and cannot accept an image.",
              ok: false,
            } as Answer;
          }
          let r = await askModel(
            m,
            params.question,
            token,
            maxTokens,
            signal,
            sendImage ? imageParts : undefined,
          );
          if (r.truncated && !signal.aborted) {
            const retryTokens = maxTokens * 2;
            notes.push(`${m}: truncated at ${maxTokens}, retried at ${retryTokens}.`);
            const retry = await askModel(
              m,
              params.question,
              token,
              retryTokens,
              signal,
              sendImage ? imageParts : undefined,
            );
            if (retry.ok) r = retry;
          }
          return r;
        }),
      );

      const failed = results.filter((r) => !r.ok).length;
      const summary = `${results.length - failed}/${results.length} models answered`;
      const header = notes.length ? `${summary}\n${notes.join("\n")}` : summary;

      return {
        content: [
          { type: "text", text: `${header}\n\n${JSON.stringify({ results }, null, 2)}` },
        ],
        details: { summary, failed, notes },
      };
    },
  });
}
