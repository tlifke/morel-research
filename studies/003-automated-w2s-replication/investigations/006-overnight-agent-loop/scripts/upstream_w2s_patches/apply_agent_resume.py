#!/usr/bin/env python3
"""inv 006: add resume + SIGTERM handling to upstream
AutonomousAgentLoop (w2s_research/research_loop/agent.py).

Two behaviors:

1. **HANDOFF_RESUME=1**: on init, find highest `iteration_NN.yaml` in
   `$WORKSPACE/.agent_handoff/`, set `session_count = N+1`, prime
   `self._prompt` with `make_bootstrap_message(latest, N, prior_state)`.
   So the next launch picks up exactly where the prior one left off.

2. **SIGTERM handler**: register a handler that sets
   `self._should_stop_after_session = True`. The run loop checks the
   flag after each `_run_session()` completes and breaks cleanly with
   `StopReason.USER_INTERRUPT`. SIGTERM mid-Bash kills the SFT
   subprocess and loses that iteration's work — but durable state
   from prior iterations is intact.

Edits are idempotent — re-running on already-patched source is a no-op.

Apply on desktop with:

    /home/tlifke/Projects/automated-w2s-research/.venv/bin/python \\
        <morel-research>/studies/003-automated-w2s-replication/investigations/\\
        006-overnight-agent-loop/scripts/upstream_w2s_patches/apply_agent_resume.py
"""
from __future__ import annotations
from pathlib import Path

AGENT_PY = Path(
    "/home/tlifke/Projects/automated-w2s-research/"
    "w2s_research/research_loop/agent.py"
)


def patch() -> bool:
    src = AGENT_PY.read_text()
    if "_should_stop_after_session" in src:
        print("[agent.py] already patched")
        return False

    old_init_tail = (
        "        self.session_count = 0\n"
        "        self._prompt: Optional[str] = None\n"
    )
    new_init_tail = (
        "        self.session_count = 0\n"
        "        self._prompt: Optional[str] = None\n"
        "\n"
        "        # inv 006: graceful SIGTERM at next session boundary.\n"
        "        self._should_stop_after_session = False\n"
        "        try:\n"
        "            import signal as _signal\n"
        "            def _on_sigterm(_signum, _frame):\n"
        "                print(\"\\n[Loop] SIGTERM — will stop after current session boundary\", flush=True)\n"
        "                self._should_stop_after_session = True\n"
        "            _signal.signal(_signal.SIGTERM, _on_sigterm)\n"
        "        except Exception as _e:\n"
        "            print(f\"[Init] Warning: SIGTERM handler not registered: {_e}\")\n"
        "\n"
        "        # inv 006: resume from existing handoff yaml(s) if requested.\n"
        "        if os.environ.get(\"HANDOFF_RESUME\") == \"1\" and _HAND_AVAILABLE:\n"
        "            try:\n"
        "                handoff_dir = self.workspace / \".agent_handoff\"\n"
        "                if handoff_dir.exists():\n"
        "                    yamls = sorted(handoff_dir.glob(\"iteration_*.yaml\"))\n"
        "                    if yamls:\n"
        "                        latest = yamls[-1]\n"
        "                        n_str = latest.stem.split(\"_\")[-1]\n"
        "                        try:\n"
        "                            n = int(n_str)\n"
        "                        except ValueError:\n"
        "                            n = len(yamls) - 1\n"
        "                        prior_state = _hand_read(latest)\n"
        "                        self.session_count = n + 1\n"
        "                        self._prompt = _hand_bootstrap(\n"
        "                            latest, n, prior_state=prior_state\n"
        "                        )\n"
        "                        print(\n"
        "                            f\"[Resume] Found {len(yamls)} prior iteration(s); \"\n"
        "                            f\"continuing at session {self.session_count} \"\n"
        "                            f\"with bootstrap from {latest.name}\",\n"
        "                            flush=True,\n"
        "                        )\n"
        "            except Exception as _e:\n"
        "                print(f\"[Resume] Warning: resume failed, starting fresh: {_e}\", flush=True)\n"
    )
    if old_init_tail not in src:
        raise SystemExit("[agent.py] init-tail anchor missing")
    src = src.replace(old_init_tail, new_init_tail)

    old_imp = (
        "    from handoff_writer import (\n"
        "        extract_iteration_state as _hand_extract,\n"
        "        write_handoff as _hand_write,\n"
        "        make_bootstrap_message as _hand_bootstrap,\n"
        "    )"
    )
    new_imp = (
        "    from handoff_writer import (\n"
        "        extract_iteration_state as _hand_extract,\n"
        "        write_handoff as _hand_write,\n"
        "        make_bootstrap_message as _hand_bootstrap,\n"
        "        read_handoff as _hand_read,\n"
        "    )"
    )
    if old_imp not in src:
        raise SystemExit("[agent.py] handoff import anchor missing")
    src = src.replace(old_imp, new_imp)

    old_loop = (
        "            try:\n"
        "                await self._run_session()\n"
        "                self.session_count += 1\n"
        "                self.stop_checker.record_success()\n"
        "                if not self.local_mode:\n"
        "                    await self._sync_to_s3()\n"
        "\n"
        "            except KeyboardInterrupt:"
    )
    new_loop = (
        "            try:\n"
        "                await self._run_session()\n"
        "                self.session_count += 1\n"
        "                self.stop_checker.record_success()\n"
        "                if not self.local_mode:\n"
        "                    await self._sync_to_s3()\n"
        "                if self._should_stop_after_session:\n"
        "                    print(\"[Loop] Clean stop after session boundary (SIGTERM).\", flush=True)\n"
        "                    stop_reason = StopReason.USER_INTERRUPT\n"
        "                    break\n"
        "\n"
        "            except KeyboardInterrupt:"
    )
    if old_loop not in src:
        raise SystemExit("[agent.py] run-loop anchor missing")
    src = src.replace(old_loop, new_loop)

    AGENT_PY.write_text(src)
    print("[agent.py] patched: SIGTERM handler + HANDOFF_RESUME support")
    return True


if __name__ == "__main__":
    patch()
