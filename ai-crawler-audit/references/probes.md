# Probes - exact commands

All read-only against the live origin. Set `B=https://<host>`. Capture exit codes on their own
line when a result becomes a finding.

## 1. Crawler access matrix (status per user agent per URL)

```bash
B=https://wholesale.example.com
for u in /en /en/products /en/products/<slug> /en/wholesale-program /en/contact; do
  echo "== $u"
  for ua in \
    "GPTBot/1.2 (+https://openai.com/gptbot)" \
    "OAI-SearchBot/1.0; +https://openai.com/searchbot" \
    "ChatGPT-User/1.0; +https://openai.com/bot" \
    "ClaudeBot/1.0; +claudebot@anthropic.com" \
    "Claude-User/1.0" "Claude-SearchBot/1.0" \
    "PerplexityBot/1.0; +https://perplexity.ai/perplexitybot" \
    "Perplexity-User/1.0; +https://perplexity.ai/perplexity-user" \
    "Google-Extended" \
    "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)" \
    "Applebot/0.1; +http://www.apple.com/go/applebot" \
    "Amazonbot/0.1; +https://developer.amazon.com/support/amazonbot" \
    "Bytespider" \
    "meta-externalagent/1.1 (+https://developers.facebook.com/docs/sharing/webmasters/crawler)"; do
    printf "%-4s %s\n" "$(curl -sS --max-time 20 -o /dev/null -w '%{http_code}' -A "$ua" "$B$u")" "$ua"
  done
done
curl -sS "$B/robots.txt"    # read the groups; search/fetch bots vs training bots
```

Classes: search/fetch = OAI-SearchBot, ChatGPT-User, Claude-SearchBot, Claude-User,
PerplexityBot, Perplexity-User, bingbot, Applebot. Training controls = GPTBot, ClaudeBot,
anthropic-ai, Google-Extended, CCBot, Bytespider, meta-externalagent. Google-Extended never
affects Search inclusion. ChatGPT-User and Perplexity-User ignore robots.txt (user-initiated).

## 2. JS-free content probe per template (words, links, JSON-LD, canonical)

```bash
for p in /en /en/collections /en/products /en/wholesale-program /en/contact; do
  curl -sS --max-time 25 -A "OAI-SearchBot/1.0; +https://openai.com/searchbot" "$B$p" -o /tmp/p.html
  python3 - "$p" <<'PY'
import re,html,sys
s=open('/tmp/p.html',encoding='utf-8',errors='replace').read()
blocks=re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>',s,re.S)
types=[t for b in blocks for t in re.findall(r'"@type":"([A-Za-z]+)"',b)[:1]]
body=re.sub(r'<script.*?</script>|<style.*?</style>','',s,flags=re.S)
words=len(html.unescape(re.sub(r'<[^>]+>',' ',body)).split())
links=len(set(re.findall(r'href="(/[^"#?]+)"',s)))
canon=re.search(r'<link rel="canonical" href="([^"]+)"',s)
print(f"{sys.argv[1]:24s} words={words:5d} links={links:4d} ld={types} canonical={canon.group(1) if canon else None}")
PY
done
```

Flags: words < 150 on a content page; links < 5 on a listing page; canonical != the page's own
URL; `ld=['Organization']` only on a product page; a FAQ page whose answers you cannot grep out of
the HTML (`grep -c "<distinctive answer phrase>"` = 0).

## 3. Sitemap vs discoverable links

```bash
curl -sS "$B/sitemap.xml" | grep -o '<loc>[^<]*</loc>' | sed 's#</\?loc>##g' > /tmp/sitemap.txt
wc -l /tmp/sitemap.txt
# every sitemap URL must be robots-allowed and self-canonical; every hub page's links should be in the sitemap
grep -c '/collections/' /tmp/sitemap.txt; grep -c '/products/' /tmp/sitemap.txt
```

## 4. Index presence

- DuckDuckGo HTML endpoint (Bing index): `https://duckduckgo.com/html/?q=site%3A<host>`
- Bing: `https://www.bing.com/search?q=%22<host>%22+<brand>` (a bare `site:` on an unknown host
  gets rewritten into unrelated results with "Do you mean ...")
- Google: `site:<host>` in the user's connected Chrome (the built-in browser hits a CAPTCHA; never
  bypass it). Search Console > Pages, and > Performance > "AI Overviews / AI Mode" (since 2026-08-31).

## 5. Answer-engine baseline mechanics

- ChatGPT logged out, search on: navigate the built-in browser to
  `https://chatgpt.com/?q=<url-encoded prompt>`, wait ~10 s, press Escape to close the login
  modal, take screenshots and scroll (`zoom` may return the full frame). `get_page_text` and the
  DOM selectors return the settings dialog or empty strings on this layout; do not trust them.
- Perplexity: `mcp__perplexity-deep__perplexity_search_web` with `recency: year`; citations come
  back as a numbered list - open the cited competitor pages and list what they state.
- Record per run: names, cited domains, brand named y/n. Three runs minimum per prompt.

## 6. Entity and facts sweep

```bash
# Organization node from the home page
curl -sS -A "GPTBot/1.2" "$B/en" | grep -o '<script type="application/ld+json">[^<]*' | head -3
# the same legal name / email / address on four surfaces
for p in /en /en/contact /llms.txt; do curl -sS "$B$p" | grep -oiE "Monli (LLC|Pets, Inc\.?)|[a-z]+@[a-z.]+" | sort | uniq -c; done
# never-claim sweep (phrases from the brand's own list)
for p in /en /en/our-story /en/sustainability /en/contact /en/wholesale-program /llms.txt; do
  printf "%-24s " "$p"; curl -sS "$B$p" | grep -oiE "organic|100% recycled|oeko-tex|plastic-free|natural dyes|compostable" | sort | uniq -c | paste -sd' ' -; echo
done
```

Open every `sameAs` URL in the browser before it goes in the JSON-LD; a dead or wrong profile is
worse than none.

## 7. llms.txt

```bash
curl -sS -o /tmp/llms.txt -w 'HTTP %{http_code} %{content_type}\n' "$B/llms.txt"; head -20 /tmp/llms.txt
# every linked URL must be 200
grep -oE 'https?://[^ )]+' /tmp/llms.txt | sort -u | while read u; do printf "%s %s\n" "$(curl -sS -o /dev/null -w '%{http_code}' "$u")" "$u"; done
```

## 8. IndexNow (freshness)

Key file `public/<32hex>.txt` containing the key; submit script runs AFTER deploy (verifies
`https://<host>/<key>.txt` == key first), reads the live sitemap, submits URLs without `lastmod`
plus those modified within N days, POSTs `{host,key,keyLocation,urlList}` to
`https://api.indexnow.org/indexnow` in batches of 10,000, dry-run by default. Status meanings:
200/202 ok, 403 key invalid, 422 URL not on host, 429 slow down. Keep the submit script in
something like `scripts/post-deploy/indexnow-submit.mjs`, with its own unit tests.

## 9. Post-deploy re-verification

Repeat probes 1, 2, 3, 6 and 7 against production after the deploy; compare word counts, link
counts, JSON-LD types and sitemap counts to the pre-fix numbers; check the IndexNow key file
returns 200 text/plain. Read the deployed revision (a health `gitSha` or a build id), not the
pipeline's colour.
