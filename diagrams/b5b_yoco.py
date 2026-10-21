"""Diagram: YOCO prefill truncation (decoder SWA bounded replay) for a 1,000-token prompt.

Used by: src/concepts/yoco-swa-replay.html ("The picture")
Sources (commit 9bd9cf2):
  deepinfer/model_executor/models/v4_modules/yoco.py:14-21          consumer layers = [n_prefill_layer, N)
  deepinfer/model_executor/models/deepseek.py:190-207               boundary: get_consumer_view (compact) / get_mask_view (mask)
  deepinfer/model_executor/models/decoder_layer.py:134-142          compact rows; consumer_full_hidden from the full rows
  deepinfer/model_executor/models/v4_modules/attn.py:672-721        _store_yoco_full_kv: main + index KV for all positions
  csrc/engine/input_metadata/prepare_tensor_input_v4.cpp:225       clip_prefix = clamp(data_len - keep - q_start, 0, q_len - 1)
  csrc/engine/input_metadata/prepare_tensor_input_v4.cpp:155       visible lower bound = max(pos - W + 1, data_len - keep, valid_start)
  csrc/engine/input_metadata/prepare_tensor_input_v4.cpp:267-271   ring store only for kept rows among the last 134
  README.md:25                                                     compact + KEEP_TOKENS = 140
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, BORDER, GRAY_MID, INK, MUTE, PINK, TEAL, VIOLET, WHITE, Diagram  # noqa: E402

d = Diagram(width=1100)
d.header(
    "YOCO prefill truncation: a 1,000-token prompt with KEEP_TOKENS = 140",
    "DEEPINFER_YOCO_PREFILL_TRUNCATION_MODE=compact  ·  window 128 (docs value)  ·  one sequence, one prefill chunk",
    params="keep range = [1000 − 140, 1000) = [860, 1000)   ring = 134 slots   guard: 140 ≥ 128 + 6",
)

# ============================================================================
# Panel 1: rows per layer group
# ============================================================================
y0 = 112
P1_H = 300
d.panel(y0, P1_H, 1, "Which positions does each group of layers compute?",
        "Producer layers: all 1,000. Consumer layers: only 860..999. Consumer compressed KV still covers all 1,000.")

AX0, AX1 = 300, 1040


def px(p, n=1000):
    return AX0 + (AX1 - AX0) * p / n


ry = y0 + 78
RH = 30
# producer
d.text(46, ry + 20, "producer layers", 13, BLUE[0], "bold")
d.text(46, ry + 37, "[0, n_prefill_layer)", 12, MUTE, mono=True)
d.rect(px(0), ry, px(1000) - px(0), RH, fill=BLUE[1], stroke=BLUE, rx=3, sw=1.4)
d.text((px(0) + px(1000)) / 2, ry + 20, "all rows: Q, SWA KV, compressed KV, attention, MoE", 12.5, BLUE[0], "bold", "middle")

ry2 = ry + 66
d.text(46, ry2 + 20, "consumer layers", 13, TEAL[0], "bold")
d.text(46, ry2 + 37, "[n_prefill_layer, N)", 12, MUTE, mono=True)
d.rect(px(0), ry2, px(860) - px(0), RH, fill=BORDER, stroke=GRAY_MID, rx=3, sw=1.2, dash="4 3")
d.text((px(0) + px(860)) / 2, ry2 + 20, "rows 0..859 are not computed", 12.5, MUTE, "bold", "middle")
d.rect(px(860), ry2, px(1000) - px(860), RH, fill=TEAL[1], stroke=TEAL, rx=3, sw=1.6)
d.text((px(860) + px(1000)) / 2, ry2 + 20, "140 rows", 12.5, TEAL[0], "bold", "middle")

ry3 = ry2 + 58
d.text(46, ry3 + 20, "consumer compressed", 13, VIOLET[0], "bold")
d.text(46, ry3 + 37, "KV and index K", 13, VIOLET[0], "bold")
d.rect(px(0), ry3, px(1000) - px(0), RH, fill=VIOLET[1], stroke=VIOLET, rx=3, sw=1.4)
d.text((px(0) + px(1000)) / 2, ry3 + 20, "all 1,000 positions, from the full shared hidden state (_store_yoco_full_kv)", 12.5, VIOLET[0], "bold",
       "middle")
for p in (0, 860, 1000):
    d.line(px(p), ry3 + RH + 4, px(p), ry3 + RH + 10, MUTE, 1)
    d.text(px(p), ry3 + RH + 25, str(p), 12, MUTE, anchor="middle", mono=True)

# ============================================================================
# Panel 2: visible keys of kept queries
# ============================================================================
y1 = y0 + P1_H + 20
P2_H = 350
d.panel(y1, P2_H, 2, "Which SWA keys does a kept query see in a consumer layer?",
        "The window [pos − 127, pos], cut at 860. Queries from 987 on see a full window of 128 keys.")

B0, B1 = 840, 1006
BX0, BX1 = 340, 1040


def bx(p):
    return BX0 + (BX1 - BX0) * (p - B0) / (B1 - B0)


qy = y1 + 98
rows = [
    ("query 860", 860, 860, "1 key"),
    ("query 900", 860, 900, "41 keys"),
    ("query 987", 860, 987, "128 keys (full)"),
    ("query 999", 872, 999, "128 keys (full)"),
]
d.line(bx(860), qy - 8, bx(860), qy + 4 * 34 + 4, AMBER[0], 1.4, dash="5 4")
d.text(bx(860), qy - 14, "860 = data_len − KEEP_TOKENS", 12, AMBER[0], "bold", "middle", mono=True)
for i, (lab, lo, hi, note) in enumerate(rows):
    yy = qy + 6 + i * 34
    d.text(46, yy + 16, lab, 12.5, TEAL[0], "bold", mono=True)
    d.rect(bx(B0), yy, bx(B1) - bx(B0), 22, fill=WHITE, stroke=BORDER, rx=2, sw=0.8)
    d.rect(bx(lo), yy, max(bx(hi + 1) - bx(lo), 3), 22, fill=TEAL[1], stroke=TEAL, rx=2, sw=1.3)
    d.text(196, yy + 16, note, 12, INK, mono=True)

wy = qy + 6 + 4 * 34 + 8
d.text(46, wy + 16, "ring writes", 12.5, PINK[0], "bold", mono=True)
d.rect(bx(B0), wy, bx(B1) - bx(B0), 22, fill=WHITE, stroke=BORDER, rx=2, sw=0.8)
d.rect(bx(866), wy, bx(1000) - bx(866), 22, fill=PINK[1], stroke=PINK, rx=2, sw=1.3)
d.text(196, wy + 16, "866..999", 12, INK, mono=True)
for p in (840, 860, 900, 987, 1000):
    d.text(bx(p), wy + 42, str(p), 12, MUTE, anchor="middle", mono=True)
d.text(46, wy + 66, "The ring keeps the last 134 positions (866..999). The first decode query (1000) reads 873..1000: all are in the ring.", 12.5,
       INK)

# ============================================================================
# Panel 3: mask vs compact
# ============================================================================
y2 = y1 + P2_H + 20
P3_H = 186
d.panel(y2, P3_H, 3, "Two modes, the same kept rows",
        "mask computes every row but narrows the window. compact removes the rows. The kept rows get the same numbers.")
bw, bh, bg = 316, 90, 33
bxs = [46, 46 + bw + bg, 46 + 2 * (bw + bg)]
by = y2 + 70
d.box(bxs[0], by, bw, bh, "off (default)", ["consumer layers: 1,000 rows", "full window for every row", "exact SWA KV"],
      col=(MUTE, BORDER, None), align="start", mono_size=12)
d.box(bxs[1], by, bw, bh, "mask", ["consumer layers: 1,000 rows", "window cut at 860", "rows < 860 see no SWA key"],
      col=AMBER, align="start", mono_size=12)
d.box(bxs[2], by, bw, bh, "compact (README setting)", ["consumer layers: 140 rows", "window cut at 860", "least work"],
      col=TEAL, align="start", mono_size=12)

y = y2 + P3_H + 22
d.legend(30, y, [(BLUE, "producer rows"), (TEAL, "consumer rows / visible keys"), (VIOLET, "full compressed KV"),
                 (PINK, "ring writes"), (AMBER, "keep boundary")])
y += 34
y = d.footnotes(30, y, [
    "Simplified: no chunking, no context parallelism, no prefix-cache hit. Deduction (the code does not say it): from the second consumer layer",
    "  on, the SWA KV of the kept rows is approximate. The deployment notes agree; they say the result is \"used for decode only and never",
    "  enters the prefix cache\" (doc/inference_deployment_qa.md:187).",
])
d.save(height=y + 10)
