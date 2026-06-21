# The Compliance Architecture of AI Agents — project website

Interactive companion site for the paper *"What Makes AI Agents Follow the Rules?"*
A single-page, dependency-free static site that lets you filter the study's results by
model, rule framing, enforcement level, pressure tactic, and more — and read the raw
agent transcripts behind the numbers.

## Structure

```
index.html        # all page content + dashboard containers
css/styles.css    # blue / agentic-safety theme, hand-rolled
js/app.js         # all interactivity: heatmaps, SVG charts, response explorer
data/data.js      # precomputed aggregates + sampled transcripts (window.SITE_DATA)
build_data.py     # regenerates data/data.js from the raw experiment JSONL
```

No build step or framework. Fonts load from Google Fonts (graceful system fallback offline).

## Run locally

```bash
python3 -m http.server 8731
# open http://localhost:8731/
```

It also works opened directly as a `file://` — the data ships as `data/data.js`
(a `window.SITE_DATA = {...}` assignment), so there is no `fetch`/CORS dependency.

## Regenerate the data

Point `build_data.py` at a checkout of the experiment repo
([`mika-okamoto/ai-incentives`](https://github.com/mika-okamoto/ai-incentives)).
It reads the combined results in `results/paper_multimodel/_combined/*.jsonl`,
aggregates compliance rates per model × condition cell, samples transcripts for the
explorer, and writes `data/data.js`.

```bash
python3 build_data.py /path/to/ai-incentives ./data/data.js
```

The aggregated cell values were validated against the exact percentages quoted in the
paper (e.g. Gemini 100%→34% under imperative + small fine; Grok 8%→92% under peer-fined).

The reasoning-transparency numbers are taken directly from the paper's Table
(`source/results.tex`) rather than recomputed.

## Deploying

Any static host works. For GitHub Pages, drop these files at the repo root (or in
`/docs`) and enable Pages. The site is self-contained.
