---
name: expression-bank
description: >-
  Builds a vetted bank of portrait photos of the user making different expressions and poses
  (skeptical, surprised, worried, excited, pointing, holding a phone...) from a few good photos of
  them, for thumbnails, flyers, ads and video covers. Generates with GPT Image and/or Gemini, checks
  every face against the user's own photos with a free local face match, and hands back a labelled
  bank sheet of only the images that still look like them. Use for "make photos of me looking
  surprised", "expression bank", "I need pictures of me for a flyer/thumbnail", "my AI photos don't
  look like me".
license: MIT
compatibility: Python 3.9+ with opencv-python and numpy; macOS, Linux or Windows. Needs an OpenAI or Gemini API key.
metadata:
  version: 1.0.0
  author: David He (NexAI Advisors)
---

# Expression Bank

Turn 3-12 good photos of one person into a set of expression portraits that still look like them.
Every image is scored against their own photos; a face that drifted into a stranger never reaches
the sheet as a keeper. All logic is in `scripts/expression_bank.py` (run it with `python3 -I`).

**Rules that do not bend:**
- **Only the user's own face**, or a person who agreed to it. Never build a bank of a celebrity, a
  client who did not agree, a child, or anyone from a scraped photo. `run` refuses without `--consent`;
  ask the user, do not add the flag for them.
- **No key, no run.** The script refuses when no API key is set. Never ask the user to paste a key
  into chat, and never print, log or commit one.
- **Spend is capped.** Default cap \$3 per run. A run never spends past it: retries stop at the cap. When the first pass alone is over it, show the estimate and get the user's yes
  before adding `--yes`.

## Steps

### 1. Setup
```bash
python3 -I scripts/expression_bank.py setup
```
If it says a key or package is missing, walk the user through [setup](references/setup.md) and stop
until they have done it. They put the key in the file themselves.
Accept when: it prints `SETUP OK`.

### 2. Check the reference photos
Ask for a folder of 3-12 photos of the person (real photos or AI headshots), then:
```bash
python3 -I scripts/expression_bank.py check-refs --refs <folder>
```
It flags every weak photo right away: too small (face under 200 px), blurry, dark or turned away,
more than one main face, or a face that does not match the others (a different person). Tell the user
which photos were flagged and why, in plain words, and what makes a good one (see
[setup](references/setup.md#good-reference-photos)).
Accept when: it prints `REFS OK`. On `STOP`, nothing runs until the user swaps in better photos.

### 3. Pick the shots and show the cost
The default set is 8 shots: skeptical, surprised, worried, frustrated, exhausted, excited (pointing),
curious (palms up) and confident (holding a phone). For other needs, write a shots file
(see [shots](references/shots.md)) and pass `--shots <file>`.
```bash
python3 -I scripts/expression_bank.py plan --refs <folder> --out <out-folder> [--engines gpt,gemini] [--shots <file>]
```
Show the user the plan line: shots, engines, estimated cost and worst case with retries.
Accept when: the user agreed to the shots and the cost. At or under the cap, their go-ahead to run is enough.

### 4. Confirm consent, then run
Ask: "Are these photos of you, or of someone who agreed to this?" Only on yes:
```bash
python3 -I scripts/expression_bank.py run --refs <folder> --out <out-folder> --consent [--engines ...] [--shots <file>] [--retries 1]
```
Each shot is generated on every chosen engine; a shot that misses KEEP is retried up to `--retries`
times. Each image is scored locally against the user's photos:

| Verdict | Score | Meaning |
|---|---|---|
| KEEP | 0.72+ | looks like them |
| REVIEW | 0.55-0.72 | check by eye before using |
| REJECT | under 0.55 | a different-looking person; do not use |

Accept when: it prints `SHEET <path>` and `scores.json` exists in the out folder.

### 5. Hand over the bank
Open `bank-sheet.jpg` yourself first and look at every face: the score cannot see a sixth finger or
a warped hand. Then send the sheet to the user with one line per shot (verdict, score). The best
image per shot is in `<out-folder>/bank/<shot>.png`. Say plainly which shots are KEEP, which need
their eye (REVIEW), and offer to re-roll REJECT or REVIEW shots (a new spend, same cap).
Accept when: the user has the sheet and the bank folder path.

## Notes
- GPT Image usually holds identity better than Gemini (2026-11 run: GPT 6 of 8 KEEP, Gemini 3 of 8).
  If the user has only one key, run that engine alone with `--engines gpt` or `--engines gemini`.
- The face models (OpenCV YuNet and SFace, about 40 MB) download once to `~/.config/expression-bank/models`
  and are checked against pinned SHA-256 hashes. Faces never leave the computer for scoring; they do
  go to OpenAI or Google for generation, under the user's own account.
- Generated photos are AI images. If the user publishes them where rules apply (YouTube altered
  content, ad platforms), remind them to label them as AI-generated.
