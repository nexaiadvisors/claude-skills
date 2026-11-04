# Claude Skills

Five agent skills and a safety guardrails file for [Claude Code](https://claude.com/claude-code), released free under MIT.

All three were written for one person's daily use, then stripped of every machine-specific path,
name and private project reference so they run for anyone. Nothing to sign up for, no telemetry,
no dependency on the author's setup.

## The skills

### [`project-sweep`](project-sweep/) - what did I start and never finish?

Reads your agent session transcripts over a date window, reconstructs every project you worked
on, and hands back a ranked shortlist of what actually deserves your next working days.

The rule it is built on: **a transcript records what was *said* at one moment, and is never
evidence of where something stands now.** "I'll finish this tomorrow" is a lead, not a fact. So
every state claim is re-derived from the artifact itself - the commit, the branch, the running
deploy, the live URL - before anything is called unfinished. It also runs a skeptic pass that
assumes each candidate is already done and attacks it, and it reports coverage honestly, keeping
"checked, found nothing" separate from "could not check".

Read-only. It changes nothing.

### [`to-chips`](to-chips/) - split the work, run both lanes, merge

Routes each unit of a task to either a fresh background agent session (a "chip", each in its own
git worktree) or the session you are already in - then runs both lanes and merges the parallel
work back, running your tests.

It cuts chips with disjoint file ownership, pins every chip to one immutable base commit, detects
completion from disk rather than waiting on a notification, and deliberately refuses to
manufacture parallelism: a task with no genuine file-disjoint split becomes exactly one chip, not
four. It never pushes, opens PRs, or deletes branches. Chips are launched, not executed - a human
starts them, and that is the approval gate.

### [`verify-deploy-state`](verify-deploy-state/) - is my change actually live?

Answers "did it deploy?" with evidence instead of a green pipeline. It reads the running
service's own revision, the cloud resource's image and config, the git history behind that
image, and every path that can deploy the surface, then names the drift and the one next
action.

The rule it is built on: **staleness has no error state.** A build failure is loud; a deploy
that never fired is silent, because the old version keeps serving traffic and every health
check stays green. So the skill reads the running artifact, verifies a database by its objects
rather than its migration ledger, derives a frontend probe from what the diff emits, and keeps
"checked, found nothing" separate from "could not check".

Read-only. It changes nothing.

### [`long-shift-brief`](long-shift-brief/) - keep an agent working for hours

A 5-question interview that turns a one-line request into a brief an agent can follow
unattended: a finish line, a self-test it runs after every change, a gold-standard example, an
off-limits list and a pass limit. Ships as a copy-paste prompt (`PROMPT.md`) that works in
Claude Code, Cursor, Codex or ChatGPT's agent mode, and as a skill for Claude Code.

### [`agent-guardrails`](agent-guardrails/) - three rules for running an agent in production

A drop-in `CLAUDE.md` that holds a coding agent to three safety rules when it can run commands,
edit files and call tools for you: never take an irreversible action without a human yes, leave a
trail you can read afterward, and never accept a goal without a boundary on how it may reach it.
Each rule carries a one-line test. Not a skill, just a file to copy into your repo or your
`~/.claude/CLAUDE.md`.

### [`ai-crawler-audit`](ai-crawler-audit/) - can ChatGPT find and recommend your business?

Checks whether AI answer engines can reach your site and what they say about you. It asks
ChatGPT and Perplexity the questions your buyers ask (several times each, because answers
change), checks you are indexed on Bing and Google, tests whether AI crawlers are blocked by your
robots.txt, CDN or host, measures how much of each key page is readable without JavaScript, and
checks that your business name, contact details and facts match everywhere. It ranks findings by
2026 evidence, says plainly which popular tricks don't work (llms.txt, "best X" pages, FAQ schema
for citations), and only changes your site when you ask it to.

Built for owners of small service businesses who have heard "buyers ask ChatGPT now" and want to
know whether it can see them.

### [`expression-bank`](expression-bank/) - photos of you making any face, that still look like you

Give it 3-12 good photos of yourself and it makes the expressions you need for thumbnails, flyers
and video covers: surprised, skeptical, worried, excited, pointing, holding a phone, or anything you
describe. It grades your reference photos first and flags weak ones (too small, blurry, more than
one face, someone else) before spending anything. It generates with GPT Image and/or Gemini, scores
every face against your own photos with a free local face match, keeps only the ones that still
look like you, and hands back one labelled sheet. It refuses to run without your own API key,
without your consent that the face is yours, or over a \$3 cap. Setup: `expression-bank/references/setup.md`.

## Install

Copy either directory into your skills folder:

```
cp -R project-sweep       ~/.claude/skills/
cp -R to-chips            ~/.claude/skills/
cp -R verify-deploy-state ~/.claude/skills/
cp -R long-shift-brief    ~/.claude/skills/
cp -R expression-bank     ~/.claude/skills/
```

Then invoke with `/project-sweep`, `/to-chips`, `/verify-deploy-state` or `/long-shift-brief`. Each skill's own README covers prerequisites,
arguments, and how it degrades when an optional capability is missing.

## Feedback

These solve problems the author actually had, so they encode opinions. If one finds something you
had forgotten about, or if it gets something wrong, open an issue - that is the most useful thing
you can send back.

## License

MIT - see [LICENSE](LICENSE).
