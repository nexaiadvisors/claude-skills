# Evidence, 2026 - what the primary sources say

Verified 2026-09-15 by two Oracle research lanes (vendor docs + published studies; X/HN/YouTube/
GitHub for practitioner logs). Re-verify dates before quoting to a client; this field moves.

## Official positions

- Google, AI optimization guide (added May 2026): no new files, markup or Markdown needed for
  AI features; "ignore tactics like chunking content, creating unnecessary AI text files (like
  llms.txt), or pursuing inauthentic mentions"; prioritize SEO over "AEO/GEO hacks"; a site must be
  indexed and snippet-eligible. https://developers.google.com/search/docs/fundamentals/ai-optimization-guide
  and https://developers.google.com/search/docs/appearance/ai-features
- Google spam policies (2026-08-28): doorway abuse and scaled content abuse (incl. AI-generated
  pages "without adding value") apply to generative AI responses too.
  https://developers.google.com/search/docs/essentials/spam-policies
- Google vendor guidance (2026-06-05): be wary of unsolicited SEO email, guarantees, and any deal
  where you must link to or host with the vendor; asks whether "AEO/GEO" advice aligns with
  Google's guidance. https://developers.google.com/search/docs/fundamentals/do-i-need-seo
- OpenAI bots: OAI-SearchBot surfaces sites in ChatGPT search (not training); GPTBot may train;
  ChatGPT-User is user-initiated and may ignore robots.txt. ChatGPT search uses third-party
  search providers (reported: Bing). https://developers.openai.com/api/docs/bots ,
  https://help.openai.com/en/articles/9237897-searching-the-web-with-chatgpt . Referrals carry
  `utm_source=chatgpt.com` (Publishers FAQ 12627856).
- Anthropic: ClaudeBot (training), Claude-User (user fetch), Claude-SearchBot (search index).
  https://support.claude.com/en/articles/8896518
- Perplexity: PerplexityBot (search, respects robots), Perplexity-User (ignores robots).
  https://docs.perplexity.ai/guides/bots . Cloudflare documented undeclared Perplexity crawlers
  (2025-08-04).
- Bing: "AI Performance" report in Webmaster Tools (2026-02-10, citations across Copilot and Bing
  AI); guidance: IndexNow, clear headings/tables/FAQ sections, fresh accurate content, evidence.
  IndexNow participants: Bing, Yandex, Naver, Seznam, Yep, Amazon; not Google.
- Google Search Console generative-AI performance reports: all sites worldwide since 2026-08-31
  (impressions only). GA4 "AI Assistant" default channel since 2026-05-13.

## Measured effects

- llms.txt: Ahrefs (137K domains, June 2026): 28% publish one, 97% received zero requests; of the
  fetched 3%, 96% were bots and only 19.5% named AI tools. SE Ranking (300K domains): no
  correlation with citations. Practitioner logs on X/HN agree (2 vs 424 hits; 7 reads in 12
  weeks on 83 sites; Astro removed theirs). Mueller and Illyes: Google does not use it.
  https://ahrefs.com/blog/llmstxt-study , https://seranking.com/blog/llms-txt
- Structured data: Ahrefs difference-in-differences on 1,885 pages that added JSON-LD: AI
  Overviews -4.6%, AI Mode +2.4%, ChatGPT +2.2% (the last two indistinguishable from zero).
  FAQ rich results removed from Google (May 2026). SE Ranking: FAQ schema pages 3.6 vs 4.2
  citations. Live fetchers DO read JSON-LD (Williams-Cook hidden-address test), so entity
  hygiene still matters. https://ahrefs.com/blog/schema-ai-citations
- What gets cited: "best X" lists are 43.8% of ChatGPT-cited page types (Ahrefs); but
  self-promotional pages got cited yet skipped 43% of the time and faded (Ahrefs experiment);
  ~48% of citations are community/UGC and 85% of brand mentions originate off-site (AirOps 2026);
  LinkedIn is the #2 cited domain across ChatGPT/AI Mode/Perplexity (Semrush, 325K prompts);
  AI-cited URLs are 25.7% fresher (Ahrefs); 76% of ChatGPT's top-cited pages refreshed within 30
  days; brand mentions correlate with AI Overview visibility more than links (Ahrefs, 75K brands).
- Misinformation defense: in Ahrefs' planted-falsehood test ChatGPT cited the brand's official
  FAQ in 84% of answers; Gemini/Perplexity repeated the falsehood 37-39% of the time.
- Volatility: under 1-in-100 chance of the same brand list twice; top brands per category still
  appear in 55-77% of runs (SparkToro, Jan 2026). ChatGPT averages ~5 brands per answer,
  Perplexity ~8 (Conductor, July 2026).
- Traffic: AI referrals 0.1-0.25% of referral traffic (Ahrefs 2025), under 1% (6sense).

## The vendor-pitch stat table

| Claim in the pitch | What the source actually says |
|---|---|
| "Over half of buyers use AI before Googling" | G2 (Apr 2026, n=1,076 B2B SOFTWARE buyers): 51% start with a chatbot more often than Google. Semrush (2026, n=643 US B2B): 41%. TrustRadius (early 2025): 7% used LLMs in buying. Forrester/6sense: ~94% use AI somewhere in the journey. |
| "AI gives them 3-5 names" | ChatGPT ~5, Perplexity ~8, Claude ~8.5, Gemini ~9; the list changes almost every run. |
| "N pages, each targeting a query, fix this" | Google: ignore GEO hacks, spam policy covers scaled query pages; Ahrefs: self-pages skipped 43% even when cited; 85% of mentions are off-site. |
| "Zero cost" | Google's vendor guidance flags unsolicited email, guarantees and vendor-hosted assets; "captures RFQs" means the leads land on their forms. |

## Code patterns worth borrowing (inspected 2026-09-15)

- thedaviddias/llms-txt-hub `apps/web/components/json-ld.tsx`: escape `<` as `<` in JSON-LD.
- Auriti-Labs/geo-optimizer-skill `frontend/scripts/indexnow-submit.mjs`: sitemap-lastmod
  selection, dry-run default, status map, never in build.
- onvoyage-ai/gtm-engineer-skills `improve-aeo-geo/SKILL.md`: a checklist (bots allowed,
  canonical, sitemap lastmod); its llms.txt/FAQPage weights are contradicted by the logs above.
