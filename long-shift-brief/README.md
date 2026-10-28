# long-shift-brief

Gets an AI coding agent to work for hours instead of stopping every 90 seconds to ask
"should I continue?".

Two ways to use it:

- **No setup:** open [`PROMPT.md`](PROMPT.md), copy the prompt, paste it into Claude Code,
  Cursor (agent mode), OpenAI Codex or ChatGPT's agent mode, and add your task on the last line.
- **As a skill:** copy this folder to `~/.claude/skills/` and run `/long-shift-brief <your task>`.

Both do the same thing. The agent first asks you 5 questions with its own suggested answers
(finish line, self-test, gold standard, off-limits, run length), writes them to `BRIEF.md`, and
starts only after you say `yes`. Then it works through `TASKS.md`, tests every change, keeps
notes in `PROGRESS.md`, re-reads the brief every 5 passes, and follows three safety rails: never
weaken a test, stop at the pass limit, and never send, charge, delete, publish or deploy without you.

From the video "How I keep AI agents busy for 12 hours" on the NexAI Advisors YouTube channel.
