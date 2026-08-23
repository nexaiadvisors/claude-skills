# project-sweep

An agent skill that reads your agent session transcripts over a date window, reconstructs every
project you worked on, verifies each one's **current** state against the artifact rather than the
transcript, and hands back a ranked shortlist of what actually deserves your next working days.

For anyone who runs a coding agent across many projects and has lost track of what got finished.

## What it does

- Builds a **complete inventory** of sessions in the window, split into cron/automated,
  worker/subagent, and human-driven. Every human-driven session must end up owned by a project or
  explicitly called noise — an unowned session is treated as a gap in the sweep, not a judgement call.
- **Verifies rather than believes.** A transcript records what was *said* at one moment. Every state
  claim is re-derived this run from the artifact: the branch, the PR, the running deploy, the signed
  document, the provider's Sent record, the tracker item.
- **Refutes its own conclusions.** A skeptic pass defaults to "this is already finished" and attacks
  each remaining candidate from angles the verifier did not use.
- **Ranks by stakes, not by volume.** An expiring five-minute filing outranks a large pile of
  half-finished code with no deadline and no user.
- Reports **coverage honestly**, keeping "checked, found nothing" separate from "could not check".

What it deliberately does **not** do:

- It does not change anything. No commits, pushes, merges, checkouts, worktrees, tracker updates or
  messages — every step is an observation.
- It does not estimate. A project whose verification tool is unavailable is reported as unverified,
  never given a softer verdict inferred from the transcript.
- It is not a fast "where was I on Tuesday" lookup. That question is answered far more cheaply by
  searching recent sessions directly. This skill is the expensive whole-portfolio audit.

## Prerequisites

Same list as the SKILL.md *Prerequisites* table — that file is the source of truth. SKILL.md
runs these as a preflight immediately before Phase 1, once `TRANSCRIPT_ROOT` has been located.

| Needs | Why | Check | If missing |
|---|---|---|---|
| A POSIX shell | every command | `command -v sh` | Stop. |
| `python3` | parses transcripts, portable date math | `command -v python3` | Stop. |
| `git` | verifies code claims | `command -v git` | Degrade: code state moves to COULD NOT CHECK. |
| A readable transcript store | the entire input | see Configuration | Stop. |
| `jq` (optional) | faster field probing | `command -v jq` | Degrade: use the `python3` probe. |
| Forge CLI, e.g. `gh` (optional) | verifies PRs and CI | `gh auth status` | Degrade: PR/CI claims move to COULD NOT CHECK. |
| Tracker CLI (optional) | verifies tracker items | `command -v "$TRACKER_CMD"` | Degrade: tracker claims move to COULD NOT CHECK. |
| Mail/chat CLI (optional) | verifies a message was really sent | `command -v "$MAIL_CMD"` | Degrade: send claims move to COULD NOT CHECK. |
| Parallel sub-agents (optional) | fans out phases 2-4 | your agent's capability | Degrade: run slices serially, narrow the window, say so. |

The skill assumes **no specific agent product**. It discovers the transcript store and probes its
format at runtime, and supports JSONL-per-session, JSON-array-per-session, and text/Markdown
transcripts, plus stores exposed as a search API instead of files.

## Install

```sh
# user scope — available in every project
git clone <repo-url> ~/.claude/skills/project-sweep

# project scope — checked in, shared with a team
git clone <repo-url> .claude/skills/project-sweep
```

Replace `~/.claude/skills` with your agent's own skills directory if it differs. Copying the
directory works just as well as cloning it. Three files ship, and only the first is read at run
time:

| File | Role |
|---|---|
| `SKILL.md` | the skill itself — the only file the agent loads |
| `README.md` | this document: what it does, how to configure it, what it does not verify |
| `LICENSE` | MIT |

## Configuration

Everything is an environment variable. No secret belongs in any of them — the optional integrations
are named by *command* and authenticate however they already do on your machine.

| Value | Env var | Default | Required | How to find yours |
|---|---|---|---|---|
| Transcript store | `TRANSCRIPT_ROOT` | none | **yes** | run the discovery loop in SKILL.md → *Locating the transcript store* |
| Working notes dir | `SWEEP_WORKDIR` | `mktemp -d` | no | any writable path outside the repos being audited |
| Repo search roots | `CODE_ROOTS` | `$HOME` | no | the directories your checkouts live under, **one per line** (not space-separated — roots such as `~/Library/Application Support` contain spaces) |
| Tracker CLI | `TRACKER_CMD` | unset (lane off) | no | the command you file work items with |
| Mail/chat CLI | `MAIL_CMD` | unset (lane off) | no | must be able to read your **Sent** record, not just send |

Window and shortlist size are passed at invocation: `--days N`, `--days=N`, or
`YYYY-MM-DD..YYYY-MM-DD` for the window, and `--top N` or `--top=N` for the shortlist (default
30 days, top 5). Every one of those five spellings is parsed by the argument block in SKILL.md →
*Locating the transcript store*, which resolves them to `$SINCE`, `$UNTIL` and `$TOP`; the two
window forms are mutually exclusive, and anything malformed — including a flag whose value is
missing or empty — exits 2 with a named reason rather than sweeping a wrong window silently.

## Worked example

```
$ export TRANSCRIPT_ROOT="$HOME/.<your-agent>/sessions"
$ export CODE_ROOTS="$HOME/src
$HOME/work"                          # one root per LINE - roots may contain spaces
$ export MAIL_CMD=<your-mail-cli>    # turns the outbound-message lane ON
> /project-sweep --days 30 --top 5
```

Trimmed output:

```
COVERAGE FIRST — 214 session files in window, 168 top-level, 46 subagent.
  buckets: cron 31 (1 row) | worker 46 | human-driven 91
  format: jsonl; fields role/timestamp/cwd/content all present
  lanes ON:  mail (MAIL_CMD set)
  lanes OFF: tracker (TRACKER_CMD unset), signature provider (none installed)
  could-not-check roster at the end of this section

TOP 5
1. invoice-portal  (business)  — client billing for Q3 work
   VERIFIED: unsent. `<mail-cli> sent --search invoice > log 2>&1` → EXIT=0, 0 rows.
   That is "checked, found nothing", not "could not check" — the mail lane is ON above.
   The transcript contains a finished draft; the Sent record does not.
   Remains: send it. Size: 5 min. Ranks #1 — money sitting still, no blocker.
2. auth-rewrite  (code)  — session-cookie migration
   VERIFIED: unmerged. `git -C ~/src/auth cherry origin/main feat/cookie` → 6 unshipped
   patches (rev-list said 19 — rebases inflate it). CI green, never deployed: the live
   /health gitSha is 4 commits behind the default branch. Remains: deploy. Size: ~1h.
...

FULL INVENTORY — 23 projects
| project | bucket | last activity | status | evidence |
| auth-rewrite | code | 2026-08-19 | in progress | 6 unshipped patches (git cherry) |
| docs-site | code | 2026-08-02 | shipped | merged 3f21a90, live sha matches |
| vendor-contract | business | 2026-07-30 | could not check | no signature-provider CLI |
...

RULED OUT — 6
- log-pipeline: looked stalled; landed as a squashed commit under a different branch name.

COVERAGE / COULD NOT CHECK — 3        (sub-block of COVERAGE, not a fifth section)
- vendor-contract: no signature-provider access. Reported unverified, NOT reported as open.
- two tracker items: TRACKER_CMD unset.
```

The shape that matters: every status cell names the command that produced it, and the two failure
categories never merge.

## Limitations and blast radius

- **Writes:** only its own working notes under `SWEEP_WORKDIR`. Nothing inside any repo it inspects.
- **Reads:** your full session transcripts. The inventory files it produces are as sensitive as the
  transcripts — they can contain anything you ever pasted into an agent. Keep `SWEEP_WORKDIR` out of
  any repo you publish.
- **Network:** none of its own. Optional verification steps call out through CLIs you already
  authenticated. It never authenticates and never handles a credential.
- **Cost:** high. It reads metadata for every session in the window and runs one verifier per
  distinct project. A 30-day window over a busy machine is a long run; start with `--days 7`.
- **Accuracy ceiling:** the sweep can only be as complete as the store you point it at. A second
  transcript store, or a search API that caps or ranks its results, yields a confident-looking sweep
  of part of your work. The skill makes you state which store you chose and why, but it cannot know
  what it was never shown. Two concrete ways a store hides: it may sit outside `~/.*` (for example
  under `~/Library/Application Support` or `~/.local/share`), and it may shard sessions by date
  (`sessions/YYYY/MM/DD/`) deeper than a shallow scan reaches. Discovery covers both, and the depth
  self-check in SKILL.md reports, per format, how many files a shallow scan would have missed — on
  the machine this was written on, a date-sharded store reported `.jsonl: depth-4 sees 47 of 1659`.
- **Degraded fields:** stores without a per-event timestamp fall back to file mtime, and every
  window decision then becomes approximate. Stores without a working-directory field force project
  attribution from directory names and first prompts.
- **Tested scope, precisely.** All eight shell blocks in SKILL.md pass `/bin/bash -n` under bash
  3.2.57, and seven of them were executed on macOS under that same `/bin/bash` — the eighth is a
  two-line `CODE_ROOTS=` illustration with nothing to run. Every count below was measured on one
  machine on 2026-08-22; the transcript stores are live and grow, so re-running will not reproduce
  the totals to the digit.
  - *store discovery* — run against a real home directory; surfaces roots under both
    `~/Library/Application Support` and `~/.local/share`, and took 26s.
  - *depth self-check* — run against a date-sharded store (`.jsonl: depth-4 sees 47 of 1659`) and a
    per-project store whose sessions are partly nested (`.jsonl: depth-4 sees 1115 of 3487`). Both
    printed `DEPTH_SHORTFALL`. An unset or nonexistent root exits 2; an empty one exits 1.
  - *format probe* — run against five inputs. A real store, whose 200 sampled files came back as a
    mix of session files and text sidecars (185 JSONL to 15 text on the last run recorded here; the
    split moves, the mix does not) — that mix is exactly what a single-file probe misreads as a
    text store. A synthetic JSON-array store, 3 files of 1,103,625 bytes each. A Markdown store. An
    empty directory (exit 1). And an array whose first event alone exceeds the read window, which
    reports an instrument problem instead of guessing "text". An unwritable working directory exits
    2 rather than reporting an empty store — tested both by making its parent unwritable and by
    making the directory itself unwritable.
  - *window parser* — all four documented invocation forms (`--days N`, `--days=N`, a bare
    `YYYY-MM-DD..YYYY-MM-DD`, and no arguments at all), plus eleven rejected ones: five malformed
    (`--days abc`, `--top x`, an unknown flag, `--days` together with a range, and a reversed
    range) and six with a missing or empty value (`--days`/`--top` as the final argument,
    `--days=`/`--top=`, and an explicit empty value). All eleven exit 2 with a named reason; none
    of them hangs.
  - *repo resolution* — run against a root whose path contains a space, which the preceding
    word-splitting form silently resolved to zero repos where the newline form finds them. Its
    depth cap was removed after measuring: `-maxdepth 4` over `$HOME` found 130 checkouts where the
    uncapped, pruned scan found 265, and the capped scan reported no error.
  - *preflight* — run with `TRANSCRIPT_ROOT` set (silent, exit 0) and unset
    (`MISSING_CONFIG:TRANSCRIPT_ROOT`).

  What is **not** tested: the full five-phase sweep end to end, any non-macOS shell, and every
  optional verification lane (forge, tracker, mail), which have no default implementation here by
  design. Treat those as unverified.

## License

MIT — see [`LICENSE`](LICENSE). Copyright is held by "The project-sweep Authors"; if you fork this,
put your own name or organisation there. Note that a `license:` line in a SKILL.md frontmatter is a
label, not a grant — the `LICENSE` file is what actually conveys the rights.
