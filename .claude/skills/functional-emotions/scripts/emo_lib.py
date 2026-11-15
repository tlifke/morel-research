"""Shared plumbing for the functional-emotions replication scripts.

Plain Hugging Face `transformers` + PyTorch forward hooks; no TransformerLens /
nnsight dependency, so it works on any decoder-only HF model whose decoder
blocks live in a ModuleList (Llama, Qwen2/3, Gemma 2/3, Mistral, Phi-3,
GPT-NeoX/Pythia, GPT-2, OLMo).

Conventions (keep these consistent across every experiment):
  * "layer l" means the residual stream at the OUTPUT of decoder block l
    (0-indexed). This is what we read and what we steer.
  * Emotion vectors are stored un-normalized in `vectors[l, e, :]`. Probing
    uses the unit vector; steering uses unit vector * strength * mean_norm[l],
    where mean_norm[l] is the average residual-stream L2 norm at layer l over
    a reference dataset (the paper's convention, "steering strengths are given
    relative to the average norm of the residual stream activations").
  * Token position 0 (BOS / first token) is excluded from norm statistics and
    from probe summaries: it is usually an attention-sink outlier with a
    residual norm 10-100x the rest.
"""

from __future__ import annotations

import contextlib
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import torch

# ---------------------------------------------------------------------------
# Model loading / structure
# ---------------------------------------------------------------------------


def load_model(name: str, dtype: str = "bfloat16", device: str | None = None):
    """Load an HF causal LM + tokenizer in eval mode."""
    from transformers import AutoModelForCausalLM, AutoTokenizer

    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    tok = AutoTokenizer.from_pretrained(name)
    # Single-device load (no `accelerate` needed). For models that don't fit on one GPU,
    # pass device_map="auto" here instead and install accelerate.
    model = AutoModelForCausalLM.from_pretrained(name, dtype=getattr(torch, dtype)).to(device)
    model.eval()
    return model, tok


def get_layers(model) -> torch.nn.ModuleList:
    """Return the ModuleList of decoder blocks for common HF architectures."""
    candidates = [
        ("model", "layers"),                    # Llama, Qwen, Mistral, Gemma, OLMo, Phi-3
        ("model", "language_model", "layers"),  # some multimodal wrappers (Gemma 3)
        ("transformer", "h"),                   # GPT-2, GPT-J
        ("gpt_neox", "layers"),                 # Pythia
    ]
    for path in candidates:
        obj = model
        try:
            for p in path:
                obj = getattr(obj, p)
        except AttributeError:
            continue
        if isinstance(obj, torch.nn.ModuleList):
            return obj
    raise ValueError(f"Could not find decoder layers on {type(model).__name__}; add its path to get_layers().")


def get_unembed(model) -> tuple[torch.Tensor, torch.nn.Module | None]:
    """Return (W_U [vocab, d_model], final_norm module or None)."""
    W_U = model.get_output_embeddings().weight
    final_norm = None
    for path in [("model", "norm"), ("model", "language_model", "norm"), ("transformer", "ln_f"), ("gpt_neox", "final_layer_norm")]:
        obj = model
        try:
            for p in path:
                obj = getattr(obj, p)
            final_norm = obj
            break
        except AttributeError:
            continue
    return W_U, final_norm


def n_layers(model) -> int:
    return len(get_layers(model))


def _block_output_tensor(output):
    """Decoder blocks return a tensor (transformers>=5 for many archs) or a tuple."""
    return output[0] if isinstance(output, tuple) else output


def _replace_block_output(output, new_hidden):
    if isinstance(output, tuple):
        return (new_hidden,) + tuple(output[1:])
    return new_hidden


# ---------------------------------------------------------------------------
# Reading activations
# ---------------------------------------------------------------------------


@torch.no_grad()
def residuals(model, input_ids: torch.Tensor, layers: Sequence[int] | None = None,
              attention_mask: torch.Tensor | None = None) -> dict[int, torch.Tensor]:
    """Run a forward pass and return {layer: resid [batch, seq, d_model]} (float32, CPU).

    Uses forward hooks on decoder blocks (not output_hidden_states, because in
    many HF models hidden_states[-1] has the final norm applied, which would
    make the last layer inconsistent with the others).
    """
    blocks = get_layers(model)
    layers = list(range(len(blocks))) if layers is None else list(layers)
    store: dict[int, torch.Tensor] = {}
    handles = []
    for l in layers:
        def hook(_m, _i, out, l=l):
            store[l] = _block_output_tensor(out).detach().float().cpu()
        handles.append(blocks[l].register_forward_hook(hook))
    try:
        model(input_ids=input_ids.to(model.device),
              attention_mask=None if attention_mask is None else attention_mask.to(model.device))
    finally:
        for h in handles:
            h.remove()
    return store


# ---------------------------------------------------------------------------
# Steering
# ---------------------------------------------------------------------------


@dataclass
class Steer:
    """Add `strength * mean_norm[l] * unit(direction[l])` to the residual at layer l.

    positions:
      "all"          every position, including tokens generated later (the
                     paper's blackmail / reward-hacking setting: "steered ...
                     throughout the evaluation").
      "generated"    only positions produced after the prompt (prefill excluded).
      list[int]      absolute token indices in the prompt (e.g. activity tokens
                     for the preference experiment, or the Assistant-turn tokens
                     for the "He feels" test). Generated tokens are not steered.
    """

    directions: dict[int, torch.Tensor]  # layer -> [d_model] (any norm; normalized internally)
    strength: float                      # fraction of mean residual norm; sign = direction
    mean_norm: dict[int, float]          # layer -> mean residual L2 norm
    positions: str | list[int] = "all"
    _handles: list = field(default_factory=list, repr=False)
    _offset: int = field(default=0, repr=False)

    def _make_hook(self, l: int):
        unit = self.directions[l] / self.directions[l].norm()
        delta_full = (self.strength * self.mean_norm[l]) * unit

        def hook(_m, _i, out):
            h = _block_output_tensor(out)
            seq = h.shape[1]
            start = self._offset_by_layer.get(l, 0)
            delta = delta_full.to(device=h.device, dtype=h.dtype)
            if self.positions == "all":
                h = h + delta
            elif self.positions == "generated":
                if start > 0:  # cached decoding step(s) after prefill
                    h = h + delta
            else:
                idx = [p - start for p in self.positions if start <= p < start + seq]
                if idx:
                    h = h.clone()
                    h[:, idx, :] += delta
            self._offset_by_layer[l] = start + seq
            return _replace_block_output(out, h)

        return hook

    def attach(self, model):
        """Register hooks on `model`. Use as: `with Steer(...).attach(model): ...`.

        Position bookkeeping assumes one sequence per call: a prefill pass
        followed by single-token cached decoding steps (what `model.generate`
        does with batch size 1). Re-attach for every new prompt.
        """
        missing = [l for l in self.directions if l not in self.mean_norm]
        if missing:
            raise ValueError(f"mean_norm missing for layers {missing}")
        self._offset_by_layer = {}
        blocks = get_layers(model)
        if self.strength != 0:
            for l in self.directions:
                self._handles.append(blocks[l].register_forward_hook(self._make_hook(l)))
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        for h in self._handles:
            h.remove()
        self._handles.clear()
        return False


def steer_layers(vectors: np.ndarray, emotion_idx: int, layers: Iterable[int]) -> dict[int, torch.Tensor]:
    """Directions dict for one emotion across several layers (vectors: [L, E, d])."""
    return {l: torch.from_numpy(np.asarray(vectors[l, emotion_idx], dtype=np.float32)) for l in layers}


def build_direction(ev: "EmotionVectors", spec: str, layers: Iterable[int],
                    pcs: np.ndarray | None = None) -> dict[int, torch.Tensor]:
    """Parse a direction spec into {layer: direction}. Grammar:

      desperate              the emotion vector
      pc1 / pc2 ...          a principal component of emotion space (needs pcs [L, n, d]
                             from geometry.py; sign: +pc1 ~ positive valence, +pc2 ~ high arousal)
      desperate-calm         difference of two emotion vectors (each unit-normalized first)
      desperate^pc1,pc2      emotion vector with the listed PCs projected out
                             ("what does desperation do beyond valence/arousal?")
      random:7               isotropic Gaussian direction (seed 7). THE essential control:
                             same norm as any other spec, so it tells you how much of an
                             effect is just "perturbing the residual stream at all".

    All directions are returned un-normalized; Steer normalizes them, so strength
    always means "fraction of mean residual norm" regardless of spec.
    """
    def unit(x):
        return x / np.linalg.norm(x)

    def one(l: int, s: str) -> np.ndarray:
        if s.startswith("pc"):
            if pcs is None:
                raise ValueError("pc directions need --pcs (from geometry.py)")
            return pcs[l, int(s[2:]) - 1]
        return ev.vectors[l, ev.idx(s)]

    out = {}
    if spec.startswith("random"):
        seed = int(spec.split(":")[1]) if ":" in spec else 0
        d = ev.vectors.shape[-1]
        for l in layers:  # same random direction at every layer (per seed)
            out[l] = torch.from_numpy(np.random.default_rng(seed).standard_normal(d).astype(np.float32))
        return out
    for l in layers:
        base, _, perp = spec.partition("^")
        if "-" in base and base not in ev.emotions:  # e.g. "worn out" has no '-', "grief-stricken" does
            a, b = base.split("-", 1)
            v = unit(one(l, a)) - unit(one(l, b))
        else:
            v = one(l, base).astype(np.float64)
        if perp:
            if pcs is None:
                raise ValueError("orthogonalizing needs --pcs (from geometry.py)")
            Q, _ = np.linalg.qr(np.stack([pcs[l, int(p.strip()[2:]) - 1] for p in perp.split(",")]).T)
            v = v - Q @ (Q.T @ v)
        out[l] = torch.from_numpy(np.asarray(v, dtype=np.float32))
    return out


# ---------------------------------------------------------------------------
# Generation helpers
# ---------------------------------------------------------------------------


@torch.no_grad()
def generate(model, tok, prompt_ids: torch.Tensor, max_new_tokens: int = 256,
             temperature: float = 1.0, top_p: float = 1.0, steer: Steer | None = None) -> str:
    """Sample a continuation, optionally under steering. Returns decoded new text."""
    ctx = steer.attach(model) if steer is not None else contextlib.nullcontext()
    with ctx:
        out = model.generate(
            input_ids=prompt_ids.to(model.device),
            attention_mask=torch.ones_like(prompt_ids).to(model.device),
            max_new_tokens=max_new_tokens,
            do_sample=temperature > 0,
            temperature=temperature if temperature > 0 else None,
            top_p=top_p if temperature > 0 else None,
            pad_token_id=tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id,
        )
    return tok.decode(out[0, prompt_ids.shape[1]:], skip_special_tokens=True)


# ---------------------------------------------------------------------------
# Prompt formatting and key token positions
# ---------------------------------------------------------------------------


@dataclass
class Formatted:
    ids: torch.Tensor          # [1, seq]
    text: str
    user_end: int | None       # index of last token of the last user message's content
    assistant_colon: int       # index of last prompt token before the assistant's first content token
    spans: dict                # name -> (start_tok, end_tok_exclusive) for any marked substrings


def format_chat(tok, user: str, system: str | None = None, assistant_prefill: str = "",
                mode: str = "auto", mark: dict[str, str] | None = None,
                history: list[dict] | None = None) -> Formatted:
    """Format a single-turn prompt and locate the paper's key token positions.

    mode="chat":   tokenizer chat template with add_generation_prompt=True. The
                   "Assistant colon" analogue is the LAST token of the assistant
                   header (e.g. the "\\n" after "<|im_start|>assistant" for Qwen,
                   the "\\n\\n" after "<|end_header_id|>" for Llama 3). Check it
                   with `describe_positions()` for every new model family.
    mode="paper":  the paper's raw format "Human: {user}\\n\\nAssistant:" -- the
                   colon is literally ":". Use this for base models.
    mode="auto":   "chat" if the tokenizer has a chat template, else "paper".
    mark:          {name: substring} -> token spans of those substrings (first
                   occurrence inside the user message), e.g. the activity text.
    history:       earlier turns [{"role":..., "content":...}] placed before `user`.
    """
    if mode == "auto":
        mode = "chat" if getattr(tok, "chat_template", None) else "paper"
    if mode == "chat":
        msgs = ([{"role": "system", "content": system}] if system else []) + (history or []) + [
            {"role": "user", "content": user}]
        prefix = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    else:
        parts = []
        if system:
            parts.append(system + "\n\n")
        for m in history or []:
            parts.append(("Human: " if m["role"] == "user" else "Assistant: ") + m["content"] + "\n\n")
        parts.append(f"Human: {user}\n\nAssistant:")
        prefix = "".join(parts)
    text = prefix + ((" " if mode == "paper" and assistant_prefill else "") + assistant_prefill)
    enc = tok(text, return_offsets_mapping=True, add_special_tokens=(mode == "paper"))
    ids = torch.tensor([enc["input_ids"]])
    offsets = enc["offset_mapping"]

    def char_to_tok(c: int) -> int:
        """Index of the token containing char c (or the last token starting before c)."""
        best = 0
        for i, (s, e) in enumerate(offsets):
            if s <= c < max(e, s + 1):
                return i
            if s <= c:
                best = i
        return best

    u_start = prefix.rfind(user)
    user_end = char_to_tok(u_start + len(user) - 1) if u_start >= 0 and user else None
    assistant_colon = char_to_tok(len(prefix) - 1)
    # Some tokenizers merge the last header char with following prefill; fall back to last prefix token.
    spans = {}
    for name, sub in (mark or {}).items():
        c = prefix.find(sub, max(u_start, 0))
        if c < 0:
            raise ValueError(f"marked substring {name!r} not found in prompt")
        spans[name] = (char_to_tok(c), char_to_tok(c + len(sub) - 1) + 1)
    return Formatted(ids=ids, text=text, user_end=user_end, assistant_colon=assistant_colon, spans=spans)


def describe_positions(tok, f: Formatted) -> str:
    """Human-readable check that the key positions landed where intended."""
    toks = tok.convert_ids_to_tokens(f.ids[0].tolist())
    lines = [f"user_end        -> {f.user_end}: {toks[f.user_end]!r}" if f.user_end is not None else "user_end -> None",
             f"assistant_colon -> {f.assistant_colon}: {toks[f.assistant_colon]!r}"]
    for k, (s, e) in f.spans.items():
        lines.append(f"span {k:<10} -> [{s},{e}): {toks[s:e]}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Emotion vector files
# ---------------------------------------------------------------------------


@dataclass
class EmotionVectors:
    vectors: np.ndarray        # [L, E, d]  (post-processing: mean-subtracted + neutral-PC-projected)
    raw: np.ndarray | None     # [L, E, d]  mean-subtracted only
    emotions: list[str]
    mean_norm: np.ndarray      # [L]
    meta: dict

    def idx(self, emotion: str) -> int:
        return self.emotions.index(emotion)

    def unit(self, layer: int) -> np.ndarray:
        v = self.vectors[layer]
        return v / np.linalg.norm(v, axis=-1, keepdims=True)

    def save(self, path: str | Path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(path, vectors=self.vectors, raw=self.raw if self.raw is not None else np.zeros(0),
                            emotions=np.array(self.emotions), mean_norm=self.mean_norm,
                            meta=np.array(json.dumps(self.meta)))

    @classmethod
    def load(cls, path: str | Path) -> "EmotionVectors":
        z = np.load(path, allow_pickle=False)
        raw = z["raw"] if z["raw"].size else None
        return cls(z["vectors"], raw, [str(e) for e in z["emotions"]], z["mean_norm"], json.loads(str(z["meta"])))

    def mean_norm_dict(self) -> dict[int, float]:
        return {l: float(x) for l, x in enumerate(self.mean_norm)}


def project_scores(resid: np.ndarray, unit: np.ndarray, kind: str = "dot") -> np.ndarray:
    """resid [..., d] x unit [E, d] -> [..., E]. kind: 'dot' (projection) or 'cos'."""
    s = resid @ unit.T
    if kind == "cos":
        s = s / (np.linalg.norm(resid, axis=-1, keepdims=True) + 1e-8)
    return s


def default_layer(n: int) -> int:
    """The paper's default probe layer: 'about two-thirds of the way through the model'."""
    return int(round(2 * n / 3))


def mid_layers(n: int, width: float = 0.2) -> list[int]:
    """A band of middle layers centred at n/2 (the paper steered preferences at 'middle layers')."""
    lo, hi = int(math.floor(n * (0.5 - width / 2))), int(math.ceil(n * (0.5 + width / 2)))
    return list(range(max(lo, 0), min(hi, n)))


def read_jsonl(path: str | Path) -> list[dict]:
    with open(path) as f:
        return [json.loads(l) for l in f if l.strip()]


def append_jsonl(path: str | Path, rec: dict):
    with open(path, "a") as f:
        f.write(json.dumps(rec) + "\n")
