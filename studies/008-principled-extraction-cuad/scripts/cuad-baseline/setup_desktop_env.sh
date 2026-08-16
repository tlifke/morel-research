#!/usr/bin/env bash
set -euo pipefail

ROOT="${CUAD_ROOT:-$HOME/Projects/cuad-baseline}"
export PATH="$HOME/.local/bin:$PATH"

mkdir -p "$ROOT" "$ROOT/ckpt"
cd "$ROOT"

if [ ! -d repo ]; then
  git clone --depth 1 https://github.com/TheAtticusProject/cuad.git repo
fi

if [ ! -d .venv ]; then
  uv venv --python 3.10 .venv
fi

uv pip install --python .venv/bin/python \
  torch==1.13.1+cu117 --index-url https://download.pytorch.org/whl/cu117

uv pip install --python .venv/bin/python \
  'transformers==4.12.5' \
  'tokenizers<0.11' \
  'huggingface-hub<0.1' \
  'numpy<2' \
  sentencepiece \
  scikit-learn \
  pandas \
  tqdm \
  tensorboardX \
  protobuf

for f in roberta-base roberta-large deberta-v2-xlarge; do
  if [ ! -f "ckpt/$f.zip" ]; then
    curl -sL -o "ckpt/$f.zip" \
      "https://zenodo.org/api/records/4599830/files/$f.zip/content"
  fi
  if [ ! -d "ckpt/$f" ]; then
    unzip -q -o "ckpt/$f.zip" -d "ckpt/"
  fi
done

.venv/bin/python -c "import torch;print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
