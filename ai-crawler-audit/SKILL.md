---
name: ai-crawler-audit
description: "Audits AI visibility and buyer decision gaps. Use for GEO/AEO, crawler access, llms.txt, AI recommendations, or offer evaluation."
argument-hint: "[live URL] [repo path] [prompts: 'best X for Y', ...] [quick|deep|fix|buyer-check]"
metadata: {author: "David He, NexAI Advisors", version: "1.0.0", license: "MIT"}
---

# AI Crawler Audit

## Overview

Answer engines do not rank pages, they cite sources. A site is cited when (1) the engine's
retrieval can reach it (index + crawler access + server-rendered text), (2) one page states the
facts a buyer's question needs, plainly and consistently, and (3) other sites mention the brand.
This skill measures all three on the LIVE site with reproducible probes, ranks findings by the
2026 evidence (not by vendor folklore), and in fix mode applies only the changes that evidence
supports, then re-verifies on the deployed host.

Every finding cites a command and its output, a URL, or a `file:line`. Every claim about "what
works" carries a source in [references/evidence-2026.md](references/evidence-2026.md). The exact
commands live in [references/probes.md](references/probes.md).

**Expectation-setting is part of the audit.** AI referrals are 0.1-1% of traffic in every
published dataset; brand recommendations change on nearly every run; the biggest lever
(third-party mentions) is off-site. Say so in the report so nobody buys "4-5 pages that get you
into ChatGPT".

## When to Use This Skill

- "Are we showing up in ChatGPT / Perplexity / AI Overviews?", "why doesn't ChatGPT recommend us?"
- "AI crawler audit", "GEO audit", "AEO audit", "AI visibility", "is our site readable by AI?"
- "Should we add llms.txt / FAQ schema / an AI page?", "someone emailed us about AI optimization"
- After launching or migrating a site
- Fix mode ("audit and fix", "address what it finds") only on an explicit ask
- "Can a buyer or an AI assistant evaluate this offer?", "buyer decision check": use
  `buyer-check` below for information answerability without implying a visibility audit.

**Not for:** setting up Search Console, Bing Webmaster Tools or a business profile (do that by
hand or with a separate skill); classic technical SEO; page speed.

## Buyer-check mode

For a scoped offer review, follow [references/buyer-decision-check.md](references/buyer-decision-check.md)
and write its answer sheet. This mode opens only the declared offer/proof/terms sources;
it does not run a recommendation benchmark, crawl the site, transact, or change pages.
Label proposed facts and hypothetical buyer questions. The answer sheet diagnoses missing
or conflicting information; it never predicts a customer's choice or marks the offer approved.
The full audit below also includes this check after Phase 5. For `buyer-check` alone, the
full-audit phase checklist is not applicable; report those phases as not run.

## Inputs to establish first (Phase 0)

1. **Target**: the live origin (never guess a production URL) and, if available, the repo.
2. **Owner intent**: does the owner WANT AI crawlers? Blocking training bots (GPTBot, ClaudeBot,
   Google-Extended, CCBot, Bytespider) is a legitimate choice; blocking search/fetch bots
   (OAI-SearchBot, ChatGPT-User, Claude-SearchBot, Claude-User, PerplexityBot, Perplexity-User)
   removes the site from answers. Report each class separately.
3. **The buyer prompts**: 3-5 category questions a real buyer would ask ("best sustainable pet toy
   wholesale suppliers for independent boutiques, name 5") plus one brand-name prompt. Take them
   from the owner, sales calls or support tickets; do not invent the market's vocabulary.
4. **The brand's facts source**: a verified-claims list and a never-claim list if one exists (e.g.
   `social/config/<brand>-context.json`, a KB, a brand guide). Every fact the audit later asks to
   publish must trace to it. If none exists, note it as a finding: the site's claims have no
   owner.

## Workflow

### Phase 1 - Answer-engine baseline (the truth test, run BEFORE reading any code)

Ask each engine the buyer prompts and record, per prompt and engine: the names returned, the
cited URLs, and what those cited pages contain (this is the gap list). Repeat each prompt at
least 3 times; recommendations are non-deterministic (SparkToro 2026: under 1-in-100 chance of
the same brand list twice), so one run is an anecdote.

- **ChatGPT**: `https://chatgpt.com/?q=<url-encoded prompt>` works logged out with search on in
  the built-in browser. Read the answer from screenshots (scroll + zoom); the DOM selectors
  (`[data-message-author-role]`, `article`, `.markdown`) and `get_page_text` return the settings
  dialog or nothing on the logged-out layout. Dismiss the login modal with Escape or its X.
- **Perplexity**: the `perplexity_search_web` MCP tool, or the site. It returns citations.
- **Google AI Mode** (`udm=50`) / AI Overviews: the built-in browser hits a CAPTCHA; use the
  user's connected Chrome or say it was not measured. Never bypass the CAPTCHA.
- **Copilot / Claude / Gemini**: optional; each has its own top-cited-domain profile.

Output: a table `prompt | engine | run | names | cited domains | the brand named? (y/n)`, and one
line per cited competitor page: what it states that our page does not (MOQ, who they sell to,
where made, certifications, no-Amazon policy, marketplace listing). In one real audit, every
competitor ChatGPT cited was cited from ONE honest wholesale page of its own plus a
marketplace brand page.

### Phase 2 - Index presence (an unindexed page cannot be cited)

- Bing/DuckDuckGo `site:` (ChatGPT search draws on Bing): use DuckDuckGo's HTML endpoint or
  `bing.com/search?q="<host>"+<brand>`; Bing rewrites a bare `site:` query for an unknown host
  into unrelated results ("Do you mean ..."), so a brand term is required.
- Google `site:` via the user's Chrome; Search Console coverage and the gen-AI performance report
  (worldwide since 2026-08-31) if access exists.
- Report: how many URLs are indexed on each, and when the host was first crawled.

### Phase 3 - Crawler access matrix

For 5 key URLs (home, catalog/listing, one detail page, the conversion page, the facts/FAQ page)
fetch with each crawler user agent and record the HTTP status; parse robots.txt per group;
check the CDN/WAF for bot blockers (Cloudflare "block AI bots" is on by default for new zones;
Netlify has a User Agent Blocker extension). Commands: [references/probes.md](references/probes.md).
A search/fetch bot getting anything but 200 on a public page is High. A missing but
current token (Claude-User, Claude-SearchBot, OAI-SearchBot) in an explicit AI group is Low if the
`*` group allows it. Note that ChatGPT-User and Perplexity-User ignore robots.txt by design.

### Phase 4 - JS-free content per page template

AI fetchers do not execute JavaScript (OAI-SearchBot, ClaudeBot, PerplexityBot; Google's first
pass). For each key template, fetch with a bot UA and measure: visible words, count of internal
links, JSON-LD `@type`s, `<link rel=canonical>`, and whether the facts a buyer needs are in the
text. Thresholds that were real defects on 2026-09-15: a listing page with 0 category links and
~200 words (client-fetched grid); a FAQ page with 1 of 6 answers in the HTML (collapsed answers
unmounted); 13 pages canonicalising to the home page (inherited root canonical). Then diff the
sitemap against the links actually discoverable in HTML.

### Phase 5 - Entity and official facts

- Organization JSON-LD: `sameAs` lists every public profile (marketplaces, social, LinkedIn,
  the DTC store) and each URL was OPENED this session; `legalName`, founder, city-level address;
  a `WebSite` node linked by `@id`; `<` escaped in the serializer.
- One legal name, one email, one address everywhere: JSON-LD, footer, contact page, llms.txt,
  marketplace profiles. Assistants assemble the entity from exactly these.
- The official FAQ and terms (MOQ, shipping, lead time, who you sell to, where made,
  certifications) are in crawlable text on ONE complete page. ChatGPT cited the brand's own FAQ
  in 84% of answers in Ahrefs' planted-misinformation test.
- Never-claim sweep: grep every public page and llms.txt for the brand's forbidden phrases; an
  engine that quotes the page repeats them.
- Product structured data only from real fields: an empty `materials` array means no
  `material` property. Never invent an attribute to look complete.

### Phase 5A - Buyer decision information

Run [references/buyer-decision-check.md](references/buyer-decision-check.md) against the declared
offer and its proof/terms. Keep user fit, deployment risk and budget-owner questions separate.
Record answerability, source support and owner confirmation separately: a crawlable claim
can still be unsupported. Carry required unknowns into findings; don't invent a price or
quantified result to make a simulated buyer select the offer.

### Phase 6 - llms.txt

Present, `200 text/plain` (not the framework catch-all returning HTML), every linked URL 200,
every fact also on a public page, no never-claim phrases. Then state the expectation honestly:
no major answer engine is documented to read it (Ahrefs, 137K domains: 97% of llms.txt files got
zero requests; Google says it ignores it). Keep it because it is cheap; never sell it as a lever.

### Phase 7 - Freshness

Sitemap `lastmod` only where truthful; IndexNow key file at `/<key>.txt` plus a submit script that
runs AFTER deploy (never in the build) and submits no-lastmod pages plus recently modified URLs;
Bing Webmaster Tools sitemap; AI-cited pages skew 25.7% fresher than organic results.

### Phase 8 - Measurement

Search Console gen-AI report; Bing Webmaster Tools "AI Performance" (citations across Copilot and
Bing AI); referrer filters (`utm_source=chatgpt.com`, perplexity.ai, copilot.microsoft.com,
claude.ai, gemini.google.com) in PostHog/GA4 (GA4 has an "AI Assistant" channel since 2026-05).
Re-run the Phase 1 prompts monthly, 10+ times each.

## Findings table

| Check | Typical severity |
|---|---|
| Search/fetch AI bot blocked (robots, WAF, CDN) on public pages | High |
| Key template ships its list/facts only via client JS | High |
| Non-self canonical on citable pages | High |
| Not indexed on Bing/Google (no sitemap submitted, no inbound link) | High |
| Official FAQ/terms absent from HTML or contradicting other pages | High |
| Entity inconsistent (legal name, address, email) across surfaces | Medium |
| Organization `sameAs` empty / profiles not linked | Medium |
| Never-claim phrase on a public page or in llms.txt | Medium |
| llms.txt served as HTML by a catch-all | Medium |
| No IndexNow / no truthful lastmod | Low |
| No llms.txt | Low |
| Brand absent from category answers while all of the above pass | Off-site work, not a site defect |

## Fix mode (explicit ask only)

Ranked by evidence. Do the top rows before touching the bottom ones.

1. Index and canonical integrity: self-canonical every citable route, add missing routes to the
   sitemap, submit to Search Console and Bing.
2. Server-render what buyers and crawlers need: listing grids seeded from the server, FAQ answers
   in the DOM (hidden, not unmounted), facts in text.
3. Entity: `sameAs` from opened profiles, one legal name, WebSite node, escape `<`.
4. Freshness: IndexNow key + post-deploy submit; truthful lastmod.
5. llms.txt hygiene from the verified facts source, guarded by a test that forbids never-claim
   phrases.
6. Hand the off-site list to the owner: roundups the engines already cite (read them off the
   Phase 1 citations), marketplace reviews, LinkedIn company posts (the #2 cited domain for
   professional queries), community answers.

**Do not build**: FAQPage JSON-LD for citation lift (Google removed FAQ rich results May 2026; SE
Ranking and Ahrefs found no lift), `llms-full.txt`, query-targeted "best X" pages (Ahrefs: cited
pages still skipped 43% of the time, citations temporary; Google spam policy covers scaled query
pages), invented product attributes, or anything a vendor promises "at zero cost".

**Re-verify on the deployed host, per surface**: repeat Phases 3-6 against production after the
deploy lands (bot-UA word counts, JSON-LD types, sitemap counts, key file 200). A green build is
not a deploy; a merged branch is not a deploy. Guard each fix with a test that fails when the
defect returns (mutation-test it) - e.g. the FAQ test that unmounts an answer must go red.

## Vendor-pitch triage (the reason this audit is usually requested)

When an email says "buyers ask ChatGPT for best X, you are not appearing, we will build N pages":
run Phase 1 (the absence is usually TRUE), then check the stat (the 51% figure is G2's April 2026
survey of B2B SOFTWARE buyers; general B2B is ~41%, TrustRadius early 2025 found 7%), then apply
Google's vendor guidance: unsolicited email, guaranteed results, and leads landing on the vendor's
forms are each a flag. The remedy that works is the fix list above plus off-site mentions, not N
query pages.

## Report format

```
# AI crawler audit - <host> - <date>
## Baseline (Phase 1): <prompts x engines x runs>; brand named in N of M runs; cited competitors and what their pages state
## Index presence: Bing/DDG N URLs, Google N URLs, first crawl <date>
## Findings (P0 first): | # | Check | Severity | Confidence | Evidence (command/output/URL/file:line) | Fix |
## Expectation: AI referral share, volatility, what only the owner can do
## Fix log (fix mode): change -> guard test -> live re-verification result
## Sources: evidence-2026.md entries used
## Buyer decision information: answer sheet; required unknowns; claim confirmation; next internal action
```

## Quality Checklist

- [ ] Phase 1 ran BEFORE any code was read; each prompt run 3+ times; cited competitor pages opened and their stated facts listed
- [ ] Index presence measured on Bing/DDG AND Google (or "not measured" with the reason)
- [ ] Access matrix: every UA in probes.md on 5 key URLs; search/fetch vs training bots reported separately
- [ ] Per-template JS-free probe: words, internal links, JSON-LD types, canonical; sitemap diffed against discoverable links
- [ ] Every `sameAs` URL opened this session; legal name/email/address cross-checked on 4 surfaces
- [ ] Never-claim sweep run against every public page and llms.txt (or "no claims source exists" recorded as a finding)
- [ ] Buyer-check answer sheet cites declared sources; unknowns and approval status are separate from visibility or purchasing outcomes
- [ ] llms.txt reported with the honest expectation line
- [ ] No FAQPage-for-citations, llms-full.txt, or "best X" self-pages recommended
- [ ] Fix mode entered only on an explicit ask; every fix has a guard test that was mutation-tested
- [ ] Post-deploy re-verification done on the live host per surface, not from a build log
- [ ] Report states AI referral share and recommendation volatility so the owner's expectations are calibrated

## References

| File | Contents |
|---|---|
| [references/probes.md](references/probes.md) | Exact commands: UA matrix, JS-free word/link/JSON-LD probe, canonical and sitemap checks, ChatGPT/Perplexity baseline mechanics, IndexNow script shape, never-claim sweep |
| [references/evidence-2026.md](references/evidence-2026.md) | What the 2026 primary sources say works and does not, with URLs and dates; the vendor-pitch stat table |
| [references/buyer-decision-check.md](references/buyer-decision-check.md) | Scoped user-fit, implementation and budget-owner questions; answerability, evidence and confirmation checks |
