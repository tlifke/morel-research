import json
import os
import re
import sys
import urllib.request
from pathlib import Path

from judge_casefile import render

HARNESS = Path(__file__).resolve().parents[1]
PROMPT = (HARNESS / "judges" / "process_judge.md").read_text()


def parse_json(text):
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return {"_parse_error": True, "raw": text[:400]}
    try:
        return json.loads(m.group(0))
    except Exception:
        return {"_parse_error": True, "raw": text[:400]}


def call_ollama(prompt, model, url):
    body = {"model": model, "messages": [{"role": "user", "content": prompt}],
            "reasoning_effort": "low", "max_tokens": 1800, "temperature": 0.3}
    req = urllib.request.Request(url.rstrip("/") + "/chat/completions",
                                data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    j = json.load(urllib.request.urlopen(req, timeout=180))
    return j["choices"][0]["message"]["content"] or ""


def call_gemini(prompt, model):
    key = os.environ.get("GEMINI_API_KEY", "")
    u = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 2000}}
    req = urllib.request.Request(u, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    j = json.load(urllib.request.urlopen(req, timeout=180))
    parts = j["candidates"][0]["content"]["parts"]
    return "".join(p.get("text", "") for p in parts)


def main():
    run_dir, which = sys.argv[1], sys.argv[2]  # which = gemini | nemotron
    prompt = PROMPT.replace("{CASEFILE}", render(run_dir))
    if which == "gemini":
        text = call_gemini(prompt, os.environ.get("JUDGE_MODEL", "gemini-3.1-flash-lite"))
    else:
        text = call_ollama(prompt, os.environ.get("JUDGE_MODEL", "nemotron-3-nano:4b"),
                           os.environ.get("OLLAMA_URL", "http://localhost:11434/v1"))
    verdict = parse_json(text)
    verdict["_judge"] = which
    verdict["_run"] = Path(run_dir).name
    outdir = HARNESS / "runs" / "judgments"
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / f"{Path(run_dir).name}__{which}.json").write_text(json.dumps(verdict, indent=2))
    print(json.dumps(verdict, indent=2))


if __name__ == "__main__":
    main()
