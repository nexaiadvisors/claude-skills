---
name: to-chips
description: "Routes each unit of work between fresh background agent sessions (chips - each in its own git worktree, auto-merged and tested when done) and the current session, then runs both lanes. Use for 'chip this', 'offload this', 'hand this off to a new session', 'run this in a fresh session', 'split this up and get it done', or when context runs low."
argument-hint: "[task description | done | watch | status]"
license: "MIT"
compatibility: "Needs git 2.31+ (worktrees) and a POSIX shell. The one-click chip lane needs a host tool that launches a background agent session; without one the skill falls back to manual worktrees, which run the identical protocol. Notifications and auto-watch are optional and degrade with a stated message."
metadata:
  version: "1.0.0"
---

# To Chips

## Overview

**A chip is one unit of work handed to a fresh agent session that runs in its own git worktree, commits on its own branch, and reports completion by writing a file on disk.** Nothing about a chip is magic: it is a prompt, a worktree, a branch, and a JSON result file. Chips are launched, not executed — they start when the user starts them.

This skill takes a task, **routes each unit of it to the lane that can actually execute it**, and then runs both lanes: chips (background sessions) and inline (this session). Most work is chipped; a minority structurally cannot be, and that minority is executed here rather than faked into a chip that will fail.

**Lean toward chipping, but route on judgment — and when a unit is a bad fit for a chip, just do it.** Chips exist to buy back context and run work unattended in parallel. When that is what the unit needs, chip it, and do not talk yourself out of it because the work looks small. When it is not — the unit needs live access you have and a chip does not, or an exclusive resource, or the user's judgment turn by turn — forcing it into a chip produces a session that stalls or guesses. Handle it here instead. Both outcomes are correct results for this skill, not failures of it.

The routing is per UNIT, not per request: a single invocation routinely produces several chips **and** a short inline lane, and both are executed in the same turn.

After launching, **this session watches for completion on its own.** Chips are independent sessions, not subagents, so there is no push event when one finishes — instead this session polls the on-disk ledger each chip writes and, once every chip reports done, **automatically** merges all chip branches back into the base branch and runs the repo's tests. The user does not need to type "done" (though they still can, to force it early or from another session).

**The completion protocol is transport-independent, and that is what makes this portable.** Chips signal through a marker commit and a ledger JSON file, never through the launcher. So the merge, integration, and verify machinery works identically whether a chip session was started by a one-click host tool or by a human opening a terminal in a worktree. Only the convenience of launching changes.

## Configuration

Resolve these before Step 1. Each has a detection command; only override when detection is wrong.

| Value | Env var | Default | How to find yours |
|---|---|---|---|
| State directory (manifests + ledgers) | `CHIP_STATE_DIR` | `$HOME/.claude/to-chips` — the Claude Code layout, which this bundle documents as its default | any writable dir outside the repo that survives the session; on a host with a different config layout, export `CHIP_STATE_DIR` |
| Session launcher | `CHIP_LAUNCHER` | auto: a host tool that starts a background agent session from a written prompt; else `manual` | see **Prerequisites** below |
| Base branch (merge target) | — | the branch this session is on | `git rev-parse --abbrev-ref HEAD` |
| Repo identity (for matching runs) | — | auto | `git rev-parse --path-format=absolute --git-common-dir` |
| Integration verify commands | — | auto-detected from the repo | `package.json` scripts / `pyproject.toml` / `Makefile`; ask if ambiguous |
| Max chips per run | `CHIP_MAX` | `6` | — |
| Max watch budget | `CHIP_WATCH_BUDGET` | `6h` | — |
| Required model tier for chips | `CHIP_MODEL_TIER` | unset — no threshold, so the model gate is skipped and says so | the tier name your host's model picker shows, e.g. `CHIP_MODEL_TIER=Opus`; compared by CLASS, never by version string |

Never put a secret in this table or in a chip prompt. Chips run with whatever credentials their worktree inherits — see **Blast radius**.

**`CHIP_STATE_DIR` must be re-resolved inside every block that uses it — shell state does not survive between commands.** Each command you run is typically a NEW shell, so a variable assigned in the preflight is gone by the next step, and a watcher that expands an unset `$CHIP_STATE_DIR` polls `/<run-id>/ledger` and waits forever. Two rules, both required:

- **Every shell block opens by recomputing it:** `CHIP_STATE_DIR="${CHIP_STATE_DIR:-$HOME/.claude/to-chips}"`. The default resolves identically in every shell, and an exported override is inherited by all of them, so the path is deterministic either way.
- **Anything written OUT of a shell** — a chip prompt, the manifest, the run card — carries the **resolved absolute path as a literal**, never the variable name. A chip session inherits nothing from this one.

## Prerequisites

| Needs | Why | Check | If missing |
|---|---|---|---|
| `git` 2.31+ with worktree support | every chip is a worktree; merge and verify run in the base checkout | `git --version` | **Stop.** "This skill needs git with `git worktree`." |
| cwd is a git repo | worktrees, manifest, merge (Steps 3-7) | `git rev-parse --git-dir` | **Stop** for code runs. A single non-code task can still launch — see Step 2, non-code chips. |
| A background-session launcher | starts each chip without spending this session's context | your host's tool for spawning a background agent session from a written prompt | **Degrade, loudly:** set `CHIP_LAUNCHER=manual` and use Lane B in Step 5. The protocol is unchanged; the user creates the worktrees and opens the sessions. Say this in one line — never report a chip as launched when it was not. |
| Background shell execution | auto-watch polls the ledger without blocking the session | your host's ability to run a shell command in the background | **Degrade:** launch, then tell the user to say "done" when the chips finish. Manual integration is fully supported. |
| A notification channel (optional) | surfaces the merge outcome to someone who walked away | your host's notification tool | **Degrade:** report in-session only, and say once that notifications are unavailable. |
| A session-inspection tool (optional) | peek at a stalled chip | your host's session list / event tool | **Degrade:** name the chips missing a ledger and stop there. |
| `rg` (optional) | faster claim-confirmation greps | `command -v rg` | **Degrade:** use `grep -rn`; every command in this skill has a `grep` form. |

### Preflight — run before Step 1

```sh
git rev-parse --git-dir >/dev/null 2>&1 || echo "NOT_A_GIT_REPO"
git --version
CHIP_STATE_DIR="${CHIP_STATE_DIR:-$HOME/.claude/to-chips}"   # recompute in EVERY block; shell state does not persist
mkdir -p "$CHIP_STATE_DIR" || echo "STATE_DIR_UNWRITABLE:$CHIP_STATE_DIR"
echo "STATE_DIR=$CHIP_STATE_DIR"                             # record this literal - later blocks and every prompt use it
echo "MODEL_TIER=${CHIP_MODEL_TIER:-unset (model gate skipped)}"
```

Note the resolved `STATE_DIR` value from that output. Later steps either recompute it with the same one-liner or paste that literal path — never `$CHIP_STATE_DIR` in a shell that has not just set it.

Then, in one line, state which optional capabilities are present and which lanes are therefore degraded. Do not start a partial run without saying so. A missing launcher and an empty task list produce very similar-looking output — phrase every degradation by mechanism, never as a conclusion about the work.

## When to Use This Skill

**Trigger phrases:**
- "chip this task" / "split this into chips" / "parallelize this with chips"
- "hand this off to a new session" / "offload this" / "run this in a fresh session" / "chip this off my plate" — the context-preservation use: offload ANY task (however small) to a new session instead of writing a handoff document
- "watch [run-id]" — (re)enter auto-watch for a launched run (usually self-invoked)
- "done" / "merge" — force integration now (finished subset or override)
- a bare "done" — force integration, but only when the latest run for this repo has status `launched` (never re-merge a `merged` run). If "done" could plausibly mean something else in context, confirm first: "Merge the N chip branches from run <run-id>?"
- "status" — snapshot chip progress without waiting

**Not for:**
- Headless, hands-off parallel execution with auto-chaining waves. This skill is the human-in-the-loop variant: visible sessions someone starts, watches, and can steer. If you have a fully autonomous orchestrator, use that instead.
- Subagents inside THIS session (research fan-out, reviews). Those share this session's context and need no worktree, so use your agent framework's subagent mechanism directly.
- Multi-agent non-code work that needs coordination *between* agents — a research team, several review lenses arguing with each other. A single self-contained non-code task is still a valid request: launch it as one plain session chip with no worktree ceremony.

**Still the right skill when some or all of the work turns out not to be chippable.** Routing IS the job: this skill decides the lane per unit and then executes both, so "this part needs prod access" or "this needs one serial E2E lane" is an answer it produces, not a reason to bounce the request elsewhere.

## Blast radius

Before the first step, know what a run touches:

- **Writes** a manifest and ledger files under `$CHIP_STATE_DIR/<run-id>/`.
- **Creates** one git worktree and one branch per chip, and **commits** on them.
- **Commits** on the base branch (the inline lane, and the integration edits).
- **Merges** chip branches into the base branch and **runs the repo's test/lint/build commands** in the base checkout. That checkout holds the repo's real `.env`, so those commands run with real credentials — see Step 7.6.
- **Does not** push, open pull requests, or delete branches.
- **Spends** whatever each chip session costs on your agent plan; chips run unattended once started.

---

## Workflow

### Step 1: Route the mode

- **SLICE** (default) — argument is a task description. Go to Step 2, which routes each unit to the chip lane or the inline lane before any parallelization analysis.
- **WATCH** — argument is "watch", or this session is resuming its own auto-watch (background watcher just fired). Go to Step 6.
- **MERGE** — argument is "done"/"merge", or the user says "done" after a launched run (scoped per the trigger rule). Go to Step 7.
- **STATUS** — argument is "status".

### Step 2 (SLICE): Route each unit — chip what benefits, do the rest here

Split the request into units of work, then route EACH one. Ask a single question per unit: **would a fresh session with a written prompt do this better than I would right now?**

**An explicit offload request pre-decides the routing.** When the user says "chip this", "offload this", "chip this off my plate", "hand this off to a new session", or "run this in a fresh session", they have already made the ceremony-vs-work call — they are spending their context, not yours — and it is not yours to re-litigate. Those units go to chips. Only a STRUCTURAL blocker (the first inline bullet below) can override the request; "the ceremony costs more than the work" and "I could not write the prompt" are NOT available against an explicit request. If a structural blocker genuinely applies, say so in one line and ask before absorbing the unit inline.

**CHIP it when** a cold agent can run it unattended from a prompt: it is independently committable, its files are knowable up front, it needs no mid-flight decision from the user, and finishing it here would burn context you want for something else. Small is fine — a one-line fix is a perfectly good chip, and "I could just do it in 30 seconds" is a weak reason to keep it when your context is the scarce resource. **When context is running low, lean harder toward chipping**, including for small units: that is the situation this skill was built for.

**Do it INLINE when** chipping would fight the work rather than help it:

- **A chip structurally cannot.** It needs live-system access a fresh worktree lacks (prod, credentials, deploy control, an external account), or a globally exclusive resource that concurrent chips would contend for (serial E2E ports, one shared DB with a destructive teardown, a device), or an approval gate mid-flight (outbound comms, purchases, irreversible ops) where a chip would stall or guess.
- **It is the scouting that decides the chip cut.** Diagnose first, then chip what the diagnosis found.
- **It needs a HUMAN in the loop, not just iteration.** A chip iterates perfectly well on its own — it just iterates against tests instead of against a person. What it cannot do is get *their* judgment mid-flight: a design call, a taste question, an approval. "Exploratory debugging" is NOT this; a chip debugs fine given a failing test.
- **The ceremony costs more than the work — but only the first time you pay it.** Worktree + branch + merge + verify is a per-RUN cost, not a per-chip one: if this run is already cutting chips, one more costs a single launch call, so this clause is unavailable — chip it. It applies only when ALL of: this run would otherwise chip nothing, the unit is a single-file edit you can finish this turn with no new file reads, the user did not ask you to offload it, and your context is not under pressure. What it may never rest on is "a trivial edit I am already positioned to make" — being positioned to do it is the rationalization this skill exists to overrule.
- **No prompt you could write would let a cold agent finish it.** Do not estimate this, TEST it: draft the three lines — goal (one sentence) / owned paths / done-when + verify command. If you can write them, chip it; you just wrote the prompt, and [references/chip-prompt.md](references/chip-prompt.md) supplies the rest. Fall back to inline only if you can NAME the missing fact you cannot supply: a decision only the user can make, a value only this live session holds, or an artifact you cannot point at by path/id/URL. If you cannot name it, the unit is under-specified rather than un-chippable, and specifying it *was* the work.

**Scout-then-fan-out is the highest-value shape here.** When a unit's output is the chip plan, do it inline FIRST in this same turn, then cut chips from what you learned. This is why routing is per-unit rather than per-request.

**Sequencing across lanes.** If any inline unit needs an exclusive resource, every chip prompt must be told to stay off it ("do NOT run the browser E2E suite; it is serial and the parent session owns it") — two lanes fighting over one database produce false failures in both. Step 5b covers when each lane runs.

**Any mix is a valid outcome**, including all-chips and all-inline. If nothing wants chipping, say so in one line and do the work — do not manufacture a chip to satisfy a quota, and do not stall to ask whether chips are appropriate. The one bias worth naming: "I already have the context loaded" argues for chipping when that context is nearly spent, not against it.

**If zero units routed to the chip lane, stop the chip workflow here.** Skip Steps 3-7 entirely — no run-id, no manifest, no ledger directory, no watcher, no MERGE. Print the short no-chip block from Output Format and go straight to Step 5b. (A manifest with `"chips": []` plus an armed watcher is the failure mode to avoid: it waits on ledgers nothing will ever write.)

Everything below in Steps 3-5 concerns the chip lane. The inline lane is executed by this session in the same turn (Step 5b).

**Firing a single chip for a non-code task.** A single self-contained non-code task — a message draft, reading and analyzing a document, a one-shot errand, a single research question or write-up — is still a valid one-chip run, but it needs neither a worktree/merge/test cycle nor any multi-agent machinery. It needs exactly what a chip's underlying primitive already gives: a session pre-loaded with the prompt. Compose a **self-contained prompt** (cold-agent test — task + context + durable artifact links/ids + any approval or tone rules) and launch a SINGLE chip with `{title, tldr, prompt}`; **omit the working directory** (a fresh empty workspace is harmless for non-code work), and skip Steps 3-5's worktree/manifest/merge ceremony. Do this **directly, without complaint** — this is the common "just launch a session with this prompt" request, and it should Just Work. One-line trace: `not a code task; single session-sized -> launching one session chip (no worktree/merge/test).`

Apply the independence test to decide **1 vs many**:

- Does the task decompose into **2+ independently committable units** that do **not edit the same files** and do **not need each other's output**?

Outcomes:
- **No real split (a single or small task)** -> launch exactly **ONE chip** for the whole task. Size alone is not a reason to keep it — if it passed Step 2's routing, offloading it to a fresh session is the point. Its owned paths are simply the files the task will touch (or, if unknown up front, the directory or area it lives in). This is the most common shape.
- **Split exists but has a dependency spine** (a shared foundation: schema, types, engine, design system) -> the spine is NOT chippable alongside its dependents. Make the spine the FIRST chip and record the dependent wave in the manifest's `next_wave` (a cold MERGE session surfaces it); or, if the spine is trivial, fold it into a single chip with its dependents. One run = one wave of file-disjoint chips.
- **2 to `CHIP_MAX` independent units** -> chip them. Collapse tiny units into neighbors. If a unit is itself too big for one session, split it further only if the pieces stay file-disjoint — otherwise keep it as one bigger chip.

Never *manufacture* parallelism: splitting into MULTIPLE chips still requires genuine file-disjoint independence. "Not parallelizable" means **one chip**, not several — whether it is chipped at all was already decided in Step 2.

Also preflight for an existing run on this repo with status `launched` — recompute the state dir in the same block that reads it:

```sh
CHIP_STATE_DIR="${CHIP_STATE_DIR:-$HOME/.claude/to-chips}"
grep -l '"status": "launched"' "$CHIP_STATE_DIR"/*/manifest.json 2>/dev/null
```

Match repos by `git rev-parse --path-format=absolute --git-common-dir`, **not by cwd** (a worktree's cwd differs from its repo's). If a live run exists, warn — two live runs can own overlapping files — and get confirmation before launching a second.

### Step 2b (SLICE): Run the scouting units NOW

If Step 2 routed any unit inline because its output IS the chip plan, execute it here — before cutting anything. Steps 3-5 consume its result. Skipping ahead means fabricating a cut from a diagnosis you have not done, which is how chips end up owning the wrong files.

### Step 3 (SLICE, chip lane only): Cut the chips

For each chip define:
1. **Goal** — one objective sentence.
2. **Owned files/dirs** — the only paths this chip may create or edit. Ownership across chips MUST be disjoint. Shared files (barrel exports, route tables, lockfiles, config) belong to NO chip — chips list them as forbidden, and the integration step (MERGE) makes those edits after merging.
3. **Done-when** — checkable criteria plus the exact per-chip verify command (targeted tests, typecheck of its files).
4. **Hand-back contract** — filled from the template in [references/chip-prompt.md](references/chip-prompt.md).

Record every shared-file edit you are deferring to integration (file -> exact change, e.g. "src/index.ts -> export chip 2's module") in the manifest's `integration_edits` array — MERGE step 5 executes exactly this list, so an empty field means you promised no wiring.

Also detect the repo's **integration verify commands** now (test/build/lint from `package.json` / `pyproject.toml` / `Makefile`, or ask if ambiguous) — recorded in the manifest, run at MERGE time.

### Step 4 (SLICE): Commit the base and write the manifest

1. **Commit first.** A chip worktree never starts from this session's working tree, and where it *does* start depends on the lane: a host launcher (Lane A) typically forks it from the repo's **default-branch HEAD**, while a manual worktree (Lane B) starts at whatever commit `git worktree add` was handed — which, below, is `<base_commit>` itself. Both lanes converge because each chip's first action (per the template) is `git reset --hard <base_commit>`: a real move in Lane A, a harmless no-op in Lane B. Either way the base must be a commit: if the working branch has uncommitted changes the chips need, commit them now (normal commit rules apply). Record `base_branch` = the branch this session is on (the merge target), `base_commit` = its current SHA, `base_checkout` = the absolute path of the checkout where `base_branch` is checked out (usually this session's cwd — worktrees count).
2. **Write the manifest** to `<state-dir>/<run-id>/manifest.json` — `<state-dir>` is the resolved absolute path from the preflight, not the variable name (`run-id` = `<repo-name>-<YYYYMMDD-HHMMSS>`):

```json
{
  "run_id": "...",
  "repo_root": "/abs/path (git common dir's parent)",
  "base_branch": "feature/x",
  "base_commit": "<full sha>",
  "base_checkout": "/abs/path of the checkout holding base_branch",
  "verify_commands": ["npm test", "npm run lint"],
  "integration_edits": [{"file": "src/index.ts", "change": "export new module from chip-2"}],
  "deferred_inline": ["inline units held until after integration, e.g. run the serial E2E suite"],
  "next_wave": "optional: what to chip after this run merges",
  "status": "launched",
  "chips": [
    {"id": "chip-1", "title": "...", "owned_paths": ["src/foo/"]}
  ]
}
```

Create the empty `<state-dir>/<run-id>/ledger/` directory alongside it, using that same resolved literal — this is the exact path every chip prompt will carry, and the path the watcher recomputes to.

### Step 5 (SLICE): Compose and launch the chips

Build each chip's prompt from [references/chip-prompt.md](references/chip-prompt.md). Every prompt must be **self-contained** — a cold agent with no access to this conversation must be able to execute it. Inline the project context, conventions, owned and forbidden paths, done-when, the literal `base_commit` SHA, the literal resolved ledger path, and the hand-back contract verbatim. Resolve the state dir to a real absolute path (`CHIP_STATE_DIR="${CHIP_STATE_DIR:-$HOME/.claude/to-chips}"`, then paste the value) before writing it into a prompt: the chip session will not have that variable set.

**Self-contained is not the same as true — a chip prompt may not assert an unverified fact about the code.** This fires whenever a prompt (or an inline unit's brief) states that the code currently contains X: a literal string, a token or class of a particular kind, a count of occurrences, or a defect list you did not confirm this turn. Either confirm it NOW (`grep -rn '<literal>' <path>`, or `rg -n` if available) and paste the matched line into the prompt, or write it as a LEAD carrying its own confirm step, verbatim: "claim: <X>. Confirm with `<exact command>` BEFORE editing; if it does not reproduce, change nothing, mark the item not-present, and say so in the hand-back." A prompt that hands over a defect LIST carries that instruction once for the whole list, and the chip-prompt template's `Claims to confirm before editing` block is where it goes. A cold agent cannot tell a verified fact in its prompt from a remembered one, so an unchecked claim becomes an edit.

> **Failure mode, measured.** A 12-defect brief for a front-end hardening task carried two false claims. One named a Tailwind class `bg-f5e6d3` in a component that already read `bg-[#f5e6d3]` — the "defect" was the brief's own typo. The other labelled `shadow-container` a design-system boxShadow token when it was really a plain CSS class injected at runtime by a style component, setting `overflow: overlay` plus webkit scrollbar rules; "fixing" it would have shipped a drop shadow that never existed. The same brief understated a dead-class count by roughly 5x — 73 distinct classes, described as "a handful". Two of twelve items were fiction, and a cold agent would have edited on all twelve.
>
> Validation before every launch: *"for every code fact in this prompt, did I run the command that proves it, or did I give the agent the command to run first?"*

**Model gate (before any launch).** On hosts where a chip session inherits the launching session's model, effort, and permission mode, the host stamps them onto each chip from THIS session. Three consequences, none of them documented anywhere the agent can read at runtime:

- The launch call typically has **no model parameter**.
- A `model:` entry in a settings file **cannot override** the host's per-session stamp.
- **You cannot switch the model yourself** — the user must, from the model picker.

The threshold is `CHIP_MODEL_TIER` (see **Configuration**). It ships **unset**, because no tier name is portable across hosts — an un-evaluable "required tier" is worse than none, so there is no built-in value to guess at.

- **`CHIP_MODEL_TIER` unset (the default)** -> there is no threshold to compare against, so **skip the gate** and say so in one line: "No CHIP_MODEL_TIER set - chips will inherit this session's model (<model>)." The run card prints the inherited model regardless, which is what makes the inheritance visible without a gate.
- **`CHIP_MODEL_TIER` set** -> compare it against this session's own model (stated in your environment context) by CLASS, not by exact version string: case-insensitive match of the configured tier name against the session's model name, ignoring version numbers, so a newer release of the same tier is never treated as a downgrade.
  - **Session at or above the required tier** -> proceed to launch.
  - **Below it** -> show the cut plan but **do NOT launch yet**. Tell the user: "Chips inherit this session's model (currently <model>); this run asks for <CHIP_MODEL_TIER>. Switch this session with the model picker, then say 'launch'." Launch on a lower tier only if they explicitly say to keep it. **This gate blocks the CHIP lane only** — carry on with Step 5b's inline units while it is held (skipping any whose result would change the cut) and report them alongside the pending plan.

If you have not confirmed that your host inherits session settings this way, say so in one line and skip the gate rather than asserting behavior you have not observed.

**Launching — two lanes, one protocol.**

*Lane A — a host session launcher is available.* Launch one background session per chip with:
- `prompt` — the full chip prompt.
- `title` — imperative, under 60 chars (e.g. "Chip 2/4: Build the export endpoint").
- `tldr` — 1-2 plain-English sentences; no file paths or code (it is a tooltip).
- working directory — omit, so the host creates a fresh worktree in the current project. Set it only if the task names a different repo.

*Lane B — `CHIP_LAUNCHER=manual`.* Create the worktrees yourself and hand the user the prompts. Each prompt is composed text that **you paste into the heredoc below** — nothing in this skill sets a variable holding it, and redirecting an unset variable writes a zero-byte file and still exits 0, so the lane would look like it worked and hand the user an empty brief. Everything downstream is identical, because chips report through files, not through the launcher:

```sh
# recompute first: this is a new shell, and the preflight's value did not survive
CHIP_STATE_DIR="${CHIP_STATE_DIR:-$HOME/.claude/to-chips}"
PROMPT_DIR="$CHIP_STATE_DIR/<run-id>"
mkdir -p "$PROMPT_DIR"          # Step 4 already made it; harmless if this shell is fresh
# one per chip, run from the base checkout
git worktree add -b "chip-<N>-<slug>" "../<repo-name>-chip-<N>" "<base_commit>"
# Write the prompt where the chip session will read it. Paste the composed prompt
# text between the markers - the quoted delimiter keeps $, `, and \ literal, so
# the chip reads exactly what you wrote.
cat > "$PROMPT_DIR/chip-<N>.prompt.md" <<'CHIP_PROMPT_EOF'
<the entire composed prompt for chip <N>, pasted verbatim here - every section of
references/chip-prompt.md with its placeholders already filled in>
CHIP_PROMPT_EOF
# Loud, not silent. `[ -s ]` is NOT enough here: a single blank line is 1 byte and
# passes it, and so does an unedited copy of the placeholder above. Check content -
# a real prompt carries the literal base commit and no longer carries the marker.
PF="$PROMPT_DIR/chip-<N>.prompt.md"
if grep -q 'pasted verbatim here' "$PF" || ! grep -q '<base_commit>' "$PF"; then
  echo "BAD_PROMPT:chip-<N> - paste the real composed prompt, then re-run"; exit 1
fi
wc -c "$PF"
```

Then tell the user, explicitly and in one line: *"Chip launching is not available on this host, so I created N worktrees and wrote N prompts. Open an agent session in each worktree and give it its prompt. I will still auto-merge and test once all N report done."* A prompt built this way already contains its `git reset --hard <base_commit>` first step, which is a harmless no-op when the worktree was created at that commit — leave it in, so one prompt works in both lanes.

Print the run card (Output Format below). Then, unless the user said "just launch" / "no watch", **immediately arm auto-watch (Step 6) in the same turn.**

### Step 5b (SLICE): Execute the inline lane

Chips are launched, not executed — nothing runs until someone starts them. So after arming the watcher, **do the inline units in this same turn** rather than reporting a plan and stopping. Order matters:

- **Scouting units already ran** at Step 2b — the cut was derived from them.
- **Units needing an exclusive resource** (serial E2E, a shared DB with destructive teardown) run either before launching or after integration — never while chips are in flight. Say which in the run card, and record anything deferred in the manifest's `deferred_inline` so Step 7 actually runs it.
- **Everything else** can proceed while the chips work.
- **The inline lane counts as a chip for ownership.** Do not create or edit any path listed in a chip's `owned_paths`. Chips forked from `base_commit` while you are committing onto `base_branch`, so an inline edit to a chip-owned file is a guaranteed merge conflict at Step 7 — fold the change into that chip's prompt instead, or defer it to Step 7's integration edits.
- **Commit each inline unit as you finish it.** The watcher can fire at any moment and Step 7 halts unless `base_checkout` has a clean tree — an uncommitted inline edit will stall the auto-integration you just promised. If something must stay uncommitted, say so in the run card and disarm auto-watch so the user merges deliberately.

If an inline unit turns out to need approval (an outbound send, a purchase, an irreversible op), stop at that unit and ask — do not guess, and do not let it block the other inline units or the chips.

Report inline results in the same reply as the run card, so one turn answers both "what did you dispatch" and "what did you already finish".

### Step 6 (WATCH): Wait for all chips, then auto-integrate

The goal: detect completion without the user typing anything, then hand off to MERGE. Completion is signalled by the ledger files chips write (`$CHIP_STATE_DIR/<run-id>/ledger/chip-<N>.json`) — poll them; do not expect a push event.

1. **Arm a background watcher** that exits when every chip has written its ledger. Run it in the background with a timeout around ten minutes:

   ```bash
   # The watcher runs in its own shell, so it recomputes the state dir rather than
   # inheriting it. Without this line $CHIP_STATE_DIR is empty here and LED becomes
   # "/<run-id>/ledger" - a path that never fills, so the loop never exits.
   CHIP_STATE_DIR="${CHIP_STATE_DIR:-$HOME/.claude/to-chips}"
   LED="$CHIP_STATE_DIR/<run-id>/ledger"
   [ -d "$LED" ] || { echo "NO_LEDGER_DIR:$LED"; exit 1; }
   # find, not a bare glob: safe under zsh's nomatch and portable to bash
   until [ "$(find "$LED" -maxdepth 1 -name 'chip-*.json' 2>/dev/null | wc -l | tr -d ' ')" -ge <N> ]; do sleep 30; done
   echo "all <N> chips reported"
   ```

   The `[ -d "$LED" ]` line is the guard that turns the old silent-hang failure into
   a loud one: a mis-resolved state dir now exits non-zero on the first pass instead
   of sleeping until the watch budget runs out.

   If background execution is unavailable but your host can schedule a self-wake, re-invoke this skill's WATCH mode on a patient cadence — roughly 4-5 minutes while chips are in flight, so each wake lands outside the previous one's prompt-cache window. If neither exists, stop here and tell the user to say "done" when the chips finish.

2. **When the watcher fires** (re-invoking this session): recompute the ledger count.
   - **All <N> present** -> read every ledger. If all say `status: done`, proceed to **Step 7 (MERGE)** automatically. If any says `needs_attention`, STOP: report which and why, and ask whether to merge the finished subset or wait. Do not auto-merge a run with a flagged chip.
   - **Still fewer than N** (the watcher hit its cap, not completion) -> re-arm the same watcher. Track total elapsed; after `CHIP_WATCH_BUDGET` (default ~6 hours) with no completion, stop watching and tell the user the run is parked — they can resume anytime with "done". Name the chips still missing a ledger; if one has clearly stalled, offer to inspect its session if your host can.

3. **Notify.** When auto-integration finishes (or halts for a decision), send a notification if your host has one — the user launched these to walk away, so surface the outcome: merged and tests green, or the specific thing that needs them. If there is no notification channel, say so once rather than silently skipping it.

Auto-watch is interruptible: if the user says "stop watching" or "cancel", stop the background watcher and leave the run for a manual "done".

### Step 7 (MERGE): Merge back and test

Reached automatically from WATCH, or manually via "done"/"merge".

1. **Locate the run.** Recompute the state dir first — MERGE often arrives in a cold session, hours later, with nothing set:

   ```sh
   CHIP_STATE_DIR="${CHIP_STATE_DIR:-$HOME/.claude/to-chips}"
   ls "$CHIP_STATE_DIR"/*/manifest.json
   ```

   Scan those manifests for runs matching this repo (`git rev-parse --path-format=absolute --git-common-dir` comparison). One unmerged run -> use it. Multiple unmerged runs -> list them and ask which. A run-id argument always wins.
2. **Collect chip results.** Read `ledger/*.json`. For any chip missing a ledger entry, fall back to branch discovery: `git log --all -F --grep="[to-chips:<run-id>:chip-<N>]" --format="%H %s"` — **the `-F` is required**, because without it git treats the brackets as a regex character range and the command dies with `fatal: ... invalid character range` - it does not run and match the wrong commits, it refuses to run at all. Then resolve the branch with `git branch --contains <sha> --format="%(refname:short)"` (excluding `base_branch` itself). The marker commit may sit mid-branch; the **branch tip** is what gets merged. A chip with neither a ledger entry nor a marked commit is **unfinished**.
3. **Preflight.** If any chip is unfinished or `needs_attention`, STOP and report which — ask whether to merge the finished subset or wait. Then locate the merge cwd: run `git worktree list --porcelain` and find the checkout whose branch is `base_branch` (start from `base_checkout`; it may have moved). If no checkout has it, check it out in the main repo root. NEVER `git checkout <base_branch>` in a second location while one already holds it, and never use `--ignore-other-worktrees`. Assert that `git rev-parse --abbrev-ref HEAD` equals `base_branch` and that the working tree is clean before the first merge; halt with a clear message otherwise.
4. **Merge, one chip at a time,** in that checkout (`git merge --no-ff <chip-branch> -m "merge chip-N: <title> [to-chips:<run-id>]"`). Chips own disjoint files, so conflicts should be rare; if one occurs, resolve it yourself favoring both chips' intent. If intent is genuinely ambiguous, run `git merge --abort` FIRST (never leave a mid-merge state), then halt and report which chip branch conflicted on which files. Never resolve by discarding a chip's work silently. Already-merged chips stay merged — each merge is atomic, so a retry resumes cleanly.
5. **Integration edits.** Apply the shared-file edits no chip was allowed to make, from all three channels: (a) the manifest's `integration_edits`, (b) each chip's ledger `notes`, and (c) any `INTEGRATION-NOTES.md` files inside the merged chips' owned paths (`git ls-files '*INTEGRATION-NOTES.md'`). Delete those files once applied.
6. **Verify.** Run every `verify_commands` entry. All must exit 0 — and **take that exit code from the command itself, not from the harness.** A background task's "completed (exit code 0)" is the status of the LAST command in the call, so a diagnostic appended after a gate silently overwrites it. A pipe is worse: `cmd | tail` returns `tail`'s status, which is always 0. Capture each gate's own code on its own line, and read the tallies too, not just the code:

   ```sh
   npm test > test.log 2>&1; echo "TEST_EXIT=$?"
   ```

   If a gate is red, **baseline it at the merge-base before blaming the chips** — an identical failure on a clean tree is pre-existing, not yours. Four traps worth checking before you accuse a chip:

   - **Migrated is not seeded.** For E2E suites, confirm the test environment is SEEDED and not merely migrated. Mass login failures across unrelated specs are empty reference tables, not a code regression.
   - **Pinned `typeRoots` breaks worktrees.** If EVERY suite dies at compile with `Cannot find name 'describe'` / `'expect'` while `@types/*` is installed at the repo root, the tsconfig pins `typeRoots` — that disables TypeScript's default upward walk, and a fresh chip worktree has no `node_modules` of its own. Delete `typeRoots`; do NOT symlink `node_modules` into the worktree.
   - **Verify runs where the real credentials are.** It runs in the BASE checkout, which unlike a chip worktree holds the repo's real `.env`. A suite that sends mail or charges a card for real fires HERE and not in the chips. Confirm the test bootstrap overwrites provider credentials before running it.
   - **A green pipeline is not a shipped change.** If verification includes a deploy, read the running artifact's own identity and compare it to what you pushed. Staleness has no error state.

   On failure: diagnose and fix on the base branch — the chips' individually verified units make bisection easy, so suspect the integration seams and shared-file wiring first. Report honestly if something stays red.
7. **Deferred inline work.** Run anything in the manifest's `deferred_inline` now — this is where the serial-resource units the run card promised get executed. Report their results with the merge outcome.
8. **Report + finalize.** Update the manifest `status` to `merged`. If the manifest has a `next_wave` note, surface it: "This run unblocked the next wave — re-run for: <note>". Do NOT delete chip branches now: the chip worktrees still hold them, so `git branch -d` would fail. Leave cleanup for later, and when it happens remove the worktree first (`git worktree remove`) and then use `git branch -d`, never `-D` — `-d` refuses to delete an unmerged branch, and that refusal is the only thing standing between a cleanup pass and silently discarded work.

### STATUS mode

Read the latest matching manifest and ledger, and report per chip: **launched** (no ledger entry yet) or **done** / **needs_attention** (from the ledger), plus whether auto-watch is still armed and what remains before MERGE can run. Chips do not report progress mid-flight; to inspect a running chip, use your host's session-inspection tool if it has one.

---

## Output Format (run card, after SLICE)

Lead with the routing so the split is visible, then the chip table, then what you are doing yourself.

```markdown
## <task title> — <N> chips + <M> inline (run: <run-id>)

Base: <base_branch> @ <short-sha> - committed and ready.
Model: <this session's model> - inherited by every chip (tier gate: <CHIP_MODEL_TIER | none set>).
Launcher: <host launcher | manual worktrees>.

| Unit | Lane | Why |
|---|---|---|
| <unit> | chip 1 | independent, file-disjoint, runs unattended |
| <unit> | inline | needs prod access a fresh worktree does not have |
| <unit> | inline | serial E2E - running after the chips integrate |

| Chip | Owns | Done when |
|---|---|---|
| 1. <title> | <paths> | <one-liner> |

Start each chip to run its agent - they work in parallel worktrees.
I'm now watching for completion - once all <N> report done I'll auto-merge
into <base_branch> and run: <verify commands>. You don't need to type "done"
(say "done" to force it early, or "stop watching" to cancel the auto-merge).

Meanwhile I'm doing <inline units> myself; <any unit deferred until after
integration, and why>.
```

When nothing wants chipping, skip the ceremony entirely — one line on why, then the work:

```markdown
Not chipping this: <reason - needs live prod access / one exclusive E2E lane /
you'll want to steer it turn by turn>. Doing it here.
```

---

## Quality Checklist

_Chip-lane items below apply only to runs that launched at least one chip._

- [ ] Preflight ran; every degraded lane (no launcher, no background execution, no notifications) was stated in one line, not silently skipped
- [ ] Every unit routed in Step 2, shown in the run card — or, for a zero-chip run, in the one-line no-chip note — with a one-line reason each; no unit silently dropped; no stalling to ask "are chips appropriate?" — route and execute
- [ ] Units kept inline were kept for a real reason (structural blocker, scouting, genuinely interactive, or ceremony > work), NOT reflexively — and under context pressure the lean went toward chipping even for small units
- [ ] Chip COUNT matched real independence — single or small task -> one chip; multiple chips only for genuinely file-disjoint units; no manufactured parallelism; spine excluded or folded, with the dependent wave in `next_wave`
- [ ] Inline work needing an exclusive resource (serial E2E, shared DB) ran BEFORE launch or AFTER integration — never concurrently with chips — and chip prompts were told to stay off it
- [ ] Chip file ownership is disjoint; shared-file wiring recorded in `integration_edits`, not assigned to chips
- [ ] Base committed before launch; `base_branch` / `base_commit` / `base_checkout` recorded in the manifest
- [ ] Model gate ran by CLASS against `CHIP_MODEL_TIER` (never by exact version string), or was explicitly skipped — and said so — because no tier is configured or host inheritance is unconfirmed
- [ ] Every chip prompt is self-contained (cold-agent test) and carries the literal `base_commit` SHA, the literal resolved ledger path, and the hand-back contract
- [ ] Every code fact asserted in a chip prompt was confirmed this turn (matched grep line pasted) or handed over as a lead with its own confirm-before-edit command — no defect list, literal string, or token-kind claim shipped unverified
- [ ] Auto-watch armed after launch, or the manual-done fallback stated explicitly
- [ ] Every shell block that touches the state dir recomputed `CHIP_STATE_DIR` in that same block (preflight, Lane B, watcher, MERGE), and every path written into a prompt or manifest is a resolved literal
- [ ] WATCH: polls the ledger (no push assumed); re-arms on timeout; halts on `needs_attention`; has a max budget; notifies on outcome or says it cannot
- [ ] MERGE: all chips accounted for (ledger or `-F` marker grep) before merging; merges ran in the checkout that holds `base_branch`; ambiguous conflicts aborted before halting; every verify command's own exit code captured (never a pipe's, never the harness's) and green before declaring success
