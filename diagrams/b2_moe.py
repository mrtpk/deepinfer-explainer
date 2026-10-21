"""Diagram: an MoE layer (router, top-k, shared expert), the cost per token, and load balance over EP ranks.

Used by: src/learn/moe.html
Toy numbers: 8 routed experts, top-2, 1 shared expert, 4 EP ranks. Illustrative, not the DeepInfer checkpoint.
Sources (commit 9bd9cf2):
  deepinfer/model_executor/models/v4_modules/moe.py:24-37     shared experts: one wide FFN
  deepinfer/model_executor/models/v4_modules/moe.py:40-67     TopKGate: sqrtsoftplus, noaux_tc, correction bias, BF16 Wgate
  deepinfer/model_executor/models/v4_modules/mlp.py:196-205   logical vs physical experts, split evenly over EP ranks
  csrc/engine/flops_estimator.hpp:82-99                       FLOPs per token: 3*h*m*(top_k + n_shared) + router h*n_routed
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, LINE, MUTE, NEUTRAL, PINK, TEAL, VIOLET, WHITE, Diagram  # noqa: E402

d = Diagram(width=1100)
W = d.W
d.header("Mixture of Experts: few experts per token, many experts in the model",
         "Toy layer: 8 routed experts, top-2, 1 shared expert  ·  4 EP ranks in panel 3  ·  numbers are illustrative",
         params="out = shared(x) + Σ_{i in top-k} w_i · expert_i(x)        w = normalized scores of the chosen experts")

# ============================================================================
# Panel 1: one token through an MoE layer
# ============================================================================
y0 = 112
P1_H = 330
d.panel(y0, P1_H, 1, "What happens to one token?",
        "The router scores all experts. The token goes to the top-2 experts and to the shared expert. A weighted sum joins the outputs.")

# token
ty = y0 + 160
d.box(46, ty - 26, 90, 52, "token x", ["[hidden]"], col=INK, fill=WHITE)

# router box with score bars
rx, ry, rw, rh = 176, y0 + 72, 300, 236
d.rect(rx, ry, rw, rh, fill=VIOLET[1], stroke=VIOLET[0], sw=1.5)
d.text(rx + 14, ry + 22, "Router (gate)", 14, VIOLET[0], "bold")
d.text(rx + 120, ry + 22, "s = score_fn(x · Wgate)", 11.5, INK, mono=True)
d.text(rx + 14, ry + 40, "pick top-2 of s + bias (bias = 0 here)", 11.5, MUTE, mono=True)
scores = [0.21, 0.35, 0.82, 0.18, 0.40, 0.74, 0.30, 0.25]
top = {2, 5}
for i, s in enumerate(scores):
    by = ry + 58 + i * 21
    d.text(rx + 14, by + 13, f"E{i}", 11.5, MUTE, "bold", mono=True)
    w = 200 * s
    col = AMBER if i in top else NEUTRAL
    d.rect(rx + 44, by + 2, w, 15, fill=col[1], stroke=col[0], rx=2, sw=1.1)
    d.text(rx + 50 + w, by + 14, f"{s:.2f}", 11, AMBER[0] if i in top else MUTE, "bold" if i in top else "normal", mono=True)
d.arrow(136, ty, rx - 2, ty, INK)

# experts column
ex = 540
d.text(ex, y0 + 90, "Routed experts", 13.5, INK, "bold")
for i in range(8):
    col = AMBER if i in top else NEUTRAL
    bx = ex + (i % 4) * 66
    by = y0 + 104 + (i // 4) * 46
    d.rect(bx, by, 58, 36, fill=col[1], stroke=col[0], rx=5, sw=1.8 if i in top else 1.1)
    d.text(bx + 29, by + 23, f"E{i}", 12.5, col[0] if i in top else MUTE, "bold", "middle", mono=True)
d.text(ex, y0 + 216, "weights:  w2 = 0.82/1.56 = 0.53", 11.5, AMBER[0], mono=True)
d.text(ex, y0 + 232, "          w5 = 0.74/1.56 = 0.47", 11.5, AMBER[0], mono=True)
d.rect(ex, y0 + 250, 256, 40, fill=TEAL[1], stroke=TEAL[0], rx=6, sw=1.6)
d.text(ex + 128, y0 + 275, "Shared expert (every token)", 12.5, TEAL[0], "bold", "middle")
d.arrow(rx + rw, ty - 30, ex - 2, ty - 30, AMBER[0])
d.arrow_label(rx + rw + 32, ty - 30, "top-2", AMBER[0])

# output
ox = 860
d.rect(ox, ty - 50, W - 46 - ox, 100, fill=WHITE, stroke=INK, sw=1.4)
d.text(ox + 12, ty - 26, "Output", 13.5, INK, "bold")
d.text(ox + 12, ty - 4, "shared(x)", 12, TEAL[0], "bold", mono=True)
d.text(ox + 12, ty + 14, "+ 0.53·E2(x)", 12, AMBER[0], "bold", mono=True)
d.text(ox + 12, ty + 32, "+ 0.47·E5(x)", 12, AMBER[0], "bold", mono=True)
d.arrow(ex + 266, ty, ox - 2, ty, INK)

# ============================================================================
# Panel 2: cost per token
# ============================================================================
y1 = y0 + P1_H + 20
P2_H = 200
d.panel(y1, P2_H, 2, "Why is MoE cheap per token?",
        "Compute per token grows with top-k + shared experts. Memory grows with all experts.")

bx0 = 300
full = 700
rows = [
    ("weights stored", 9, NEUTRAL, "8 routed + 1 shared = 9 expert FFNs"),
    ("weights used per token", 3, AMBER, "2 routed + 1 shared = 3 expert FFNs  (33 %)"),
]
for i, (lab, n, col, note) in enumerate(rows):
    yy = y1 + 76 + i * 46
    d.text(46, yy + 20, lab, 13, INK, "bold")
    for k in range(n):
        d.rect(bx0 + k * (full / 9), yy, full / 9 - 4, 30, fill=col[1], stroke=col[0], rx=3, sw=1.2)
    d.text(bx0 + n * (full / 9) + 6, yy + 20, note if n < 9 else "", 12, INK, mono=True)
    if n == 9:
        d.text(bx0, yy - 6, note, 11.5, MUTE, mono=True)
d.text(46, y1 + 184, "DeepInfer FFN FLOPs per token: 2 · 3 · hidden · moe_intermediate_size · (top_k + n_shared) with FP8 (flops_estimator.hpp:84-89).",
       12, MUTE)

# ============================================================================
# Panel 3: load balance
# ============================================================================
y2 = y1 + P2_H + 20
P3_H = 300
d.panel(y2, P3_H, 3, "Why does load balance matter with expert parallelism?",
        "Each EP rank holds 2 experts. The rank with the most tokens sets the time of the step for all ranks.")

counts = [50, 10, 20, 20, 120, 15, 25, 30]
scale = 1.0
base_y = y2 + 250
gx0 = 70
for r in range(4):
    rx0 = gx0 + r * 250
    d.text(rx0 + 60, base_y + 22, f"rank {r}", 12.5, INK, "bold", "middle", mono=True)
    tot = 0
    for k in range(2):
        e = 2 * r + k
        c = counts[e]
        hh = c * 1.3
        col = PINK if e == 4 else BLUE
        d.rect(rx0 + k * 62, base_y - hh, 54, hh, fill=col[1], stroke=col[0], rx=2, sw=1.2)
        d.text(rx0 + k * 62 + 27, base_y - hh - 6, f"E{e}:{c}", 11.5, col[0], "bold", "middle", mono=True)
        tot += c
    d.text(rx0 + 140, base_y - 8, f"Σ {tot}", 12.5, PINK[0] if tot == max(counts[0] + counts[1], counts[2] + counts[3], counts[4] + counts[5], counts[6] + counts[7]) else INK, "bold", mono=True)
d.line(46, base_y, W - 46, base_y, col=LINE, sw=1)
d.text(W - 46, y2 + 84, "mean 72.5 tokens per rank · max 135 · max / mean = 1.86", 12.5, PINK[0], "bold", anchor="end", mono=True)
d.text(W - 46, y2 + 104, "ranks 0, 1, 3 wait for rank 2 in the combine", 12, MUTE, anchor="end", italic=True)

y = y2 + P3_H + 24
d.legend(30, y, [(VIOLET, "router"), (AMBER, "chosen experts"), (TEAL, "shared expert"), (BLUE, "tokens per expert"),
                 (PINK, "hot expert / slowest rank")])
y += 36
y = d.footnotes(30, y, [
    "Simplified: score_fn, the bias and the weight normalization follow DeepInfer's gate arguments; the exact kernel math is in vendor code.",
    "DeepInfer reads the number of experts, top-k and the shared experts from the checkpoint config (hugging_face/config.py:164-174).",
])
d.save(height=y + 10)
