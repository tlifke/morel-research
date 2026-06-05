#!/usr/bin/env bash
set -uo pipefail

EVALPATH="$1"
DATASET="${2:-math}"
WEAK="${3:-Qwen/Qwen1.5-0.5B-Chat}"
STRONG="${4:-Qwen/Qwen3-4B-Base}"
SSH="ssh -o BatchMode=yes -o RemoteCommand=none -o RequestTTY=no -o ConnectTimeout=12 -o ServerAliveInterval=20 desktop"
PY="/home/tlifke/Projects/automated-w2s-research/.venv/bin/python"

read -r -d '' SNIP <<EOF || true
import json, urllib.request
d = json.load(open("$EVALPATH"))
payload = {"predictions": d.get("predictions"), "dataset": "$DATASET", "weak_model": "$WEAK", "strong_model": "$STRONG"}
ti = d.get("test_indices")
if ti is not None:
    payload["test_indices"] = ti
req = urllib.request.Request("http://localhost:8000/api/evaluate-predictions", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
print(urllib.request.urlopen(req, timeout=60).read().decode())
EOF

B64=$(printf '%s' "$SNIP" | base64 | tr -d '\n')
$SSH "wsl -- bash -c \"echo $B64 | base64 -d | $PY\"" 2>&1
