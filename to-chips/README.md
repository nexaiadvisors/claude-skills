# to-chips

Split a task between **fresh background agent sessions** — each in its own git worktree — and **the session you are already in**, then run both lanes and merge the results automatically.

The idea it is built around: for any unit of work, ask *"would a cold agent with a written prompt do this better than I would right now?"* Some units answer yes (independent, file-disjoint, unattended). Some answer no (needs prod access, needs a human mid-flight, is the scouting that decides the plan). This skill routes **per unit**, executes **both** answers in the same turn, and then merges the parallel work back and runs your tests.

> **Forking this?** `LICENSE` is MIT, held by NexAI Advisors LLC. If you redistribute under your own name, update the holder - see [Before you publish or fork this](#before-you-publish-or-fork-this).

## What it does

- **Routes each unit of work** to the chip lane or the inline lane, with a written reason per unit, and shows the routing table before doing anything.
- **Cuts chips with disjoint file ownership.** Shared files (barrel exports, route tables, lockfiles) belong to no chip; their edits are recorded up front and applied once at integration.
- **Pins every chip to one immutable base commit**, so all chips share a byte-identical base no matter when each is started.
- **Detects completion from disk** — a marker commit plus a ledger JSON file per chip — then merges every chip branch into your base branch and runs your repo's test/lint/build commands.
- **Executes the inline lane in the same turn**, instead of handing you a plan and stopping.
- **Deliberately does not**: push, open pull requests, delete branches, or run chips itself. Chips are *launched*; a human starts them. That is the approval gate.
- **Deliberately does not** manufacture parallelism. A task with no genuine file-disjoint split becomes exactly one chip, not four.

## Prerequisites

| Needs | Why | Check | If missing |
|---|---|---|---|
| `git` 2.31+ with worktree support | every chip is a worktree; merge and verify run in the base checkout | `git --version` | **Stop.** The skill cannot run. |
| cwd is a git repo | worktrees, manifest, merge | `git rev-parse --git-dir` | **Stop** for code runs. A single non-code task can still launch as one plain session chip. |
| A background-session launcher | starts each chip without spending the current session's context | your agent host's tool for spawning a background session from a written prompt | **Degrades to manual worktrees.** See *Limitations*. |
| Background shell execution | auto-watch polls the ledger without blocking | your host's background-command capability | **Degrades:** you type "done" when the chips finish. |
| A notification channel (optional) | surfaces the merge outcome if you walked away | your host's notification tool | **Degrades:** in-session report only. |
| A session-inspection tool (optional) | peek at a chip that looks stalled | your host's session list / event tool | **Degrades:** the skill names the chips missing a ledger and stops there. |
| `rg` (optional) | faster claim-confirmation greps | `command -v rg` | **Degrades:** `grep -rn`. Every command here has a grep form. |

**There is no vendor lock-in below the launcher.** Chips report through a marker commit and a JSON file on disk, so the merge/verify half of the skill works on any host — including no host at all, with worktrees you create by hand.

**Where it is not neutral, it says so.** The install path and the default state directory follow the **Claude Code** `~/.claude` layout, because a default has to be *some* concrete path. The state directory is the only one the skill actually reads, and `CHIP_STATE_DIR` overrides it; the install path is never read at all.

## Install

The paths below are the **Claude Code** skill layout, which this bundle targets as its documented default:

```sh
# user scope (available in every project)
git clone <this-repo> ~/.claude/skills/to-chips

# project scope (checked in, shared with a team)
git clone <this-repo> .claude/skills/to-chips
```

On a host with a different layout, clone into that host's skills directory instead — nothing in the skill reads its own install path. The one path the skill *does* use is its state directory, which defaults to the same `~/.claude` layout and is overridable with `CHIP_STATE_DIR` (see **Configuration**).

Then invoke it by name, or with one of the trigger phrases: *"chip this"*, *"offload this"*, *"run this in a fresh session"*, *"split this up and get it done"*.

## Configuration

Everything has a working default. Set an env var only when detection is wrong.

| Value | Env var | Default | Required? |
|---|---|---|---|
| State directory (manifests + ledgers) | `CHIP_STATE_DIR` | `$HOME/.claude/to-chips` (Claude Code layout — set this on hosts that use a different one) | no |
| Session launcher | `CHIP_LAUNCHER` | auto-detected; `manual` when no host launcher exists | no |
| Max chips per run | `CHIP_MAX` | `6` | no |
| Max watch budget before parking the run | `CHIP_WATCH_BUDGET` | `6h` | no |
| Required model tier for chips | `CHIP_MODEL_TIER` | unset — the model gate is skipped and says so | no |
| Base branch (merge target) | — | whatever branch the session is on | detected |
| Verify commands | — | detected from `package.json` / `pyproject.toml` / `Makefile` | detected, asks if ambiguous |

No secret ever belongs in this table or in a chip prompt. Chips inherit whatever credentials their worktree has.

## Worked example

> The transcript below is **illustrative** — it shows the shape of a run and the exact artifacts it writes. It is not a recording of a specific execution.

You are on `feature/reports` with three things to do: add a CSV export endpoint, fix a date-formatting bug in the dashboard, and confirm the staging deploy still serves the right build.

```
> chip this: CSV export endpoint, fix the date formatting bug, and check staging
```

```markdown
## Reports work — 2 chips + 1 inline (run: acme-web-20260822-1412)

Base: feature/reports @ 4f1c9ab - committed and ready.
Model: <session model> - inherited by every chip (tier gate: none set).
Launcher: host launcher.

| Unit | Lane | Why |
|---|---|---|
| CSV export endpoint | chip 1 | independent, file-disjoint, runs unattended |
| Date formatting bug | chip 2 | independent, file-disjoint, one failing test to drive it |
| Check staging build | inline | needs live deploy credentials a fresh worktree does not have |

| Chip | Owns | Done when |
|---|---|---|
| 1. Build the export endpoint | src/api/export/ | `npm test -- export` passes |
| 2. Fix date formatting | src/dashboard/format/ | `npm test -- format` passes |

Start each chip to run its agent - they work in parallel worktrees.
I'm now watching for completion - once all 2 report done I'll auto-merge
into feature/reports and run: npm test, npm run lint.

Meanwhile I'm checking staging myself.
```

While the chips run, the session does the staging check inline and commits it. Each chip, when it finishes, writes:

```json
{
  "chip": "chip-1",
  "branch": "chip-1-csv-export",
  "status": "done",
  "verify": "npm test -- export -> pass",
  "notes": "New route module. Integration must export it from src/api/index.ts."
}
```

The watching session sees both ledgers, merges both branches with `--no-ff`, applies the one deferred shared-file edit (`src/api/index.ts`), runs `npm test` and `npm run lint` capturing each exit code on its own line, and reports the result.

## Limitations & blast radius

**What a run writes and where**

- A manifest and one ledger file per chip under `$CHIP_STATE_DIR/<run-id>/`.
- One git worktree and one branch per chip, with commits on them.
- Commits on your base branch: the inline lane, and the integration edits.
- Merges into your base branch, then your repo's test/lint/build commands run **in the base checkout** — which holds your real `.env`. A suite that sends mail or charges a card for real will do so there. Confirm your test bootstrap overwrites provider credentials.
- It never pushes, never opens a pull request, and never deletes a branch.

**Known limits**

- **Without a host session launcher the "one click" is gone**, not the skill. The fallback creates the worktrees and writes each prompt to a file; you open a session in each worktree yourself. Everything downstream — ledger detection, merge, integration edits, verify — is byte-identical, because chips never talk to the launcher.
- **Without background shell execution there is no auto-watch.** Chips still run; you say "done" when they finish.
- **Chips do not report progress mid-flight.** They are opaque until they write a ledger. `status` mode tells you which have reported, nothing more.
- **One wave per run.** If your split has a dependency spine (schema, types, design system), the spine goes first and the dependents wait for the next run. The skill records the next wave rather than trying to sequence it.
- **Model inheritance is host-specific.** On hosts where a background session inherits the launching session's model and permission mode, you must set them on the launching session *before* launching — the launch call has no model parameter and a settings file cannot override the per-session stamp. If your host does not behave this way, the skill says so and skips that gate rather than asserting behavior it has not observed. The tier the gate checks against is `CHIP_MODEL_TIER`, which ships **unset** — no tier name is portable across hosts, so with nothing configured the skill skips the comparison and just prints the model each chip will inherit.
- **Tested scope:** developed and used against git repos on macOS with a JavaScript/TypeScript toolchain. The git and shell mechanics are portable and use no macOS-only commands, but Linux and Windows have not been exercised. This packaging pass did not execute the skill end to end.

## Before you publish or fork this

**If you fork this and redistribute it, put your own name in `LICENSE`.** As shipped here, line 3 reads `Copyright (c) 2026 NexAI Advisors LLC` and the frontmatter declares `license: "MIT"`. If you republish under your own name, replace the holder and update the year. That is the whole task - `LICENSE` is otherwise canonical MIT and needs no other edit.

No automated check will catch an empty holder for you. The privacy scanner that gates this bundle looks for personal identity leaking **out** of the files; a *missing* holder is the exact inverse, so it passes clean with a placeholder still in place. Treat the scanner's green as evidence about personal data only - the copyright line is a human step.

**This reminder lives here and not in `LICENSE`, on purpose - please do not move it back.** Licence detectors (GitHub's `licensee`, and the SPDX-style matchers most hosts copy) score a `LICENSE` file against the canonical text and only auto-detect above ~98% similarity. Any prose added to the file counts against that score, wherever it sits. Scored against canonical MIT on a licensee-style word-set similarity, this bundle's `LICENSE` measures **100%** as it now ships, about **93%** with a single explanatory line added above the title, and **80%** with a note wedged between the copyright line and the grant. The last of those is what shipped before this pass, and it silently cost the bundle its MIT badge. A helpful note inside `LICENSE` un-detects the licence it is trying to explain.

Nothing else in the bundle carries an identity.

## License

MIT — see [LICENSE](LICENSE).
