"""Render the capability map from tasks.yaml.

Outputs capability-map.png next to this script. Treat the result as a
living figure: it is regenerated whenever tasks.yaml changes.

Usage:
    python3 capability-map/plot.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import yaml

HERE = Path(__file__).resolve().parent
TASKS_PATH = HERE / "tasks.yaml"
OUT_PATH = HERE / "capability-map.png"

STATUS_STYLE = {
    "done":         {"color": "#2a9d8f", "marker": "o", "label": "done"},
    "in-progress":  {"color": "#e9c46a", "marker": "o", "label": "in progress"},
    "hypothesized": {"color": "#264653", "marker": "^", "label": "hypothesized"},
    "human-only":   {"color": "#e76f51", "marker": "s", "label": "human-only"},
    "blocked":      {"color": "#9b2226", "marker": "x", "label": "blocked"},
}


def load_tasks() -> list[dict]:
    with TASKS_PATH.open() as f:
        data = yaml.safe_load(f)
    return data.get("tasks", [])


def render(tasks: list[dict]) -> None:
    fig, ax = plt.subplots(figsize=(10, 8))

    # Quadrant guides.
    ax.axhline(0.5, color="lightgray", linewidth=0.8, zorder=0)
    ax.axvline(0.5, color="lightgray", linewidth=0.8, zorder=0)

    seen_statuses: set[str] = set()
    for task in tasks:
        status = task.get("status", "hypothesized")
        style = STATUS_STYLE.get(status, STATUS_STYLE["hypothesized"])
        x = float(task.get("llm_capability", 0.5))
        y = float(task.get("human_capability", 0.5))
        label = style["label"] if status not in seen_statuses else None
        seen_statuses.add(status)
        ax.scatter(
            x, y,
            c=style["color"], marker=style["marker"], s=120,
            edgecolors="black", linewidths=0.6, zorder=3, label=label,
        )
        ax.annotate(
            task.get("label", task.get("id", "?")),
            (x, y),
            xytext=(6, 4),
            textcoords="offset points",
            fontsize=8,
            zorder=4,
        )

    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    ax.set_xlabel("LLM capability  (0 = infeasible, 1 = trivial)")
    ax.set_ylabel("Human capability  (0 = infeasible, 1 = trivial)")
    ax.set_title("Capability map — research tasks in this repo")

    # Diagonal: where human and LLM capability are equal.
    ax.plot([0, 1], [0, 1], color="lightgray", linestyle="--",
            linewidth=0.8, zorder=0)
    ax.text(0.98, 0.99, "LLM = human", fontsize=7, color="gray",
            ha="right", va="top", rotation=45, zorder=0)

    ax.legend(loc="lower left", framealpha=0.9, fontsize=9)
    ax.grid(False)
    fig.tight_layout()
    fig.savefig(OUT_PATH, dpi=150)
    print(f"wrote {OUT_PATH.relative_to(HERE.parent)}", file=sys.stderr)


def main() -> None:
    tasks = load_tasks()
    if not tasks:
        print("no tasks found in tasks.yaml", file=sys.stderr)
        sys.exit(1)
    render(tasks)


if __name__ == "__main__":
    main()
