#!/usr/bin/env python3
"""Aggregate the raw experiment JSONL into a compact data.json for the website.

Reads from the cloned trace-ai-labs/llm-compliance repo's per-experiment results and
emits:
  - aggregated compliance cells per experiment (model x condition axes)
  - a curated sample of agent transcripts for the response explorer

Run:  python3 build_data.py /path/to/llm-compliance  ./data/data.json
"""
import json, glob, os, sys, collections, random

SRC = sys.argv[1] if len(sys.argv) > 1 else "/tmp/llm-compliance"
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(__file__), "data", "data.js")
COMBINED = os.path.join(SRC, "results", "data")

# ---- model registry: openrouter id -> (display, short, developer) ----
# No training-orientation group column: the paper tested whether a two-way
# split by developer-stated training philosophy predicts compliance, found
# that it does not, and reports models individually instead.
MODELS = {
    "openai/gpt-oss-120b":              ("GPT-OSS-120B",   "gpt-oss",   "OpenAI"),
    "qwen/qwen3.5-flash-02-23":         ("Qwen 3.5 Flash", "qwen",      "Alibaba"),
    "meta-llama/llama-4-maverick":      ("Llama 4 Maverick","llama",    "Meta"),
    "moonshotai/kimi-k2.5":             ("Kimi K2.5",      "kimi",      "Moonshot"),
    "nvidia/nemotron-3-super-120b-a12b":("Nemotron 3 Super","nemotron", "NVIDIA"),
    "minimax/minimax-m2.7":             ("MiniMax M2.7",   "minimax",   "MiniMax"),
    "mistralai/mistral-small-2603":     ("Mistral Small",  "mistral",   "Mistral AI"),
    "deepseek/deepseek-v3.2":           ("DeepSeek V3.2",  "deepseek",  "DeepSeek"),
    "x-ai/grok-4.1-fast":               ("Grok 4.1 Fast",  "grok",      "xAI"),
    "google/gemini-3-flash-preview":    ("Gemini 3 Flash", "gemini",    "Google"),
    "google/gemma-4-31b-it":            ("Gemma 4 31B",    "gemma",     "Google"),
    "z-ai/glm-4.7-flash":               ("GLM 4.7 Flash",  "glm",       "Z.ai"),
}
MODEL_ORDER = ["gpt-oss","qwen","llama","kimi","nemotron","minimax","mistral",
               "deepseek","grok","gemini","gemma","glm"]

def short(model_id):
    return MODELS.get(model_id, (None, None, None))[1]

def load(name):
    path = os.path.join(COMBINED, name)
    rows = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return rows

def agg(rows, keyfn, compfn=lambda r: r.get("compliant"), validfn=lambda r: r.get("parseable", True)):
    """Group rows by keyfn -> {n, comp}. Skips rows with unknown model or unparseable."""
    out = collections.defaultdict(lambda: {"n": 0, "comp": 0})
    for r in rows:
        m = short(r.get("model"))
        if m is None:
            continue
        if not validfn(r):
            continue
        c = compfn(r)
        if c is None:
            continue
        k = keyfn(r, m)
        if k is None:
            continue
        out[k]["n"] += 1
        if c:
            out[k]["comp"] += 1
    return out

def cells(rows, dims, compfn=lambda r: r.get("compliant")):
    """dims: list of (name, extractor). Returns list of dicts {dim..., m, n, comp}."""
    def keyfn(r, m):
        vals = []
        for _, ext in dims:
            v = ext(r)
            if v is None:
                return None
            vals.append(v)
        return (m, *vals)
    a = agg(rows, keyfn, compfn)
    res = []
    for k, v in a.items():
        d = {"m": k[0], "n": v["n"], "comp": v["comp"]}
        for i, (name, _) in enumerate(dims):
            d[name] = k[i + 1]
        res.append(d)
    return res

md = lambda key: (lambda r: r.get("metadata", {}).get(key))

def axis_or_control(key):
    """Control rows carry condition=='control' with the axis field left null
    (only one legacy model fills it). Treat those as the 'none' control cell."""
    def f(r):
        m = r.get("metadata", {})
        v = m.get(key)
        if v is None and m.get("condition") == "control":
            return "none"
        return v
    return f

def mandate_norm(r):
    return r.get("metadata", {}).get("mandate") or "none"

data = {}

# ---- Foundational controls: framing x fin ----
controls = load("controls.jsonl")
data["controls"] = cells(controls, [("framing", md("framing")), ("fin", md("fin_level"))])

# ---- Wording ablation: obligation verb variant x framing x fin ----
wording = load("wording.jsonl")
# The obligation verb itself is the framing manipulation here (framing field is null),
# so we key on the verb variant x fine level.
data["wording"] = cells([r for r in wording if r.get("metadata", {}).get("variant")],
                        [("variant", md("variant")), ("fin", md("fin_level"))])

# ---- Institutional authority: authority x fin ----
exp3 = load("authority.jsonl")
data["authority"] = cells(exp3, [("authority", axis_or_control("authority")), ("fin", md("fin_level"))])

# ---- Social signals: peer signal x fin ----
exp4 = load("peer_signals.jsonl")
data["social"] = cells(exp4, [("social", axis_or_control("social")), ("fin", md("fin_level"))])

# ---- Normative pressure: norm x fin (informational framing) ----
exp6 = load("norms.jsonl")
data["norm"] = cells([r for r in exp6 if r.get("metadata", {}).get("framing") == "informational"],
                     [("norm", axis_or_control("norm")), ("fin", md("fin_level"))])

# ---- Employee pressure x mandate x fin ----
exp8 = load("pressure.jsonl")
data["pressure"] = cells(exp8, [("pressure", axis_or_control("pressure")),
                                ("mandate", mandate_norm),
                                ("fin", md("fin_level"))])

# ---- Stakes (item criticality) ----
stakes = load("stakes.jsonl")
data["stakes"] = cells(stakes, [("stakes", md("stakes")),
                                ("framing", md("framing")),
                                ("fin", md("fin_level"))])

# ---- Multi-turn dynamics (framing varied, no mandate) ----
def mt_cells(rows, extra_dims):
    """end-state compliance + switch rate per cell."""
    out = collections.defaultdict(lambda: {"n": 0, "t2comp": 0, "switched": 0})
    for r in rows:
        m = short(r.get("model"))
        if m is None or not r.get("t2_parseable", True):
            continue
        t2 = r.get("t2_compliant")
        if t2 is None:
            continue
        key = [m, r.get("direction"), r.get("tactic")]
        for _, ext in extra_dims:
            key.append(ext(r))
        key = tuple(key)
        o = out[key]
        o["n"] += 1
        if t2:
            o["t2comp"] += 1
        if r.get("switched"):
            o["switched"] += 1
    res = []
    for k, v in out.items():
        d = {"m": k[0], "direction": k[1], "tactic": k[2],
             "n": v["n"], "t2comp": v["t2comp"], "switched": v["switched"]}
        for i, (name, _) in enumerate(extra_dims):
            d[name] = k[3 + i]
        res.append(d)
    return res

exp9 = load("multiturn.jsonl")
data["multiturn"] = mt_cells(exp9, [("framing", md("framing")), ("fin", md("fin_level"))])

# ---- Reasoning transparency (from the paper's table; authoritative) ----
# Taken verbatim from paper/generated/table_violation_reasoning.tex, i.e. the
# camera-ready two-stage re-judge, NOT the earlier single-pass labels. Three
# regimes: foundational baselines, pressures with no mandate, and pressures
# under the anti-adversarial mandate. `None` means that regime had no
# violations to classify (Qwen never violates under the mandate).
data["reasoning"] = [
    # short, base H/A/S, press H/A/S, mand H/A/S/MandateCite
    {"m": "gpt-oss", "base": [46, 46, 7], "press": [90, 10, 0], "mand": [89, 11, 0, 0]},
    {"m": "qwen", "base": [62, 11, 27], "press": [95, 5, 0], "mand": None},
    {"m": "llama", "base": [75, 13, 12], "press": [89, 11, 0], "mand": [94, 5, 0, 1]},
    {"m": "kimi", "base": [69, 21, 10], "press": [85, 15, 0], "mand": [79, 13, 0, 9]},
    {"m": "nemotron", "base": [60, 32, 8], "press": [88, 11, 1], "mand": [75, 21, 1, 3]},
    {"m": "minimax", "base": [68, 20, 12], "press": [89, 11, 0], "mand": [86, 10, 1, 3]},
    {"m": "mistral", "base": [53, 26, 21], "press": [78, 17, 5], "mand": [60, 31, 8, 1]},
    {"m": "deepseek", "base": [67, 25, 7], "press": [85, 14, 1], "mand": [88, 8, 0, 5]},
    {"m": "grok", "base": [73, 14, 13], "press": [95, 5, 0], "mand": [96, 4, 0, 0]},
    {"m": "gemini", "base": [86, 4, 10], "press": [90, 10, 0], "mand": [98, 2, 0, 0]},
    {"m": "gemma", "base": [80, 8, 12], "press": [80, 15, 5], "mand": [90, 7, 0, 3]},
    {"m": "glm", "base": [70, 17, 13], "press": [78, 19, 3], "mand": [63, 30, 3, 5]},
]

# ---- Response explorer: curated transcript samples ----
def clip(t, n=1600):
    t = (t or "").strip()
    return t if len(t) <= n else t[:n].rstrip() + "…"

def sample_responses(rows, axis_keys, label, per_cell=2, max_total=200):
    """collect a few transcripts per (model, axis-cell, compliant) bucket."""
    buckets = collections.defaultdict(list)
    rnd = random.Random(7)
    rows = rows[:]
    rnd.shuffle(rows)
    for r in rows:
        m = short(r.get("model"))
        if m is None or not r.get("parseable", True):
            continue
        resp = r.get("raw_response")
        if not resp or len(resp) < 40:
            continue
        ax = tuple(r.get("metadata", {}).get(k) for k in axis_keys)
        key = (m, ax, bool(r.get("compliant")))
        if len(buckets[key]) >= per_cell:
            continue
        buckets[key].append({
            "exp": label, "m": m,
            "axis": {k: r.get("metadata", {}).get(k) for k in axis_keys},
            "compliant": bool(r.get("compliant")),
            "vendor": r.get("vendor_chosen"),
            "text": clip(resp),
        })
    flat = [x for v in buckets.values() for x in v]
    rnd.shuffle(flat)
    return flat[:max_total]

def sample_multiturn(rows, label, per_cell=2, max_total=120):
    """Two-turn transcripts: T1 response + employee follow-up + T2 response."""
    buckets = collections.defaultdict(list)
    rnd = random.Random(11); rows = rows[:]; rnd.shuffle(rows)
    for r in rows:
        m = short(r.get("model"))
        if m is None or not r.get("t2_parseable", True):
            continue
        t1, t2 = r.get("t1_response"), r.get("t2_response")
        if not t1 or not t2:
            continue
        mm = r.get("metadata", {})
        key = (m, r.get("direction"), r.get("tactic"), bool(r.get("t2_compliant")))
        if len(buckets[key]) >= per_cell:
            continue
        buckets[key].append({
            "exp": label, "m": m,
            "axis": {"direction": r.get("direction"), "tactic": r.get("tactic"),
                     "framing": mm.get("framing"), "fin_level": mm.get("fin_level")},
            "compliant": bool(r.get("t2_compliant")),
            "vendor": r.get("t2_vendor"),
            "turns": [clip(t1, 1100), clip(t2, 1100)],
            "switched": bool(r.get("switched")),
        })
    flat = [x for v in buckets.values() for x in v]
    rnd.shuffle(flat)
    return flat[:max_total]

responses = []
responses += sample_responses(controls, ["framing", "fin_level"], "Foundational", max_total=150)
responses += sample_responses(exp8, ["pressure", "mandate", "fin_level"], "Employee pressure", max_total=180)
responses += sample_responses(exp4, ["social", "fin_level"], "Social signals", max_total=120)
responses += sample_responses(exp3, ["authority", "fin_level"], "Authority", max_total=110)
responses += sample_responses(exp6, ["norm", "framing", "fin_level"], "Normative", max_total=120)
responses += sample_responses(wording, ["variant", "fin_level"], "Rule wording", max_total=120)
responses += sample_responses(stakes, ["stakes", "stakes_item", "framing", "fin_level"], "Item stakes", max_total=90)
responses += sample_multiturn(exp9, "Multi-turn", max_total=120)
data["responses"] = responses

# ---- meta ----
SINGLE = ["controls.jsonl", "wording.jsonl", "authority.jsonl",
          "peer_signals.jsonl", "norms.jsonl", "pressure.jsonl",
          "stakes.jsonl", "urgency.jsonl"]
MULTI = ["multiturn.jsonl", "multiturn_pressure.jsonl"]
single_rows = sum(len(load(f)) for f in SINGLE)
multi_rows = sum(len(load(f)) for f in MULTI)
total_trials = single_rows + multi_rows               # distinct scenario runs
total_responses = single_rows + 2 * multi_rows         # each multi-turn run = 2 agent responses
# generalizable enforcement-paradox stat: compliance drop when a small fine is
# added to an informational rule, across Group II (task-optimized) models.
def ctrl_rate(m, framing, fin):
    for c in data["controls"]:
        if c["m"] == m and c["framing"] == framing and c["fin"] == fin and c["n"]:
            return 100 * c["comp"] / c["n"]
    return None
g2 = [MODELS[k][1] for k in MODELS if MODELS[k][2] == "II"]
drops = []
for m in g2:
    a, b = ctrl_rate(m, "informational", "none"), ctrl_rate(m, "informational", "low")
    if a is not None and b is not None:
        drops.append(a - b)
drops.sort()
import statistics as _st
paradox_drops = [round(d) for d in drops]

data["meta"] = {
    "models": [{"short": MODELS[k][1], "name": MODELS[k][0],
                "dev": MODELS[k][2]} for k in MODELS],
    "model_order": MODEL_ORDER,
    "total_trials": total_trials,
    "total_responses": total_responses,
    "n_models": len(MODELS),
    "n_responses": len(responses),
    "paradox_median_drop": round(_st.median(drops)) if drops else None,
    "paradox_max_drop": round(max(drops)) if drops else None,
}
print("  paradox drops (Group II, info none->low):", paradox_drops,
      "median", data["meta"]["paradox_median_drop"])

os.makedirs(os.path.dirname(OUT), exist_ok=True)
payload = json.dumps(data, separators=(",", ":"))
with open(OUT, "w") as fh:
    if OUT.endswith(".js"):
        fh.write("window.SITE_DATA=" + payload + ";\n")
    else:
        fh.write(payload)

sz = os.path.getsize(OUT)
print(f"Wrote {OUT}  ({sz/1024:.0f} KB)")
for k, v in data.items():
    if isinstance(v, list):
        print(f"  {k}: {len(v)} cells")
print(f"  total trials counted: {total_trials}")
