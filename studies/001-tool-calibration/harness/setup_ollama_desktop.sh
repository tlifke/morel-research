#!/usr/bin/env bash
# One-shot Ollama setup script — run on the desktop WSL.
#
# Intended invocation from the laptop:
#   scp harness/setup_ollama_desktop.sh desktop:~/setup_ollama_desktop.sh
#   ssh desktop                            # auto-drops into WSL
#   bash ~/setup_ollama_desktop.sh
#
# What this does:
#   1. Installs Ollama in WSL if missing.
#   2. Configures Ollama to listen on 0.0.0.0:11434 so the laptop can
#      reach it over Tailscale (otherwise it binds 127.0.0.1 only).
#   3. Enables KV-cache quantization to keep VRAM headroom on the
#      RTX 3080 12GB.
#   4. Pulls Gemma 3 4B IT and 12B IT QAT (Q4_0 quantized).
#   5. Smoke-tests each model with a one-token generation.
#
# Idempotent — re-running skips already-completed steps.
#
# NVIDIA driver + CUDA toolkit are assumed pre-installed on the
# Windows host. Inside WSL, Ollama uses the host's GPU via the
# Windows CUDA passthrough. Run `nvidia-smi` first to confirm.

set -euo pipefail

OLLAMA_ENV_DIR="${HOME}/.config/systemd/user"
OLLAMA_OVERRIDE_DIR="/etc/systemd/system/ollama.service.d"

echo "==> Step 1: verify GPU visible from WSL"
if ! command -v nvidia-smi >/dev/null 2>&1; then
    echo "    nvidia-smi not on PATH inside WSL — check WSL CUDA setup before continuing."
    echo "    See https://docs.nvidia.com/cuda/wsl-user-guide/index.html"
    exit 1
fi
nvidia-smi | head -20

echo
echo "==> Step 2: install Ollama if missing"
if command -v ollama >/dev/null 2>&1; then
    echo "    ollama already installed: $(ollama --version)"
else
    curl -fsSL https://ollama.com/install.sh | sh
fi

echo
echo "==> Step 3: configure Ollama to listen on 0.0.0.0 (Tailscale-reachable)"
if [ -d "${OLLAMA_OVERRIDE_DIR}" ] || sudo test -d "${OLLAMA_OVERRIDE_DIR}" 2>/dev/null; then
    sudo mkdir -p "${OLLAMA_OVERRIDE_DIR}"
    sudo tee "${OLLAMA_OVERRIDE_DIR}/override.conf" >/dev/null <<'EOF'
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
Environment="OLLAMA_KV_CACHE_TYPE=q8_0"
Environment="OLLAMA_FLASH_ATTENTION=1"
EOF
    sudo systemctl daemon-reload
    sudo systemctl restart ollama
    echo "    systemd override written; ollama restarted"
else
    echo "    systemd not available; export OLLAMA_HOST=0.0.0.0:11434 manually before launching ollama."
fi

echo
echo "==> Step 4: pull Gemma 3 IT (QAT, Q4_0)"
ollama pull gemma3:4b-it-qat
ollama pull gemma3:12b-it-qat

echo
echo "==> Step 5: smoke test each model"
for model in gemma3:4b-it-qat gemma3:12b-it-qat; do
    echo "    testing ${model}…"
    response="$(ollama run "${model}" --verbose=false 'Reply with exactly the word ok.' 2>&1 || true)"
    echo "    response: $(echo "${response}" | head -1 | head -c 80)"
done

echo
echo "==> Step 6: confirm Tailscale port reachable"
echo "    From the laptop, verify with:"
echo "      curl http://100.97.4.17:11434/api/tags"
echo
echo "All set. Models cached under \$HOME/.ollama/models. Re-run this"
echo "script any time; steps are idempotent."
