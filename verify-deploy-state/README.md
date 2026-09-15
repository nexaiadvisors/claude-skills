# verify-deploy-state

An agent skill that answers "is my change actually live?" with evidence instead of a green
pipeline. It reads the running service's own revision, the cloud resource's image and config,
the git history behind that image, and every path that can deploy the surface, then names the
drift and the one next action.

For anyone who has pushed a fix, watched CI go green, and still had the bug reported an hour
later.

## What it does

- **Reads the running artifact first.** A health or version endpoint that returns the git sha is
  the only surface that cannot lie about which code is serving traffic. A healthcheck says a
  process is up; it does not say which one.
- **Verifies a database by its objects.** A migrations ledger records intent, not effect. The
  skill diffs schema models against real tables and probes each object a suspect migration
  should have created.
- **Picks the probe from the diff.** For a CDN-served frontend with no version endpoint, it reads
  `git diff --name-only` first and probes the asset kind that change emits, then checks the probe
  has power before trusting a zero.
- **Enumerates every deploy path**, including the platform-side git integration that no CI log
  mentions, and builds a script-versus-resource matrix.
- **Keeps "checked, found nothing" separate from "could not check."**

What it deliberately does **not** do:

- It changes nothing. No deploys, no env writes, no restarts. Every step is a read.
- It does not trust a status. Pipeline results, deploy logs that say "finished", and control-plane
  env listings are all inputs to be cross-checked, never conclusions.
- It does not guess. A check whose tool or account is missing is reported by name.

## Prerequisites

The table in `SKILL.md` is the source of truth; the skill runs it as a preflight.

| Needs | Why | If missing |
|---|---|---|
| POSIX shell, `git`, the repo checked out | history, tag-to-commit mapping | stop |
| `curl` (+ `jq` for JSON) | read the running service's identity | that check becomes COULD NOT CHECK |
| One authenticated cloud CLI: `az`, `aws`, `gcloud`, or `kubectl` | image, env, last-modified | resource reads become COULD NOT CHECK, named per cloud |
| `psql` (optional) | schema-by-objects, only when the service owns a database | that step is skipped with a note |
| A forge CLI such as `gh` (optional) | run verdicts, webhook list | CI facts come from the web UI by hand |

The skill assumes no specific cloud. The commands shown are examples for Azure Container Apps,
ECS, Kubernetes, Cloud Run, Netlify and Vercel; the pattern (ask the live control plane, then the
live process) is the same everywhere.

## Install

```sh
# user scope - available in every project
git clone <repo-url> /tmp/claude-skills && cp -R /tmp/claude-skills/verify-deploy-state ~/.claude/skills/

# project scope - checked in, shared with a team
cp -R /tmp/claude-skills/verify-deploy-state .claude/skills/
```

Replace `~/.claude/skills` with your agent's own skills directory if it differs. Three files
ship: `SKILL.md` (the only file the agent loads), this README, and `LICENSE`.

Invoke with `/verify-deploy-state <what to check>`, for example
`/verify-deploy-state api gateway and worker`.

## Configuration

| Value | How supplied | Default |
|---|---|---|
| Resources in scope | argument, or the skill asks | none |
| `HEALTH_URL` | the service's health or version endpoint | discovered from the repo, else asked |
| `DB_URL` | only for the schema-by-objects step | unset - step skipped with a note |
| Deploy scripts | discovered from `scripts/`, `.github/workflows/`, `netlify.toml`, `vercel.json` | - |

No secret belongs in any of these. Cloud access goes through CLIs you already authenticated.

## Worked example

```
> /verify-deploy-state api and frontend

Accounts read as: aws 123456789012 (prod), gh user: alice
Per-resource state
| Resource | Image or version | Last modified | Source commit | Drift |
| api      | api:20260817-1432 | 2026-08-17 14:35Z | 3f21a90 (feature/cookies) | branch divergence: main is 4 ahead |
| frontend | css chunk a81f...  | -                 | 9c0d2e1 (main)             | none: probe derived from diff (CSS), old signature gone, new present |

Deploy paths
| Path | Resources touched |
| .github/workflows/deploy.yml | api only |
| netlify.toml [build]         | frontend, on every push |

Diagnosis
The api image was built from feature/cookies before it merged; main has moved four commits.
The next deploy from main will regress the cookie change unless the branch merges first.

Next action
Merge feature/cookies, then redeploy api from main. Nothing is wrong with the frontend.

Could not check
- api database schema: DB_URL not set.
```

## Limitations and blast radius

- **Writes:** nothing. Not even a temp file outside `/tmp`.
- **Reads:** your cloud control plane, your running service's health endpoint, your git history,
  and, if you supply `DB_URL`, your database catalog (table and index names only).
- **Network:** through CLIs you already authenticated and `curl` to hosts you name. It never
  authenticates and never stores a credential.
- **Cost:** none beyond API reads.
- **Accuracy ceiling:** it can only read the accounts your CLIs are pointed at. That is why the
  first thing it prints is which account each CLI answered as. A "not found" from the wrong account
  looks exactly like a deleted resource.
- **Tested scope:** the shell blocks in `SKILL.md` were run on macOS under `/bin/bash` 3.2 against
  Azure Container Apps, Kubernetes, Netlify and a Postgres database reached through `psql`. The
  ECS and Cloud Run commands are taken from the vendors' documented CLI surface and were not run
  by the authors. Treat those as unverified.

## License

MIT - see [`LICENSE`](LICENSE).
