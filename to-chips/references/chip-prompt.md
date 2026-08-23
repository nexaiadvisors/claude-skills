# Chip prompt template

Every chip prompt is a cold-start, self-contained brief: the chip session has NO
access to the originating conversation. Inline every fact it needs. Fill every
`<...>` before launching - including the literal `<base_commit>` SHA and the
literal absolute `<state-dir>` path - and delete sections that have no real
content.

ASCII-only typography in the prompt text (plain hyphens, straight quotes). Smart
quotes and en-dashes survive a copy-paste badly and can break a shell command
the chip is meant to run verbatim.

````text
# Chip <N>/<M>: <chip title>
Run: <run-id>  |  Part of: <task title>

You are one of <M> parallel agents, each in its own git worktree of <repo-name>.
Your worktree branch may have been forked from the repo's default-branch HEAD,
which is NOT the base this work builds on - or it may already sit on that base,
if the worktree was created by hand at the base commit. Your FIRST action is the
same either way: move onto the exact base commit (a real move in the first case,
a no-op in the second; your branch is fresh, so this is safe and cannot
conflict):

    git cat-file -e <base_commit>^{commit} && git reset --hard <base_commit>

Then confirm `git rev-parse HEAD` prints <base_commit>. If the cat-file check
fails (commit not found), do NOT improvise with fetch or merge - stop and
follow the blocker protocol below.

## Project context (shared by all chips)
<one paragraph: what the overall task is, the repo, stack, hard constraints,
conventions the team follows - style, test framework, commit format>

## Your goal (this chip ONLY)
<one objective sentence>

<detailed instructions for this chip's work>

## Claims to confirm before editing (leads, not facts)
<Delete this section only if it is genuinely empty. Anything below is a LEAD
about what the code currently contains, NOT a verified fact. For each one, run
its confirm command FIRST; if it does not reproduce, change nothing for that
item, mark it not-present, and say so in your hand-back notes. Never edit on an
unconfirmed claim.>
- <claim, e.g. the literal string `foo-bar` appears in src/x.tsx> - confirm
  with: `<exact command>`

## File ownership (hard boundary)
- You may create/edit ONLY: <owned paths>
- You may READ anything, but must NOT edit: <forbidden shared files - barrel
  exports, route tables, lockfiles, sibling chips' paths>. Wiring into shared
  files happens at integration, after all chips merge. If your work seems to
  require editing a forbidden file, write the request into
  <owned path>/INTEGRATION-NOTES.md instead and continue. That file is executed
  verbatim at integration, so make each entry actionable:
  "<file> -> <exact change>", one per line.

## Blocker protocol
If you hit any blocker you cannot resolve inside your owned paths (base commit
missing, a dependency that does not exist, the goal infeasible as specified):
stop working, commit whatever is coherent so far, then do the hand-back below
with status "needs_attention" and the reason in notes. NEVER edit forbidden
files to unblock yourself, and never sit silent - a handed-back blocker is
useful; a stalled chip is not.

## Done when
<checkable criteria>
Verify with: `<per-chip verify command>` - it must pass before hand-back.
Take the exit code from that command itself, on its own line
(`<cmd> > verify.log 2>&1; echo "EXIT=$?"`). A pipe returns the pipe's status,
not the command's, and a trailing diagnostic overwrites it.

## Hand-back contract (do this LAST, in order)
1. Run the verify command above; fix failures until it passes. If you cannot
   make it pass, use status "needs_attention" in step 3 and say why.
2. Commit ALL your work on your current branch. The FINAL commit message must
   end with this marker, VERBATIM on one line (discovery greps for the exact
   fixed string - do not rephrase, wrap, or escape it):
   [to-chips:<run-id>:chip-<N>]
3. Write your result file:

       mkdir -p <state-dir>/<run-id>/ledger

   then create <state-dir>/<run-id>/ledger/chip-<N>.json :

   {
     "chip": "chip-<N>",
     "branch": "<output of: git rev-parse --abbrev-ref HEAD>",
     "status": "<done or needs_attention>",
     "verify": "<verify command> -> <pass or fail>",
     "notes": "<1-3 lines: what you built, anything integration must know>"
   }

4. Tell the user: this chip is done. The launching session is watching for all
   chips to finish and will auto-merge and test once they have - no action
   needed here (the user can say "done" in that session to force it early).

Do NOT merge into <base_branch> yourself. Do NOT push. Do NOT open a PR. Do NOT
switch branches. The originating session owns integration.
````

## Composition rules

- **A claim about the code is a lead until you have run the command.** Any
  literal string, token kind, occurrence count, or defect list you did not
  confirm this turn goes in "Claims to confirm before editing" with its own
  exact command - never into the instructions as a fact. A cold agent cannot
  tell a verified claim from a remembered one and will edit on it. Measured
  failure: a 12-defect brief asserted a Tailwind class `bg-f5e6d3` in a file
  that already read `bg-[#f5e6d3]`, and called `shadow-container` a
  design-system boxShadow token when it was a plain CSS class injected at
  runtime by a style component - "fixing" it would have shipped a drop shadow
  that never existed. Two of twelve items were fiction.
- **Cold-agent test:** read the finished prompt pretending you have never seen
  the conversation. Any "see above", missing path, unfilled `<...>`, or
  unstated convention fails the test - fix it before launching.
- **Same conventions in every chip** (verbatim-identical context and conventions
  sections) so parallel work merges cleanly.
- **Per-chip verify must be runnable inside the chip's worktree** and scoped to
  its owned paths (targeted tests, typecheck) - the full suite runs at MERGE. A
  fresh worktree has no `node_modules` of its own, so a verify command that
  depends on installed dev dependencies must either install them or be scoped
  to something that does not need them.
- **The marker and ledger path are load-bearing.** MERGE-mode discovery depends
  on the exact strings `[to-chips:<run-id>:chip-<N>]` and
  `<state-dir>/<run-id>/ledger/chip-<N>.json`, matched with a fixed-string
  grep. Never paraphrase them, and never leave `<state-dir>` unexpanded - the
  chip session does not inherit the launching session's environment.
- **The base_commit SHA is load-bearing too.** Inline the full SHA; every chip
  resets to the same immutable commit, so all chips share a byte-identical base
  no matter when each one is started.
