---
name: project-sweep
description: "Sweeps agent session transcripts, verifies projects against artifacts, ranks what to finish. Use for 'what did I never finish'."
argument-hint: "[--days N | YYYY-MM-DD..YYYY-MM-DD] [--top N]"
compatibility: "Any OS with a POSIX shell, git, and python3. Read-only. Makes no network calls of its own; the verification phase uses whatever CLIs you already have authenticated."
---

# Project Sweep

## Overview

Reads agent session transcripts over a window, reconstructs every project and initiative that was
worked on, checks each one's **current** state against the artifact rather than the transcript, and
returns a ranked shortlist of what deserves the next working days.

This is the expensive, whole-portfolio audit. If the question is "where was I in that one thing I
paused on Tuesday", a targeted search of recent sessions answers it for a fraction of the cost —
reach for this skill only when the question is "across everything I touched, what is genuinely
unfinished and which few matter", because it verifies every candidate against reality and returns a
ranked, evidence-backed portfolio review.

## Blast radius — read before running

- **Read-only against your work.** It never commits, pushes, merges, checks out, closes a tracker
  item, sends a message, or creates a worktree. Every verification is an observation.
- **It writes only its own working notes**, to `$SWEEP_WORKDIR` (default: a fresh `mktemp -d`).
  Nothing is written inside any repo it inspects.
- **It reads your session transcripts**, which may contain anything you have ever pasted into an
  agent. Treat the inventory files it produces as being as sensitive as the transcripts themselves.
- **Network:** none from the skill itself. Verification steps you enable may call out through CLIs
  you have already authenticated (`git fetch`, `gh`, a deploy CLI, a mail CLI). It never
  authenticates anything, and never enters a credential.

## When to Use This Skill

**Trigger phrases:**
- "what did I start and never finish"
- "sweep my sessions / audit my in-flight work"
- "what should I take to completion this week"
- "review my projects across the last N days"
- "where did my time go and what is still open"

---

## Prerequisites

| Needs | Why | Check | If missing |
|---|---|---|---|
| A POSIX shell | every command below | `command -v sh` | **Stop.** Nothing here runs without one. |
| `python3` | parses transcripts and does date math portably | `command -v python3` | **Stop.** "This skill needs `python3` on PATH." |
| `git` | Phase 3 verifies code claims against real branches | `command -v git` | **Degrade:** every code-state claim moves to COULD NOT CHECK. Do not infer state from the transcript instead. |
| A readable transcript store | it is the entire input | see **Locating the transcript store** | **Stop.** "Set `TRANSCRIPT_ROOT` to the directory holding your agent's session files." |
| `jq` (optional) | faster field probing than `python3` | `command -v jq` | **Degrade:** use the `python3` probe below. No loss. |
| `gh` or another forge CLI (optional) | verifies pull requests and CI | `gh auth status` | **Degrade:** PR/CI claims move to COULD NOT CHECK, named as such. |
| A tracker CLI (optional) | verifies tracker items | `command -v "$TRACKER_CMD"` | **Degrade:** tracker claims move to COULD NOT CHECK. Never assume an item is open because you saw it mentioned. |
| A mail/chat CLI or API (optional) | verifies that a promised message was actually sent | `command -v "$MAIL_CMD"` | **Degrade:** outbound-message claims move to COULD NOT CHECK. A draft in a transcript is never evidence of a send. |
| Parallel sub-agents (optional) | Phases 2-4 fan out | your agent's own capability | **Degrade:** run the slices sequentially, narrow the window, and say the run was serial. |

---

## Configuration

| Value | Env var | Default | How to find yours |
|---|---|---|---|
| Transcript store | `TRANSCRIPT_ROOT` | *(required)* | see the discovery loop below |
| Window | `--days N`, `--days=N`, or `YYYY-MM-DD..YYYY-MM-DD` | 30 days | parsed by the argument block below; resolves to `$SINCE`/`$UNTIL` |
| Shortlist size | `--top N` or `--top=N` | 5 | parsed by the same block; resolves to `$TOP` |
| Working notes dir | `SWEEP_WORKDIR` | `mktemp -d` | any writable path outside the repos being audited |
| Repo search roots | `CODE_ROOTS` | `$HOME` | the directories your checkouts actually live under; **one per line**, so roots may contain spaces |
| Tracker CLI | `TRACKER_CMD` | *(unset — lane off)* | the command you file work items with |
| Mail/chat CLI | `MAIL_CMD` | *(unset — lane off)* | the command that can read your **Sent** record, not just send |

No secret ever belongs in this table or in this file. The optional lanes are named by **command**,
and they authenticate however they already do on your machine.

---

## Locating the transcript store

Agent CLIs do not agree on where sessions live or what they look like, so **discover it, do not
assume it.** Three shapes cover nearly everything in the wild:

| Shape | Looks like | Read it by |
|---|---|---|
| **JSONL per session** | one file per session, one JSON object per line, one line per event | read line by line; never load the file whole |
| **JSON array per session** | one file per session containing a single array of events | stream-parse, or read and slice |
| **Text/Markdown per session** | a transcript rendered as prose with speaker headers | regex the speaker headers; expect the least metadata |

Sessions are usually grouped in a directory per project, and that directory name is often a
mangled form of the path where the session started. **A store may also be a database or a
search API rather than files** — if your agent exposes session search as a tool or endpoint, use
that and record in COVERAGE that you used it, because its result set may be capped or ranked
rather than exhaustive.

**Discovery — the candidate roots on this machine:**

```sh
{                                            # newline-delimited: these paths contain spaces
  printf '%s\n' "$HOME"/.*/
  printf '%s\n' "$HOME/Library/Application Support"/*/      # macOS app data
  printf '%s\n' "$HOME/.local/share"/*/                     # XDG data dir (Linux, and some macOS)
} | while IFS= read -r d; do
  [ -d "$d" ] || continue                    # an unmatched glob stays literal; it is not a dir
  b=${d%/}; b=${b##*/}
  case "$b" in .|..) continue ;; esac        # the "$HOME"/.*/ glob matches . and .. — skipping them
  n=$(find "$d" -maxdepth 8 \
       \( -name node_modules -o -name .git -o -name Cache -o -name Caches \) -prune -o \
       -type f \( -name '*.jsonl' -o -name '*.json' -o -name '*.md' -o -name '*.txt' \) -print \
        2>/dev/null | wc -l | tr -d ' ')
  [ "${n:-0}" -ge 20 ] && printf '%8d  %s\n' "$n" "$d"
done | sort -rn | head -8
```

Expect this to take tens of seconds; it is a one-time scan and the cost buys completeness.

Three details in that loop are load-bearing, and each one is a store you would otherwise never see:

- **Depth.** Stores that date-shard their sessions — `sessions/YYYY/MM/DD/session.jsonl` — put the
  files at depth 5, one past a `-maxdepth 4` cap. On the machine this was written on, one such store
  held **1659** session files and a depth-4 scan saw **47** of them: 2.8%, with no error and no empty
  result to warn you. The scan is capped at 8 rather than uncapped so it cannot wander into a
  multi-gigabyte cache, and the heavy directories are pruned by name.
- **Roots that are not dotdirs.** `"$HOME"/.*/` alone can never match
  `~/Library/Application Support/` — the standard place for application data on macOS — nor
  `~/.local/share/<app>/` on Linux. A store living there is invisible to the glob, not merely
  low-scoring.
- **Spaces.** The candidate list is newline-delimited and read with `IFS= read -r` precisely
  because `Application Support` contains one. A space-splitting loop turns that root into two
  nonexistent paths and, with `2>/dev/null`, reports nothing at all.

Skipping `.` and `..` is likewise not cosmetic: the glob matches both, and without the guard the
highest-scoring "candidate" is your entire home directory, followed by its parent.

Pick the one whose files open as sessions, and export it as `TRANSCRIPT_ROOT`. If several look
plausible, say which you chose and why — an agent product with two stores (say, a local one and a
synced one) will otherwise give you a sweep of half your work that looks complete.

**Then prove the depth cap is not still hiding files from the root you picked**, by comparing a
capped count against an uncapped one for that single directory:

```sh
[ -d "${TRANSCRIPT_ROOT:-}" ] || { echo "MISSING_CONFIG:TRANSCRIPT_ROOT" >&2; exit 2; }
tot_c=0; tot_a=0
for ext in jsonl json md txt; do              # all three supported formats, not just JSONL
  c=$(find "$TRANSCRIPT_ROOT" -maxdepth 4 -type f -name "*.$ext" 2>/dev/null | wc -l | tr -d ' ')
  a=$(find "$TRANSCRIPT_ROOT"              -type f -name "*.$ext" 2>/dev/null | wc -l | tr -d ' ')
  c=${c:-0}; a=${a:-0}
  [ "$a" -gt 0 ] && echo "  .$ext: depth-4 sees $c of $a"
  tot_c=$((tot_c + c)); tot_a=$((tot_a + a))
done
echo "depth-4 sees $tot_c of $tot_a session-shaped files under $TRANSCRIPT_ROOT"
[ "$tot_a" -gt 0 ] || { echo "NO_SESSION_FILES under $TRANSCRIPT_ROOT" >&2; exit 1; }
[ "$tot_c" = "$tot_a" ] || echo "DEPTH_SHORTFALL: every later count must use the uncapped form"
```

If the two totals differ, every later count must come from the uncapped form, and say so in
COVERAGE. This is the exact measurement that catches a shard layout.

It counts **every extension the discovery loop scored on**, not just `*.jsonl`. A `-name '*.jsonl'`
self-check passes silently on a JSON-array store and on a Markdown store — the two other formats
this skill claims to support — so the one instrument meant to catch a hidden shard layout would be
blind to two thirds of the stores it runs against. The per-extension lines are what make the total
readable: a store can be 90% sidecar `.md` files, and you should be able to see that before you
trust the ratio.

**Probe the format and learn the field names — never assume them:**

```sh
: "${SWEEP_WORKDIR:=$(mktemp -d)}"
mkdir -p "$SWEEP_WORKDIR" || { echo "UNWRITABLE_WORKDIR: $SWEEP_WORKDIR"; exit 2; }
find "$TRANSCRIPT_ROOT" -type f \
     \( -name '*.jsonl' -o -name '*.json' -o -name '*.md' -o -name '*.txt' \) \
     | head -200 > "$SWEEP_WORKDIR/sample.txt" \
  || { echo "UNWRITABLE_WORKDIR: $SWEEP_WORKDIR"; exit 2; }
[ -s "$SWEEP_WORKDIR/sample.txt" ] || { echo "NO_SESSION_FILES under $TRANSCRIPT_ROOT"; exit 1; }
python3 - "$SWEEP_WORKDIR/sample.txt" <<'PY'
import collections, json, pathlib, re, sys
HEAD = 1 << 20                       # 1 MiB of each file: enough to classify it and to map its fields
paths = [l.strip() for l in open(sys.argv[1]) if l.strip()]
fmts, keys = collections.Counter(), collections.Counter()
for sp in paths:
    with open(sp, "rb") as fh:
        raw = fh.read(HEAD).decode("utf-8", "replace")
    txt = raw.lstrip("\ufeff \t\r\n")
    lead, rows = txt[:1], []
    if lead == "[":                  # format comes from the FIRST byte, so file size cannot change it
        fmt = "json-array"
        dec, i = json.JSONDecoder(), 1
        while len(rows) < 200:       # decode events one at a time - never needs the whole array
            while i < len(txt) and txt[i] in " \t\r\n,":
                i += 1
            if i >= len(txt) or txt[i] == "]":
                break
            try:
                obj, i = dec.raw_decode(txt, i)
            except ValueError:
                break                # ran off the end of the head window - keep what we have
            rows.append(obj)
    elif lead == "{":
        fmt = "jsonl"
        for line in txt.splitlines():
            line = line.strip()
            if line and len(rows) < 200:
                try: rows.append(json.loads(line))
                except ValueError: pass
    else:
        fmt = "text"
    fmts[fmt] += 1
    for r in rows:
        if isinstance(r, dict): keys.update(r.keys())
print("sampled", len(paths), "files ->", dict(fmts))
dominant = fmts.most_common(1)[0][0] if fmts else "none"
if keys:
    print("keys seen (top 25):", [k for k, _ in keys.most_common(25)])
elif dominant == "text":
    raw = pathlib.Path(paths[0]).read_text(errors="replace")[:HEAD]
    heads = [l for l in raw.splitlines() if re.match(r"^\s*(#{1,4}\s|\*\*|>|\[)", l)][:8]
    print("text store - candidate speaker headers to regex:")
    for h in heads: print("   ", h[:100])
else:
    print("INSTRUMENT PROBLEM: files classified as", dominant, "but not one event decoded.")
    print("  Do NOT read this as a text store. Raise HEAD, or check read permissions.")
PY
```

Three details in that probe are load-bearing. It samples up to 200 files rather than the first one,
because session directories carry sidecar files - notes, memory files, exported summaries - and
the first match is regularly one of them; a single-file probe will report a JSONL store as text.

It reads a bounded head of each file but never lets that bound decide the answer. The format is
taken from the first non-whitespace byte, and events are decoded **one at a time** from that head,
so a 60 MB session classifies exactly like a 6 KB one. The earlier shape of this probe read a
400 KB slice and then asked `json.loads` to parse it whole: on the machine this was written on,
**1235 of 3487** `.jsonl` session files were larger than that (measured 2026-08-22; it is a live
store, so the totals move), and for an array-per-session store the parse failed on every one of
them, yielding zero keys — whereupon the probe advised regexing speaker headers out of a JSON file.
That is the worst failure an instrument has, because its output looks like a finding about your
data rather than a fault in the measurement.

The 1 MiB head is sized for the field mapping, not for a full read, and the 200-event ceiling is a
ceiling rather than a promise: on the store above it decoded a median of 47 events per file and hit
200 on only 38 of 186 JSONL files. That is enough, because key names converge in the first handful
of events — the run that produced those numbers still surfaced all four fields the sweep needs. If
you need event *counts* rather than field names, read the file properly; do not raise `HEAD` and
assume the sample became complete.

And `NO_SESSION_FILES` and `UNWRITABLE_WORKDIR` are separate exits on purpose: an unwritable
working directory that reports "no sessions" is a broken instrument wearing the costume of a
finding, and every downstream phase would inherit it as "you did no work in this window". The
final branch above exists for the same reason: "structured, but nothing decoded" is reported as an
instrument problem, never quietly downgraded to "text".

Map the four fields the sweep depends on, and **write the mapping into the report** so a reader can
tell a missing field from a missing project:

| Needed | Typical key names | If your store has none |
|---|---|---|
| speaker / role | `role`, `type`, `author`, `sender` | you cannot separate human from agent turns — Phase 1's bucket counts become estimates, say so |
| timestamp | `timestamp`, `ts`, `created_at`, `time` | fall back to file mtime **and flag every window decision as approximate** |
| working directory | `cwd`, `workspace`, `projectPath` | derive the project from the session's parent directory name and the first prompt, and name which you used |
| message text | `content`, `text`, `message` | you have metadata only; the gap hunt in Phase 2 gets much weaker |

**Parse the window and the shortlist size.** Five spellings are accepted and each has a code path
below; nothing downstream may invent a sixth. The window is `--days N`, `--days=N`, or a bare
`YYYY-MM-DD..YYYY-MM-DD`; the shortlist size is `--top N` or `--top=N`. Anything else — including a
flag whose value is missing or empty — exits 2 with a named reason rather than falling back to a
default, because a silently-defaulted window sweeps the wrong days and still looks complete. Seed
the positional parameters from the invocation (`set -- --days 7 --top 5`, or your agent's
equivalent) and run:

```sh
DAYS=""; RANGE=""; TOP=""
while [ $# -gt 0 ]; do
  case "$1" in
    --days)
      if [ $# -lt 2 ] || [ -z "$2" ]; then echo "MISSING_VALUE:--days" >&2; exit 2; fi
      DAYS="$2"; shift 2 ;;
    --days=*)
      DAYS="${1#--days=}"
      if [ -z "$DAYS" ]; then echo "MISSING_VALUE:--days" >&2; exit 2; fi
      shift ;;
    --top)
      if [ $# -lt 2 ] || [ -z "$2" ]; then echo "MISSING_VALUE:--top" >&2; exit 2; fi
      TOP="$2"; shift 2 ;;
    --top=*)
      TOP="${1#--top=}"
      if [ -z "$TOP" ]; then echo "MISSING_VALUE:--top" >&2; exit 2; fi
      shift ;;
    [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]..[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9])
      RANGE="$1"; shift ;;
    *) echo "BAD_ARG:$1" >&2; exit 2 ;;
  esac
done
if [ -n "$DAYS" ] && [ -n "$RANGE" ]; then
  echo "BAD_ARGS: --days and a date range are mutually exclusive" >&2; exit 2
fi
case "${TOP:-5}"  in ''|*[!0-9]*) echo "BAD_TOP:$TOP" >&2;   exit 2 ;; esac
case "${DAYS:-30}" in ''|*[!0-9]*) echo "BAD_DAYS:$DAYS" >&2; exit 2 ;; esac
TOP="${TOP:-5}"
```

The `[ $# -lt 2 ]` guard on each value-taking flag is load-bearing. Without it, `--days` as the
final argument sets `DAYS` to the empty string and runs `shift 2` with one positional left; `shift`
fails, shifts nothing, `$#` never reaches 0, and the loop spins forever on the same argument. It
does not error and it does not sweep the wrong window — it hangs, which is the one failure mode a
caller cannot distinguish from a slow scan of a large store.

**Date math portably.** `date -d '30 days ago'` is GNU and `date -v-30d` is BSD; a skill that picks
one silently sweeps the wrong window on half the machines it runs on. Resolve the window in
`python3` instead, and validate it:

```sh
if [ -n "$RANGE" ]; then
  SINCE="${RANGE%%..*}"; UNTIL="${RANGE##*..}"
else
  SINCE=$(python3 -c 'import datetime,sys;print((datetime.date.today()-datetime.timedelta(days=int(sys.argv[1]))).isoformat())' "${DAYS:-30}")
  UNTIL=$(python3 -c 'import datetime;print(datetime.date.today().isoformat())')
fi
python3 -c 'import datetime,sys
a,b=[datetime.date.fromisoformat(x) for x in sys.argv[1:3]]
raise SystemExit(0 if a<=b else 1)' "$SINCE" "$UNTIL" \
  || { echo "BAD_WINDOW: $SINCE..$UNTIL" >&2; exit 2; }
echo "WINDOW=$SINCE..$UNTIL TOP=$TOP"
```

Every later phase filters on `$SINCE`/`$UNTIL` and reports `$TOP` items, and the resolved window
goes into COVERAGE verbatim — a reader must be able to see which days were swept without
recomputing them.

---

## Preflight — run this last, immediately before Phase 1

It is placed here, after Configuration and after **Locating the transcript store**, because it
checks `TRANSCRIPT_ROOT` — and the section above is where you obtain one. Read this file top to
bottom and nothing is checked before it exists.

```sh
for c in python3 git; do
  command -v "$c" >/dev/null 2>&1 || echo "MISSING_BINARY:$c"
done
[ -n "${TRANSCRIPT_ROOT:-}" ] && [ -d "${TRANSCRIPT_ROOT:-/nonexistent}" ] \
  || echo "MISSING_CONFIG:TRANSCRIPT_ROOT"
command -v jq >/dev/null 2>&1 || echo "DEGRADED:jq(optional)"
gh auth status >/dev/null 2>&1 || echo "DEGRADED:forge-cli(optional)"
```

If a `MISSING_BINARY` or `MISSING_CONFIG` line prints, stop and quote that row's "If missing" cell.
Every `DEGRADED` line must be carried into the final COVERAGE section by name. Do not start a
partial run silently, and never substitute a transcript for a missing verification tool — that is
the one failure this skill exists to prevent.

---

## The one rule that makes this work

**A transcript is a record of what was SAID at one moment. It is never evidence of current state.**

"I'll finish X" and "next step is Y" are *leads*. Every claim about where something stands must be
re-derived from the artifact itself this run: the commit, the branch, the PR, the deploy record,
the file, the tracker item, the provider's Sent folder, the live URL.

This holds for a repo's own docs too. A `DEPLOY.md` that says "production is 16 commits behind" is
a record of what someone typed on a date, exactly like a transcript. Check it.

It holds for the transcript store's own metadata as well: a filename, a directory name and an mtime
are all statements made by the tool that wrote them, at a moment that is not now.

---

## Workflow

### Phase 1 — Inventory (cheap, mechanical)

1. List sessions under `TRANSCRIPT_ROOT` whose **last message** falls in the window. File mtime is
   not the same as content date — a resumed session is touched long after its content ends, and a
   store that syncs or re-writes files touches all of them.
2. Separate top-level sessions from subagent/workflow transcripts. Build the inventory from
   top-level sessions; the rest are supporting detail. If your store does not distinguish them, a
   very short session whose first prompt is templated is almost always a subagent.
3. For each session extract: working directory, branch, first human prompt, last agent message,
   turn counts, first/last timestamp. Never load whole transcripts into context.
4. Classify every session into one of three buckets and report the counts:
   - **cron/automated** — scheduled or repeating lanes, if you run any. Collapse to ONE inventory row.
   - **worker/shell** — subagent shells and loop workers, identifiable by a templated opening
     prompt or very few human turns. Execution detail, not initiatives.
   - **human-driven** — the real work. This set is the completeness checklist.
5. Write the human-driven list to a file in `$SWEEP_WORKDIR`. Every row must end up owned by some
   project in the final inventory, or be explicitly called noise. An unowned row is a gap, not a
   judgement call.

**Naming trap:** a transcript's directory is where the session *started*; its working directory is
where it ended up after a `cd`. They often differ, so the same session can appear under two names.
Prefer the working directory, and never count it twice.

### Phase 2 — Reconstruct (parallel)

Fan out readers over disjoint slices of the inventory — by repo, by domain, and one slice whose job
is the **gap hunt**: find any human-driven session no other slice owns, and read its ending.

Without sub-agents, run the same slices sequentially over a narrower window rather than skipping
the gap hunt. The gap hunt is what makes the inventory a checklist instead of a sample; dropping it
turns a "complete portfolio review" into "the projects I happened to notice", which is the failure
this skill is supposed to prevent.

Each reader returns, per project: name, bucket (code / business / personal), one line on what it is,
last activity date, the transcript paths that evidence it, what the transcripts *claim*, whether it
looks unfinished, and **the specific check that would settle it**.

"Project" means anything with an outcome being driven — not only code repos. Business and personal
initiatives count, and they routinely outrank code.

### Phase 3 — Verify (the expensive, load-bearing phase)

One verifier per distinct project. Merge by substance before this phase, not by string: slices name
the same thing differently, and verifying the same project three times wastes the budget.

Each verifier answers "what is TRUE now" and names the exact command and its output:

| If it is... | Verify by |
|---|---|
| code | is it on the default branch, on an unmerged branch, or nonexistent — and is it DEPLOYED |
| a deploy | read the running artifact's own identity, or a behavioural property. Green CI never proves a deploy shipped |
| an outbound message | read it back from the provider's record. A draft in a transcript is not a sent thing |
| a document/agreement | the signed copy, or the provider's completion record |
| a tracker item | is the underlying defect still present in the code, or is the item stale |
| anything dated | state the date and the days remaining from today |

Rows whose tool you do not have are **not** verified by reading the transcript harder. They go to
COULD NOT CHECK with the reason ("no forge CLI authenticated"), and the project stays on the list
labelled unverified. An unverifiable project is a known unknown; a transcript-derived claim is a
false certainty, which is worse.

**Finding the repo.** Resolve each code project to a checkout before verifying it, and never guess:

```sh
printf '%s\n' "${CODE_ROOTS:-$HOME}" | while IFS= read -r root; do
  [ -n "$root" ] || continue
  [ -d "$root" ] || { echo "MISSING_CODE_ROOT:$root" >&2; continue; }
  find "$root" \
       \( -name node_modules -o -name Cache -o -name Caches -o -name .Trash \) -prune -o \
       -type d -name .git -print -prune 2>/dev/null
  n4=$(find "$root" -maxdepth 4 \
       \( -name node_modules -o -name Cache -o -name Caches -o -name .Trash \) -prune -o \
       -type d -name .git -print -prune 2>/dev/null | wc -l | tr -d ' ')
  echo "DEPTH4_WOULD_SEE $root ${n4:-0}" >&2          # the self-check, not the answer
done | sed 's|/\.git$||' | sort -u
```

**No depth cap here either** — the same argument as the transcript store applies, and it is not
hypothetical. A `-maxdepth 4` scan of `$HOME` on the machine this was written on found **130** repo
checkouts; the uncapped scan above found **265** of the same kind, so the capped form saw 49% of
them and reported no error. The 135 it missed were not junk: reference checkouts vendored inside
another project, plugin marketplaces cloned under an agent's own config directory, and archived
work nested a few levels down — 46 of the 135 had a space somewhere in their path. Every one of
them would have come back "no checkout found" and been filed as COULD NOT CHECK, or worse,
silently skipped.

The cost of removing the cap is bounded by pruning rather than by depth: the heavy directories are
skipped by name, and `-print -prune` stops `find` from descending into a `.git` directory once it
has been counted. Capped took 0.5s and uncapped 9.4s over the same `$HOME`. If your roots are much
larger, narrow `CODE_ROOTS` — do not put the cap back, because a narrower root is a stated choice
and a depth cap is a silent one.

The self-check is the second `find` in the block above. It is the shallow scan, so it costs about
half a second next to the real one, and it prints `DEPTH4_WOULD_SEE <root> <n>` to stderr for every
root. Put that number next to the repo total in COVERAGE: if they differ, a reader can see exactly
how much a capped scan would have hidden, instead of taking this section's word for it.

`CODE_ROOTS` is **newline-delimited, one root per line**, and the loop reads it with `IFS= read -r`:

```sh
CODE_ROOTS="$HOME/src
$HOME/Library/Application Support/some-tool"
```

Splitting that value on whitespace instead — `for root in ${CODE_ROOTS:-$HOME}` — is the failure
this replaces. A root containing a space becomes two nonexistent paths, `find` writes two "No such
file or directory" lines that `2>/dev/null` discards, the loop exits 0, and the output is empty:
every repo under that root is silently absent from the sweep. That is why a missing root is
announced as `MISSING_CODE_ROOT` here rather than swallowed — an empty result must never be able to
mean two different things.

Then run every git command as `git -C "$REPO" ...` so the sweep cannot act on whatever directory it
happens to be sitting in.

**Probe power.** Choose the probe *after* looking at what actually changed, and say out loud what
its power is: "this only moves if the change touches X". A probe that cannot move is not evidence.
Prefer behavioural probes ("the page now returns noindex") over identity ones (hashes, counts).

**Unmerged branch counts.** `rev-list --count base..branch` and `cherry base branch` answer
different questions — raw commits ahead vs commits whose patch is not already upstream. Rebases and
merges make the first number several times larger. Report the second for "unshipped work", and say
which you used.

**Read exit codes, not pipes.** `cmd 2>&1 | tail -5` returns `tail`'s status, always 0, and so does
a trailing `; echo done`. Run each verification as `cmd > log 2>&1; echo "EXIT=$?"` and read the
log's substance. A verification whose exit code you never saw did not happen.

### Phase 4 — Refute (adversarial)

For every project still called unfinished, run a skeptic whose default is `refuted: true`. Attack
from angles the verifier did not use: did it land under a different branch or a squashed commit; was
the message sent from the *other* account or a different channel; did a later session in the window
already finish it; was it deliberately dropped; is the "defect" the documented intended design.

Channel-scoped absence is not absence. "No email" is a fact about that mailbox.

### Phase 5 — Rank and report

Rank by what deserves the next working days, in this order of weight:

1. A hard external deadline or a legal/financial clock about to expire.
2. Money or legal exposure sitting still — unsigned, unsent, unfiled, unbilled, undeployed revenue code.
3. A live user-facing defect on something real people touch right now.
4. Nearly-done work where a small push converts a large sunk cost into a shipped thing.
5. Everything else.

A large pile of half-finished code with no deadline and no user ranks **below** a five-minute filing
that expires. Session volume measures where the hours went, not where the value is left — the repo
with the most sessions is usually the healthiest, not the neediest.

Say why each item ranks where it does, including why the ones just below the cut missed.

---

## Output Format

1. **TOP N** — ranked. Each: name and bucket; one line on what it is; verified state *with the check
   that established it*; exactly what remains; the single next action; rough size.
2. **FULL INVENTORY** — table of every project touched: name, bucket, last activity, status
   (shipped / in progress / stalled / abandoned / could not check), one-line evidence.
3. **RULED OUT** — what looked unfinished but is done or was deliberately dropped, plus the check
   that settled it.
4. **COVERAGE** — how many transcripts and repos were actually read, what could not be read, which
   optional lanes were off and what that blinded, the transcript field mapping you used, and
   anything unchecked that would change the ranking. Keep **"checked, found nothing"** separate from
   **"could not check"**; report any verification step that failed rather than dropping its subject.
   When the could-not-check roster is long, print it as a labelled sub-block of this section
   (`COVERAGE / COULD NOT CHECK`) rather than promoting it to a fifth top-level section — it is
   coverage reporting, and separating it from the lanes that caused it is how it gets skimmed past.

There are **four** sections. Do not add a fifth. You may additionally lead the report with a short
COVERAGE summary line before TOP N — a reader needs to know what was and was not swept before they
read a ranking — as long as the detailed roster stays in section 4.

---

## Anti-rationalization

| Thought | Reality |
|---|---|
| "The transcript says it was finished." | That is what was said, not what is. Check the artifact. |
| "CI is green, so it shipped." | Green CI proves a build, not a deploy. Read the running revision. |
| "No results, so there's nothing there." | An empty result is a claim about your instrument first. Prove the instrument. |
| "The repo's docs say it's blocked." | Docs are dated statements like transcripts. Verify them too. |
| "This repo has the most sessions, so it needs the most work." | Volume is where hours went. Rank on stakes. |
| "It's a big deal, it should be top five." | Ask whose move is next. Externally blocked is not actionable. |
| "I'll skip verifying the small ones." | The five-minute expiring item usually outranks the multi-day pile. |
| "Some checks failed; I'll leave them out." | A dropped unverifiable item is the one that bites. Label and report it. |
| "I don't have that CLI, so I'll judge from the transcript." | That is the one substitution the skill forbids. Missing tool means COULD NOT CHECK, not a softer verdict. |
| "The store I found had plenty of sessions in it." | Plenty is not all. A second store, or a capped search API, gives you a confident sweep of half your work. |
| "The dates looked right." | mtime is not content date, and `date -d` is not `date -v`. State which you used. |

---

## Quality Checklist

- [ ] Preflight run; every missing or degraded dependency named in COVERAGE
- [ ] `TRANSCRIPT_ROOT` chosen deliberately, with the reason recorded when several were plausible
- [ ] Depth self-check run on the chosen root, and any shallow-scan shortfall reported in COVERAGE
- [ ] Transcript format probed and the field mapping recorded, not assumed
- [ ] Window filtered on message content date, not file mtime — or the fallback disclosed
- [ ] Sessions classified into cron / worker / human-driven, with counts reported
- [ ] Every human-driven session owned by a project or explicitly called noise
- [ ] Gap hunt performed, in parallel or serially
- [ ] Projects merged by substance before verification
- [ ] Every state claim names the command that produced it and the exit code it returned
- [ ] Deploys verified by the running artifact's identity or behaviour
- [ ] Outbound messages verified from the provider's own record
- [ ] Probe power stated where a probe was used
- [ ] Failed, skipped and lane-off verifications disclosed, not dropped
- [ ] "Checked, found nothing" kept separate from "could not check"
- [ ] Read-only: no repo, branch, tracker item, message, or worktree modified
