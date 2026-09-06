# Why Do AI Agents Break Rules? How Framing, Context, and Social Signals Shape Compliance

Interactive results site for our AIES 2026 paper on what makes AI agents follow the
rules. Twelve instruction-tuned LLMs act as an enterprise procurement assistant under one
legal rule, and the site lets you filter every result by model, rule framing, enforcement
level, pressure tactic, and social signal, and read the raw agent transcripts behind the
numbers. Given the same rule, compliance ranges from 43.5% to 89.5% on the choice of model
alone, a stated fine can lower compliance because it reads as a price, and a deadline gets
past a built-in follow-the-law instruction for eleven of the twelve models.

- **Paper:** https://arxiv.org/abs/2608.12323 (AAAI/ACM Conference on AI, Ethics, and Society 2026; also at the COLM 2026 Workshop on Agent Behavior)
- **Live site:** https://trace-ai-labs.github.io/ai-incentives/
- **Code and data:** https://github.com/trace-ai-labs/llm-compliance
- **Follow-up benchmark:** [PACT](https://trace-ai-labs.github.io/pact/)

`paper.pdf` is the arXiv build of the AIES camera-ready; copy it from `paper/main_arxiv.pdf`
in the experiment repo whenever the paper changes. The site is a single dependency-free
static page.

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
