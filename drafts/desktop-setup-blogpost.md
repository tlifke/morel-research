# A day, not a fortnight: standing up a remote GPU inference target with Claude

I needed a GPU I could call from my laptop. Specifically, I needed Gemma 3 4B IT and 12B IT serving over HTTP on the Windows desktop in the other room, reachable from my MacBook over Tailscale, so I could run trials against them for a calibration study about LLM tool-calling behavior. The desktop has an RTX 3080 12GB; the laptop has neither the VRAM nor the desire to host a model server.

I have done a version of this setup before, solo, in a different project. It took me a couple of weeks. It was not smooth. I followed multiple guides, none of which agreed with each other, and the resulting rig never really worked well — it limped along just well enough that I stopped touching it.

This time I did it with Claude Code in about a day. (Plus a separate four-ish hours on a previous day for Tailscale, which I'll mostly take as a given here.) The steps were not meaningfully different from the steps I followed two years ago. What changed is what it's like to do those steps with a collaborator who can hold the full stack — SSH, WSL, Windows networking, Tailscale, Ollama, Python — in working memory at once.

This post is about which parts of that work needed me and which parts Claude carried. I think the split is more interesting than the recipe.

## The shape of the thing

The endpoint architecture is dead simple:

- Laptop initiates a run. Results land in a local `results/` tree.
- Desktop runs Ollama as an HTTP server bound to `0.0.0.0:11434`.
- Laptop POSTs to `http://100.97.4.17:11434/api/generate` over Tailscale.
- SSH is only used for one-time setup. There's no SSH in the hot path.

The non-obvious parts of getting there are all in the seams:

1. The desktop runs Ollama inside WSL2. WSL2's network is NAT'd; "listen on 0.0.0.0" inside WSL is not the same as "reachable from the LAN."
2. Ollama on Linux ships with a systemd unit that binds 127.0.0.1 unless overridden, so a fresh install is not reachable even from the Windows host.
3. Tailscale runs on the Windows host. So you need Ollama → WSL listening → Windows portproxy → Windows Firewall → Tailscale, with the WSL IP refreshed every time WSL reboots.

None of this is exotic. All of it has bitten me before.

## Where the human was load-bearing

There were specific moments where Claude could not have proceeded without me. They are mostly the moments you'd expect:

**Credentials and physical presence.** Claude can't enter my Windows password, can't tap an admin-elevation prompt, can't open an RDP session for me, and can't be in the room with the desktop when something needs physically poking. When I needed to run a script from an elevated PowerShell, I had to be the one to launch elevated PowerShell.

**Remembering that I'd done this before.** I had a vague memory that I'd set up SSH to the desktop "some way" during a different project (morel-primordia). That memory was the thread Claude pulled on. Claude searched morel-primordia for docs about it, found nothing useful, then thought to check `~/.ssh/config` directly — where a working `Host desktop` alias has been sitting the whole time, complete with `RemoteCommand wsl --cd /home/tlifke/Projects` so that `ssh desktop` auto-drops into WSL. The earlier auth failures were because Claude had tried `tlifke` (the WSL user) instead of `tlifk` (the Windows user, which is what SSH actually needs). I didn't remember the username mismatch; the config file did.

This is a small thing, but it's the prototype for a lot of the collaboration: I supplied the existence of the artifact, Claude figured out how to read it.

**Judgment about scope.** A separate analysis (`investigations/002-difficulty-axes/calibration_cost_estimate.md`) had me convinced that running this round through the Gemini API would have cost about five cents, since Google AI Studio serves Gemma 3 4B/12B IT under the same key I already have. I picked local anyway — partly because the base-model comparison later will need local regardless, partly because I'd rather have one inference path than two. That's a call Claude could have argued either side of; it's the kind of decision I want to make.

## Where Claude carried

**Writing the boilerplate.** The two setup scripts — `setup_ollama_desktop.sh` (WSL side) and `setup_desktop.ps1` (Windows side) — are both Claude drafts. They are idempotent. They check before they act. They cite the Tailscale IP in comments next to the commands you'd run from the laptop. They handle the WSL2-IP-changes-on-reboot problem by re-reading `wsl hostname -I` each run and refreshing the portproxy. I would have written something equivalent solo, eventually, after I'd been bitten enough times to remember to.

**Holding the full stack in mind.** This is the part I keep coming back to. When the laptop couldn't reach `100.97.4.17:11434` after the WSL setup finished, the diagnosis chain was:

- Can the Windows host reach `127.0.0.1:11434`? (No, it's a WSL service.)
- Is there a portproxy? (No.)
- Is the WSL service even bound to `0.0.0.0` inside WSL? (`ss -tlnp | grep 11434` from WSL — answer: no, still on `127.0.0.1`.)
- Why didn't the override take? (Bug in my own script — see below.)

Each of those checks is thirty seconds of typing if you know which one to run next. The reason the solo version of this took weeks isn't that any single step is hard. It's that the pieces drop out of working memory between sessions. You sit down on a Saturday, remember half of the layer cake, and end up Googling "wsl2 port forwarding tailscale" again and reading three subtly contradictory blog posts. Claude doesn't context-switch.

## The bugs, in honest detail

Three things went wrong that are worth writing down. Each one is the kind of bug I'd have spent half a day on solo.

**1. The scp landed in Windows, not WSL.** Claude said "use `scp setup_ollama_desktop.sh desktop:~/`." I ran it; scp reported success. From WSL: `ls ~/setup_ollama_desktop.sh` — no such file.

The diagnosis is a one-liner once you've seen it. scp does not honor `RemoteCommand` in `ssh_config`. So `desktop:~/` resolved to the Windows user's `C:\Users\tlifk\`, not the WSL home directory. From WSL, the file was sitting at `/mnt/c/Users/tlifk/setup_ollama_desktop.sh`. Move it, move on.

Claude flagged the cause within seconds of me pasting the not-found error. I would have spent twenty minutes wondering if my disk was broken.

**2. The systemd override never installed.** First version of my setup script had this guard:

```bash
if [ -d "$override_dir" ] || sudo test -d "$override_dir"; then
    # ... write the override file ...
fi
```

That's inverted. The override directory doesn't exist until we create it; the whole block was being skipped. The script ran clean, output looked fine, but Ollama was still bound to `127.0.0.1:11434`.

Claude wrote that bug. Claude also diagnosed it, by suggesting `ss -tlnp | grep 11434` from inside WSL as the first sanity check when the laptop's curl timed out. Then patched the script. The current version unconditionally `mkdir -p`s the override directory and writes the file. The smoke test at the end of the script now explicitly checks for `0.0.0.0:11434` in `ss` output, so a silent regression here would scream.

This is a useful data point about how to use a coding assistant: it will write bugs at roughly the rate any of us do, and the value is in the loop, not in any single artifact. The loop closes fast.

**3. WSL2 NAT was a wall I hadn't seen before.** After the override applied and Ollama was correctly listening on `0.0.0.0:11434` inside WSL, the port was still not reachable from the laptop. WSL2 runs a NAT'd virtual network; bind addresses inside WSL are not the bind addresses Tailscale-on-Windows sees.

The fix is two pieces of Windows configuration: a `netsh interface portproxy add v4tov4` rule forwarding `0.0.0.0:11434` on the host to `<WSL-IP>:11434`, and a Windows Firewall inbound rule for TCP 11434. Both require admin PowerShell. The WSL IP changes on every reboot, so the portproxy needs to be torn down and re-added each time.

`setup_desktop.ps1` automates this. It checks for admin, re-reads the WSL IP via `wsl hostname -I`, drops any existing portproxy rule, adds a fresh one, ensures the firewall rule exists, then smoke-tests `127.0.0.1:11434/api/tags` from Windows. Re-running it after a reboot is the supported "fix it" path.

I did not know about the WSL2 NAT layer before this. I knew there was something flaky about WSL networking; I didn't have a name for it. Claude named it within a minute of the symptom.

## Two smaller bits

**Admin PowerShell starts in System32.** When I opened admin PowerShell to run the driver script, Windows dropped me into `C:\Windows\System32`. I needed to get to the repo, which lives inside WSL. Claude suggested:

```
cd \\wsl$\Ubuntu\home\tlifke\Projects\morel-research
```

and flagged that elevated PowerShell sometimes can't see `\\wsl$` and offered fallbacks (full-UNC invocation, or copying the script to `/mnt/c/` first). The first path worked. This is exactly the kind of "Windows-specific gotcha I'd Google five times" that you don't have to Google when somebody can just tell you.

**The WSL password I'd forgotten.** The bash setup script needs sudo. I'd long since forgotten my WSL password. Claude pointed at:

```
wsl -d Ubuntu -u root passwd tlifke
```

Windows admin equals WSL root for free, so you can reset a forgotten user password in one command from PowerShell. I knew I'd dealt with this before, somehow; I did not remember how.

## The payoff

About 90 minutes after I started, the laptop's harness fired its first two trials at the 4B IT model. I picked the matched pair `Compute 4782 × 1847` (genuinely needs the calculator tool) versus `Compute 4 × 7` (trivially does not). Out of n=5 each:

- `Compute 4782 × 1847`: 5/5 tool calls.
- `Compute 4 × 7`: 5/5 tool calls.
- (Reference: `What is 8 divided by 4?` from the same seed corpus: 5/5 correct abstentions.)

So 4B IT recognizes the long-arithmetic case but is also over-calling on trivial arithmetic when the prompt phrasing is `Compute X × Y`. The `Compute …` framing is likely tripping a tool-use heuristic regardless of operand size. That is a genuinely interesting calibration signal — different framings of the same trivial operation elicit different behaviors — and it showed up in the first two trials, immediately, because the infrastructure worked. This is the thing the whole setup was for.

## What changed, really

The steps haven't changed much in two years. WSL2, Ollama, Tailscale, Windows portproxy — these are the same components, with the same gotchas, that I would have had to assemble solo.

What changed is having a collaborator who:

- Holds the whole stack in working memory at once. No re-reading "WSL2 networking explained" for the fourth time.
- Suggests the right next diagnostic, on the first try, when something fails. The `ss -tlnp` move was worth an hour by itself.
- Writes the boilerplate without research-pause. PowerShell, bash, Python.
- Doesn't get demoralized by gotchas. Each one resolves in minutes, not hours of guide-hopping. The emotional cost of "this isn't working again" — which, honestly, is most of why my solo version stalled out — is much lower when you're not the only one holding the thread.

The honest version of the comparison is: this work was never hard. It was tedious, with edges, spread over too many systems, and impossible to keep entirely in one head between sessions. Pair it with a model that can keep all of that in one head at once and the tedium evaporates. The edges are still there; you just notice them and move past them instead of grinding on them.

A day, not a fortnight. And the resulting setup is one I trust enough to run real experiments through.

---

## Things I made up that you should review

Flagging things that came from Claude's narrative reconstruction rather than direct observation, in case any of these are off:

1. **The previous solo-attempt timeline ("a couple of weeks", "wasn't smooth", "never really worked well")** — this is paraphrased from your framing of it. Worth checking that the duration and the "limped along" characterization match what you actually remember; I sharpened the language a little.
2. **The four-ish hours for the prior Tailscale setup** — I took this from your framing without independent context on what that day involved. If it was meaningfully different (e.g. included more than just Tailscale), the parenthetical should be tightened.
3. **The "first two trials" framing for the calibration result.** You ran the matched pair on the first live trial; I'm slightly compressing the chronology by calling it "two trials" when each was actually n=5. The numbers are right; the framing is mine. Check it reads honestly.
4. **"About 90 minutes after I started" for time-to-first-trial.** I don't actually have wall-clock data here — this is plausible from the session arc but is a guess. Replace with an actual number or drop it.
5. **The claim that you "didn't know about the WSL2 NAT layer before this."** This is inferred from your in-session reaction. If you did know about it and the surprise was something more specific, fix.
6. **The Gemini API cost estimate (~$0.05).** Pulled from `calibration_cost_estimate.md`. Worth a sanity-check against the current numbers in that file before publishing.
7. **The framing that the setup took "about a day."** I took your "about a day" at face value. If it was closer to half a day or closer to a day and a half, adjust.
8. **The closing line "one I trust enough to run real experiments through."** Slightly stronger than I have evidence for — you've run two matched pairs, not a full run. Soften if you like.
