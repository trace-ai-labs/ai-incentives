# The Compliance Architecture of AI Agents — project website

Interactive companion site for the paper *"Why Do AI Agents Break Rules? How Framing,
Context, and Social Signals Shape Compliance"* (AIES 2026; COLM 2026 Workshop on Agent
Behavior). `paper.pdf` is the arXiv build of the AIES camera-ready -- copy it from
`paper/main_arxiv.pdf` in the experiment repo whenever the paper changes.
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
([`trace-ai-labs/llm-compliance`](https://github.com/trace-ai-labs/llm-compliance)).
It reads the per-experiment results in `results/data/*.jsonl` (`controls.jsonl`,
`wording.jsonl`, `authority.jsonl`, `peer_signals.jsonl`, `norms.jsonl`,
`pressure.jsonl`, `stakes.jsonl`, `multiturn.jsonl`, …), aggregates compliance rates
per model × condition cell, samples transcripts for the explorer, and writes
`data/data.js`.

```bash
python3 build_data.py /path/to/llm-compliance ./data/data.js
```

The aggregated cell values were validated against the exact percentages quoted in the
paper (e.g. Gemini 100%→34% under imperative + small fine; Grok 8%→92% under peer-fined).

The reasoning-transparency numbers are taken directly from the paper's table
(`paper/generated/table_violation_reasoning.tex`) rather than recomputed, so they must be
re-copied into `build_data.py` whenever that table is regenerated. They are currently the
camera-ready two-stage re-judge labels, split across three regimes (foundational,
pressures with no mandate, pressures under the anti-adversarial mandate).

The site deliberately does **not** group models by training orientation. The paper tested
whether a two-way safety-tuned / task-optimized split predicts compliance and found that it
does not, so `meta.models` carries no `group` field and nothing in the UI asserts one.

## Deploying

Any static host works. For GitHub Pages, drop these files at the repo root (or in
`/docs`) and enable Pages. The site is self-contained.
