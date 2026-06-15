import base64
import json
import re
import subprocess
import sys
from pathlib import Path

from judge_casefile import render
from run_api_judge import parse_json

HARNESS = Path(__file__).resolve().parents[1]
PROMPT = (HARNESS / "judges" / "process_judge.md").read_text()
SSH = ["ssh", "-o", "BatchMode=yes", "-o", "RemoteCommand=none", "-o", "RequestTTY=no", "-o", "ConnectTimeout=20", "desktop"]


def ollama_via_ssh(body: str) -> str:
    """Run an ollama /v1 request on the desktop's WSL-localhost (reliable SSH path,
    bypassing the flaky tailnet:11434 portproxy). The base64 body goes via SSH STDIN
    (not the command line) to dodge both shell quoting AND cmd.exe's ~8191-char arg limit."""
    body_b64 = base64.b64encode(body.encode()).decode()
    remote = ('wsl -- bash -c "base64 -d | '
              'curl -s -m 240 http://localhost:11434/v1/chat/completions -H Content-Type:application/json -d @-"')
    r = subprocess.run(SSH + [remote], input=body_b64, capture_output=True, text=True, timeout=300)
    out = r.stdout
    try:
        resp = json.loads(out.strip())
    except Exception:
        m = re.search(r'\{.*"choices".*\}', out, re.DOTALL)
        if not m:
            return ""
        resp = json.loads(m.group(0))
    return (resp.get("choices", [{}])[0].get("message", {}).get("content") or "")


def main():
    run_dir = sys.argv[1]
    model = sys.argv[2] if len(sys.argv) > 2 else "nemotron-3-nano:4b"
    import os
    prompt = PROMPT.replace("{CASEFILE}", render(run_dir))
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}],
                       "reasoning_effort": os.environ.get("RE", "none"),
                       "max_tokens": int(os.environ.get("MAXTOK", "1200")), "temperature": 0.3})
    verdict = parse_json(ollama_via_ssh(body))
    verdict["_judge"] = "nemotron"
    verdict["_run"] = Path(run_dir).name
    outdir = HARNESS / "runs" / "judgments"
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / f"{Path(run_dir).name}__nemotron.json").write_text(json.dumps(verdict, indent=2))
    print(Path(run_dir).name, "pv=" + str(verdict.get("process_verdict")), "parse_err=" + str(verdict.get("_parse_error", False)))


if __name__ == "__main__":
    main()
