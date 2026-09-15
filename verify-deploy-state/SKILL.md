---
name: verify-deploy-state
description: "Checks what is actually running in production against what you think you shipped - by reading the running artifact, the cloud resource, the git history and every deploy path, never a pipeline status. Use for 'is X deployed?', 'did my change take effect?', 'what is running right now?', after any deploy script, or when a fix is live in main and still not showing up. Read-only."
argument-hint: "[service or resource names to check, e.g. 'api gateway' or 'the frontend']"
compatibility: "POSIX shell, git; optional: a cloud CLI (az, aws, gcloud, kubectl), curl, jq, psql, a forge CLI such as gh"
---

# Verify Deploy State

## What this does, and what it never does

It answers one question with evidence: **is the code you think you shipped the code that is
serving traffic right now?** It reads the running artifact's own identity, the cloud
resource's image and config, the git history behind that image, and every path that can
deploy the surface. Then it names the drift, if any, and the exact next action.

It is **read-only**. It runs no deploy, writes no env var, changes no resource. Its only
network calls go through CLIs you already authenticated (`az`, `aws`, `gcloud`, `kubectl`,
`curl` to your own hosts, `gh`). It never handles a credential. If a check needs a tool you
do not have, that check is reported as COULD NOT CHECK, never guessed.

## Why it exists

Staleness has no error state. A build failure is loud; a deploy that never fired is silent,
because the previous version keeps serving traffic and every health check stays green.
Three failure shapes this catches, each seen in production:

1. **Silent partial deploys.** An operator runs a script named like a full deploy; it
   rebuilds one of three services. Bug reports arrive for the service that never moved.
2. **Stale-image regressions.** A deploy script reads its image tag from a feature branch.
   Production runs a build older than `main`, and the next deploy from `main` "regresses".
3. **Wasted fixes.** "I'll push another commit." The deploy path in use never pulls it.

## Prerequisites

Run this preflight before Step 1. Every row names what happens when the tool is missing.

| Needs | Why | Check | If missing |
|---|---|---|---|
| POSIX shell + `git` | history and tag mapping | `command -v git` | Stop. |
| The repo checked out | maps image tags to commits | `git rev-parse --is-inside-work-tree` | Stop; run from the repo. |
| `curl` | reads the running service's identity | `command -v curl` | Step 3a becomes COULD NOT CHECK. |
| One cloud CLI, authenticated | reads image, env, last-modified | `az account show` / `aws sts get-caller-identity` / `gcloud auth list` / `kubectl config current-context` | Step 2 becomes COULD NOT CHECK; say which cloud you could not read. |
| `psql` or equivalent (optional) | Step 3b, only when the service owns a database | `command -v psql` | Step 3b becomes COULD NOT CHECK. |
| Forge CLI such as `gh` (optional) | run conclusions, webhook list | `gh auth status` | CI facts come from the CI web UI, by hand. |

**Before you read anything, print which account each CLI is pointed at** (`az account show`,
`aws sts get-caller-identity`, `gcloud config get-value account`, the kube context). A
"not found" from the wrong account is indistinguishable from a deleted resource.

## Configuration

Everything is supplied at invocation or discovered. No secret goes in any of these.

| Value | How it is supplied | Default |
|---|---|---|
| Resources in scope | argument, or asked for in Step 1 | none - the skill asks |
| `HEALTH_URL` | the service's health or version endpoint | discovered from the repo (`grep -rn "gitSha\|GIT_SHA\|BUILD_ID" src`), else asked |
| `DB_URL` | only for Step 3b | unset - Step 3b skipped with a note |
| Deploy scripts | discovered: `ls scripts/*deploy* .github/workflows/*` plus `netlify.toml`, `vercel.json` | - |

---

## Workflow

### Step 1: Name the resources, then the operator's belief

"Is the app deployed?" is not a checkable question. Expand the name into concrete resources
(gateway container, worker job, edge function, static frontend, database). Different deploy
paths often touch different subsets, and the gap between subsets is where the bug lives.

For each resource, write down what the operator believes is running and why. The belief is
the hypothesis this skill tests.

### Step 2: Read the cloud resource

Ask the live control plane, never a deploy log, for image, env, and last-modified:

```bash
# Azure Container Apps
az containerapp show -n <NAME> -g <RG> \
  --query "{image:properties.template.containers[0].image, lastModified:systemData.lastModifiedAt}" -o json
# AWS ECS
aws ecs describe-services --cluster <CLUSTER> --services <SVC> \
  --query 'services[0].{taskDef:taskDefinition, lastDeploy:deployments[0].createdAt}'
# Kubernetes
kubectl get deploy <NAME> -n <NS> -o jsonpath='{.spec.template.spec.containers[0].image}'
# Cloud Run
gcloud run services describe <SVC> --region <REGION> --format='value(status.latestReadyRevisionName)'
```

Adapt to your cloud; the pattern is constant. Record `lastModified` separately from the
image tag: a `lastModified` that advanced today with an unchanged tag is a config-only
update, not a new build.

### Step 3a: Ask the running service which revision it is

This is the only surface that cannot lie about which code is serving traffic. Delivery has
three independent facts: (1) the artifact was built and published, (2) a process pulled it
and IS it, (3) it behaves. A green pipeline establishes only (1).

```bash
curl -sf "$HEALTH_URL" | jq -r '.gitSha // .version // .build'   # what is serving
git rev-parse --short HEAD                                         # what you shipped
git merge-base --is-ancestor <served-sha> origin/main && echo "served sha is on main"
```

If the service has no such endpoint, go to Step 3c. Do not substitute a healthcheck: a
healthcheck says a process is up, not which one.

Three status surfaces that have lied, and what to read instead:

- **A run list.** `gh run list` has reported a failed run as `completed/success` and shown
  `in_progress` for a finished run. Use the list only to find run ids; take the verdict
  from `gh run view <id> --json status,conclusion`.
- **A deploy that "finished" having changed nothing.** Triggered while the image was still
  pushing, it pulled the previous `:latest`, started a fresh container, and passed its
  healthcheck. Tell: `0 layers pulled` in the deploy log. A real image change pulls layers.
- **A trigger step at the end of a job.** Everything before it publishes; only delivery is
  missing. Keep `curl -f` on any deploy-trigger call; without `-f`, curl exits 0 on a 404
  or 405 and the pipeline stays green while delivery stops for good.

Also confirm a git push deploys this resource at all. An image-pull resource (a
`dockerimage` app in Coolify, an ECS service pinned to a tag) has no git integration; a
push builds an image that nothing pulls until a trigger fires.

**Validation:** *did I read the RUNNING revision, or a status that claims it deployed?*

### Step 3b: If the service owns a database, verify schema by objects, never by the ledger

A migrations table records intent, not effect. `prisma migrate resolve --applied` and its
equivalents write a completed row without executing SQL; that is their purpose. Any
environment whose history includes `db push` or `resolve` can carry a ledger that is a
perfect fiction, and every ledger-based audit keeps confirming it.

```bash
# schema models vs actual tables - the diff must be EMPTY
grep -E "^model " prisma/schema.prisma | awk '{print $2}' | sort > /tmp/models.txt
psql "$DB_URL" -tA -c "SELECT table_name FROM information_schema.tables WHERE table_schema='public';" | sort > /tmp/tables.txt
comm -23 /tmp/models.txt /tmp/tables.txt
# probe everything one suspect migration creates (to_regclass returns NULL, never raises)
grep -E '^CREATE TABLE' migration.sql | sed -E 's/CREATE TABLE "([^"]+)".*/\1/' |
while read T; do echo "$T: $(psql "$DB_URL" -tA -c "SELECT to_regclass('public.\"$T\"') IS NOT NULL;")"; done
```

Repair, when it is yours to do, with idempotent additive DDL in a transaction
(`CREATE TABLE IF NOT EXISTS`, `ADD COLUMN IF NOT EXISTS`); apply the additive half first
and defer any `DROP`. Then re-run the diff and record the counts.

Seen in production: a migration sat in the ledger with `finished_at` set and had never run.
Production was missing three tables, a column and three indexes for five weeks while a
documented audit that read the ledger certified the schema current.

**Validation:** *did I verify the OBJECTS, or did I read the ledger?*

### Step 3c: When the artifact cannot self-identify, the substitute probe must match what the diff EMITS

Fires for a statically built, CDN-served frontend with no version endpoint (Netlify, Vercel,
S3 plus CloudFront, GitHub Pages). Derive the probe from the diff, never from habit:

```bash
git diff --name-only <deployed-sha>..<expected-sha>          # what OUTPUT kind does this emit?
curl -s "$HOST/<route>" | grep -oE '/_next/static/css/[^"]+\.css' | sort -u   # then fetch THAT kind
```

CSS sources emit `/_next/static/css/*.css` and never appear in JS chunks; media emits
`/_next/static/media/`; a server-only change emits no client asset at all. Re-extract asset
URLs from freshly fetched HTML on every check: hashed filenames rotate on ship, so a URL
captured earlier probes a stale file that can never change.

Power-validate the signature before reporting drift: absent at the old tip, present at the
new tip, and the OLD signature still present in the live artifact right now. When every
signal reads zero, including "the old shape is still there", the probe has lost power. That
is not evidence of "never deployed" and must not appear in the drift table.

**Validation:** *could this probe have returned non-zero against what is live right now?*

### Step 4: Map the deployed image to a source commit

Image tags usually encode date plus branch context.

```bash
git log --all --oneline | grep -iE "<tag-fragment>" | head -5
git log <branch> --pretty='%h %ai %an :: %s' -- <Dockerfile-path> | head -10
git log origin/main..<inferred-branch> --oneline | head      # how far off main is it?
```

For each resource: which commit and branch the image was built from, how far behind or
ahead of `main`, and whether that source is merged at all.

### Step 5: Enumerate every path that can deploy this surface

Most repos have more than one, and the second is usually a platform-side git integration no
CI log mentions:

```bash
grep -n "^\s*command" netlify.toml vercel.json 2>/dev/null       # platform builds on push
gh api repos/<owner>/<repo>/hooks --jq '.[].config.url' 2>/dev/null
grep -rn "netlify deploy\|vercel deploy\|aws s3 sync\|az containerapp\|kubectl apply" .github/workflows/ scripts/
```

Build the script-versus-resource matrix and surface every ambiguity. A script named
`deploy-everything.sh` that deploys one service is exactly the footgun this step exists for:

|                       | gateway | worker | edge-fn |
|---|---|---|---|
| `redeploy-gateway.sh` | yes | no | no |
| `deploy-core.sh`      | yes | yes | no |
| platform git integration | no | no | yes |

Both directions of the error are real. CI green with nothing deployed (Step 3a). And a CI
deploy job SKIPPED while the platform integration shipped every commit anyway: seen once as
"the frontend has not deployed in 19 hours" reported from a skipped job, while the served
page's fingerprint had moved and the repo was in fact building every merge twice.

A monorepo has one path PER SURFACE. A health endpoint's sha answers for the service that
serves it and nothing else.

**Validation:** *how many things can deploy this surface, and did I read the ARTIFACT or
only the pipeline?*

### Step 6: Compare, categorise, diagnose

| Resource | Deployed image | Source commit | `main` HEAD for source | Drift |
|---|---|---|---|---|

Drift categories: **stale image** (built well behind `main`), **branch divergence** (built
from a feature branch; `main` moved), **env drift** (resource env differs from what the
scripts would set), **script gap** (the operator ran S; the change lives in a resource S
never touches), **unmerged source** (the next deploy from `main` will regress it).

The diagnosis names the deploy path the operator most likely used and the resource it did
not reach. That is usually the whole root cause.

---

## Output

```markdown
# Deploy state - <scope>, read <timestamp>

## Accounts read as: <cloud account / kube context / forge login>
## Per-resource state
| Resource | Image or version | Last modified | Source commit | Drift |
## Deploy paths
| Path | Resources touched |
## Diagnosis
<which path was run, what it touched, where the gap is>
## Next action
<run X | fix Y | file Z - one concrete step>
## Could not check
<every check that lacked a tool or an account, by name>
```

Compact. If everything matches `main`, say so in one line and stop.

## Footguns to flag whenever seen

- A script whose name implies broader scope than it has.
- An image built from a feature branch and deployed before the branch merged.
- An env-vars-only update with the image left frozen (`lastModified` moved, tag did not).
- **An env var set in the control plane and reported as "live".** The value reaches the
  process only at container start. The only direct evidence is reading it inside the
  running container: `printenv KEY` via `kubectl exec` or the platform's terminal. Use
  `printenv KEY`, never a bare `env`; a full dump puts every secret on a screen that ends
  up in a transcript.
- **An env write applied without a redeploy.** Worse than doing neither: it sits armed and
  activates on whatever the next deploy happens to be. Write and redeploy as one action, or
  roll the write back.
- **Coolify specifically:** `PATCH /api/v1/applications/{uuid}/envs` only updates an
  existing key. For a new key it returns `404 Environment variable not found`, which reads
  like a missing application. Use `POST` with `{key, value, is_preview}`; a second POST
  returns `409`; `PATCH` is then the rollback path. `write` and `deploy` are separate token
  scopes, so a token can redeploy but not edit env (`403 Missing required permissions`).

## Quality checklist

- [ ] Every CLI's account or context printed before any read was believed
- [ ] Running revision read from the live service and compared to the shipped sha, not inferred from deploy status, CI, or a healthcheck
- [ ] CI verdicts from `gh run view <id>`, never from a run list
- [ ] Deploy log checked for layers pulled (zero means nothing new was delivered)
- [ ] Static frontend: probe kind derived from `git diff --name-only`, URL re-extracted this check, signature power-validated
- [ ] Every deploy path enumerated, including platform-side git integrations
- [ ] If the service owns a database: schema verified by object diff, not the migration ledger
- [ ] Every env var claimed live was read from inside the running container
- [ ] All in-scope resources listed; each with image, last-modified, source commit; drift category named
- [ ] Next action is one concrete step
- [ ] COULD NOT CHECK listed by name, never folded into "no drift found"
