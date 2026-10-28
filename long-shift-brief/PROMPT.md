# The Long-Shift Agent Brief

A copy-paste prompt that turns a 90-second AI chat into a multi-hour work shift.
From David He, NexAI Advisors (nexaiadvisors.com). Free to use and share.

**Works in:** any AI tool that can edit files and run commands in your project, such as
Claude Code, Cursor (agent mode), OpenAI Codex or ChatGPT's agent mode. A plain chat window
can answer the interview, but it can't test its own work, so it will still stop and ask you.

**How to use it:**
1. Open your project in the tool.
2. Paste everything between the two lines below, and add your task on the last line.
3. Answer the 5 questions. Most of the time you just type `yes` to accept the agent's suggestions.
4. Walk away. Read `PROGRESS.md` when you come back.

---

You are going to work on this project for a long stretch without me. Before you touch any
file, we set up a brief together. Follow these steps in order.

**Step 1: Interview me first (2 minutes).**
Scan the project. Then ask me these 5 questions in plain English, all in one message. Under
each one, write your recommended answer based on what you found, so I can reply `yes`.
1. **Finish line:** What does "finished" look like? List every piece of the end result, not
   just the first step.
2. **Self-test:** How will you check each change yourself, without asking me? Name the exact
   test, build or check command, or the page you will load and what must be true on it.
3. **Gold standard:** Which existing file, page or example should your work match in
   quality and style?
4. **Off-limits:** What must you never touch or do? Include anything that sends email,
   charges money, deletes data, publishes, or deploys to production.
5. **Run length:** How long should you work, and what is the maximum number of passes?
   (Default: stop after 30 passes.)

Wait for my answers. Then write them to a file called `BRIEF.md` and show it to me. Start
work only after I reply `yes`.

**Step 2: Work from a task list.**
Break the finish line into small tasks and write them to `TASKS.md`, one per line, in order.
Work on one task at a time. When a task passes its self-test, mark it done and start the next
one yourself. Do not stop to ask whether to continue.

**Step 3: Test after every change.**
Run the self-test from `BRIEF.md` after every change. If it fails, read the error, fix it and
run it again. Compare your work against the gold standard before you mark a task done.

**Step 4: Keep notes and re-read the brief.**
After each task, add 2-3 lines to `PROGRESS.md`: what you did, how you tested it, and anything
you are unsure about. Every 5 passes, re-read `BRIEF.md` so you never drift from the goal or
the off-limits list.

**Safety rails (never break these):**
- Never delete, skip or weaken a test to make it pass. If a test seems wrong, write it down in
  `PROGRESS.md` and move to the next task.
- Stop after the maximum number of passes, even if tasks remain.
- Never do anything on the off-limits list. Stop and wait for me before you send a message,
  charge money, delete data, publish anything or deploy to production.
- If you are blocked, write down why in `PROGRESS.md` and move to the next task instead of
  waiting for me.

**When you finish or hit the pass limit:** write a short summary at the top of `PROGRESS.md`
with tasks done, tasks left, every test result, and anything that needs my decision.

My task: [describe what you want done]

---
