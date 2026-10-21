"""Diagram: how hugging_face/ maps checkpoint names, loads the three channels, and checks them.

Used by: src/code/hf-weights.html
Sources (commit 9bd9cf2):
  deepinfer/hugging_face/names.py:1-16, 36-71, 147-179    module numbers, suffix map, hf_to_model
  deepinfer/hugging_face/weights.py:74-110                 _is_expert, _is_engram_table, build_coverage
  deepinfer/hugging_face/weights.py:389-436                load_covered_params (ordinary channel, then experts, then Engram)
  deepinfer/hugging_face/weights.py:275-328                _load_expert_params
  deepinfer/hugging_face/weights.py:331-386                _load_engram_tables
  deepinfer/hugging_face/loading.py:28-66, 86-121          prepare_hf_coverage, validate_hf_shapes
  deepinfer/model_executor/model_loader.py:145-153         one-way missing check
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, PINK, VIOLET, WHITE, Diagram  # noqa: E402

d = Diagram(width=1100)
d.header(
    "HF weights: names, three load channels, and the checks",
    "deepinfer/hugging_face/ (names.py, weights.py, loading.py)  ·  commit 9bd9cf2",
    params="example names; L = checkpoint layer, n_layer = num_hidden_layers from config.json",
)

# ---------------------------------------------------------------------------
# Panel 1: name map
# ---------------------------------------------------------------------------
y0 = 112
rows = [
    ("embed.weight", "module.module.0.emb.tok_emb.weight", "ordinary", BLUE),
    ("layers.3.attn.wq_a.weight  (+ .scale)", "module.module.4.self_attn.Wq.A.weight", "ordinary, FP8", BLUE),
    ("layers.3.ffn.shared_experts.w1 / w3", "module.module.4.experts.shared_experts.0.linear1.weight", "ordinary, cat 2", BLUE),
    ("layers.3.ffn.experts.{e}.w1 / w3", "module.module.4.experts.linear1.weight", "routed experts", EMERALD),
    ("layers.L.engram.embed.weight", "module.module.{L+1}.engram_embedding.embedding.embedding", "Engram table", PINK),
    ("mtp.0.embed.weight", "None: tied to module 0 (alias)", "not loaded", AMBER),
]
ROW_H = 24
P1_H = 72 + 26 + len(rows) * ROW_H + 22
d.panel(y0, P1_H, 1, "How does a checkpoint name find its parameter?",
        "hf_to_model gives the parameter path. build_coverage puts the name into one of three channels.")
tx = [62, 372, 892]
hy = y0 + 72
d.rect(46, hy - 4, 1008, 26 + len(rows) * ROW_H + 8, fill=WHITE, stroke="#d1d5db", sw=1.2)
for x, h in zip(tx, ["checkpoint name", "model parameter (model_name)", "channel"]):
    d.text(x, hy + 14, h, 12.5, MUTE, "bold")
d.line(54, hy + 22, 1046, hy + 22)
for i, (hf, cm, ch, col) in enumerate(rows):
    ry = hy + 26 + i * ROW_H + 16
    d.text(tx[0], ry, hf, 11.5, INK, mono=True)
    d.text(tx[1], ry, cm, 11.5, INK, mono=True)
    d.text(tx[2], ry, ch, 12, col[0], "bold")

# ---------------------------------------------------------------------------
# Panel 2: three channels
# ---------------------------------------------------------------------------
y1 = y0 + P1_H + 20
BW, BH, GAP = 316, 176, 30
P2_H = 72 + BH + 24
d.panel(y1, P2_H, 2, "What does each channel do with the bytes and the scales?",
        "load_covered_params runs the three channels in this order. Each channel reads only the names in its own map.")
by = y1 + 72
boxes = [
    ("1. ordinary  (tensors)", BLUE, [
        "1 or 2 names -> read_concat",
        "  (2 = cat along dim 0)",
        "copy_ into param.data",
        "1-byte dtype (FP8):",
        "  .scale E8M0 -> fp32 sf",
        "  then set_ue8m0_sf",
        "weights.py:403-427",
    ]),
    ("2. routed experts", EMERALD, [
        "only this EP rank's ids",
        "slot = cat([w1; w3]) | w2",
        "scale bytes .view(int32",
        "  | int16), not decoded",
        "copy_ into sf[local]",
        "param.mxfp4 = True",
        "weights.py:275-328",
    ]),
    ("3. Engram tables", PINK, [
        "rows row_start ..",
        "  row_start + num_per_part",
        "chunks of 2**28 bytes",
        "E8M0 -> fp32 sf on device",
        "rows past the table:",
        "  weight 0, sf 1",
        "weights.py:331-386",
    ]),
]
for i, (title, col, lines) in enumerate(boxes):
    bx = 46 + i * (BW + GAP)
    d.rect(bx, by, BW, BH, fill=col[1], stroke=col, sw=1.5)
    d.text(bx + 14, by + 24, title, 14, col[0], "bold")
    for j, s in enumerate(lines):
        last = j == len(lines) - 1
        d.text(bx + 14, by + 48 + j * 17, s, 11.5 if last else 12, MUTE if last else INK, mono=True)
    if i < 2:
        ax = bx + BW
        d.arrow(ax, by + BH / 2, ax + GAP - 2, by + BH / 2, INK)

# ---------------------------------------------------------------------------
# Panel 3: checks
# ---------------------------------------------------------------------------
y2 = y1 + P2_H + 20
steps = [
    ("prepare_hf_coverage: index, shards, names", "missing shard -> FileNotFoundError; bad shard or name -> ValueError", "loading.py:28-66", VIOLET),
    ("missing check: model params - coverage", "a param with no source -> RuntimeError; an unused tensor -> nothing", "model_loader.py:147-149", AMBER),
    ("validate_hf_shapes: headers only", "ordinary params: shape, dtype, FP32 HC/sink; tied aliases -> ValueError", "loading.py:86-121", VIOLET),
    ("load_covered_params: read and copy", "byte range, short read; FP8 weight with no .scale -> KeyError; expert asserts", "weights.py:389-436", EMERALD),
]
CARD_H, CARD_GAP = 50, 12
P3_H = 72 + len(steps) * (CARD_H + CARD_GAP) - CARD_GAP + 22
d.panel(y2, P3_H, 3, "What is checked, and when?",
        "Steps 1-3 read no weight bytes. The check in step 2 looks in one direction only.")
cy = y2 + 72
for i, (title, row, cite, col) in enumerate(steps):
    d.rect(46, cy, 1008, CARD_H, fill=col[1], stroke=col, sw=1.4)
    d.rect(46, cy, 6, CARD_H, fill=col[0], stroke=None, rx=3)
    d.badge(70, cy + 17, i + 1, col, r=10, size=11)
    d.text(88, cy + 22, title, 13.5, INK, "bold")
    d.text(88, cy + 40, row, 12, INK, mono=True)
    pw = len(cite) * 11 * 0.602 + 20
    d.pill(1054 - 10 - pw, cy + 8, pw, cite, col[0])
    if i < len(steps) - 1:
        d.arrow(70, cy + CARD_H, 70, cy + CARD_H + CARD_GAP - 2, col)
    cy += CARD_H + CARD_GAP

y = y2 + P3_H + 22
d.legend(30, y, [(BLUE, "ordinary channel"), (EMERALD, "routed experts"), (PINK, "Engram tables"),
                 (VIOLET, "checks"), (AMBER, "one-way gap / not loaded")])
y += 38
y = d.footnotes(30, y, [
    "Names are examples. Scale tensors (X.scale) are never mapped as parameters (weights.py:95).",
    "Not shown: vision names (vision_pipeline.aligner.*), the model. prefix rule, and the expert count check per layer.",
])
d.save(height=y + 10)
