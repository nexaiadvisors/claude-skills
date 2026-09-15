# agent-guardrails

One file: a `CLAUDE.md` that holds a coding agent to three safety rules when it can run
commands, edit files, and call tools for you.

The rules, in one line each:

1. **Never take an irreversible action without a human yes** - reversible by default; deletes,
   sends, deploys, spends and access changes pause for approval, per action.
2. **Leave a trail I can read afterward** - every consequential action leaves a record you can
   find without the chat, and logs are never deleted on failure.
3. **Never accept a goal without a boundary on how you may reach it** - the goal is scoped to a
   lane; routing around a blocker, weakening a check, or widening its own access to succeed is a
   failure, not a shortcut.

Each rule carries a one-line test you can apply to any action.

## Use it

```sh
# per project
cp CLAUDE.md /path/to/your/repo/CLAUDE.md

# or globally, for every project on your machine
cat CLAUDE.md >> ~/.claude/CLAUDE.md
```

Then delete any rule that does not fit your setup. A rule earns its place only if the agent
would do the wrong thing without it.

## Why it is short

A `CLAUDE.md` competes for the model's attention line by line, so three enforced rules beat
thirty ignored ones. These three are the ones that turn a mistake into an incident. Everything
else is coding style, which belongs somewhere else.

MIT. Written by David He, NexAI Advisors.
