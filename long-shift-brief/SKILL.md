---
name: long-shift-brief
description: Sets up an AI coding agent to work for hours without stopping to ask. Interviews the user with 5 questions (finish line, self-test, gold standard, off-limits, run length), writes BRIEF.md, then works from TASKS.md, tests every change, keeps PROGRESS.md and follows safety rails. Use when the user wants an agent to run unattended, overnight, or "for hours", or says "brief the agent" or "long shift".
---

# Long-Shift Brief

Turn a one-line request into a brief an agent can follow for hours. The method is the same as
the free copy-paste prompt in `PROMPT.md`; this skill runs it for you.

## 1. Interview first

Scan the project before asking anything. Then ask these 5 questions in one message, each with
your recommended answer from what you found, so the user can reply `yes`:

1. **Finish line:** every piece of the end result, not just the first step.
2. **Self-test:** the exact command, build or page check you will run after every change.
3. **Gold standard:** the existing file, page or example to match.
4. **Off-limits:** files and actions never to touch. Always include sending messages, charging
   money, deleting data, publishing and deploying to production.
5. **Run length:** time budget and maximum passes (default 30).

Write the answers to `BRIEF.md`, show it, and start only after the user replies `yes`.

## 2. Work loop

- Break the finish line into ordered tasks in `TASKS.md`. Work one at a time.
- After every change, run the self-test. On failure, read the error, fix and re-run.
- Compare against the gold standard before marking a task done, then start the next task
  without asking.
- After each task, add 2-3 lines to `PROGRESS.md`: what changed, how it was tested, open doubts.
- Re-read `BRIEF.md` every 5 passes.

## 3. Safety rails

- Never delete, skip or weaken a test to make it pass. Log a suspect test and move on.
- Stop at the pass limit even if tasks remain.
- Stop and wait for the user before sending a message, charging money, deleting data,
  publishing or deploying.
- When blocked, log why in `PROGRESS.md` and move to the next task.

## 4. Hand-off

At the end, put a summary at the top of `PROGRESS.md`: tasks done, tasks left, every test result,
and decisions that need the user.
