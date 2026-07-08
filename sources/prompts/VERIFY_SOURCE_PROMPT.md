You are classifying whether the provided text is an actual information source or noise.

The text may be a legitimate article, report, post, or document. It may also be:

- A verification/CAPTCHA window ("I'm not a robot", "verify you're human")
- An advertisement or promotional landing page
- A paywall or subscription prompt
- A login/registration page
- A robots.txt or sitemap
- An error page (404, 503, rate-limit, etc.)
- A terms of service or privacy policy page
- Bot-scraping detection or challenge page

## Classification

Determine whether the text represents a genuine information source worth ingesting into a knowledge graph, or whether it should be rejected as noise.

Consider:
- **Content substance** — Does it contain factual claims, analysis, or narrative content?
- **Structure** — Does it read like an article, report, or post with coherent structure?
- **Intent** — Is the primary purpose to inform, or to gate/advertise/verify?

## Rules

- Return ONLY one of these labels: `SOURCE` or `NOISE`
- If the text contains both real content and noise (e.g., ads alongside an article), return `SOURCE`.
- If the text is primarily noise with no substantive content, return `NOISE`.
- No explanation, no extra text.

The source text follows:
