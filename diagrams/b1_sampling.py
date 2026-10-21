"""Diagram: from logits to one token: temperature, top-p, top-k, renormalize, seeded draw.

Used by: src/learn/sampling.html (section "The picture")
Order and rules from DeepInfer (commit 9bd9cf2):
  deepinfer/model_executor/layers/tilelang_ops/fused_sample.py:209-211   logits / T, then top-p, then top-k, then log_softmax
  deepinfer/model_executor/layers/tilelang_ops/fused_sample.py:137-150   top-p on the full softmax; top-k on what is left
  deepinfer/model_executor/layers/tilelang_ops/random_sampling.py:76-84  u = hash(seed, position); first CDF bar above u
Logits are made up (6 candidate tokens). top_p = 0.8, top_k = 2, u = 0.70.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, CELL_EMPTY, EMERALD, INK, LINE, MUTE, VIOLET, WHITE, Diagram  # noqa: E402

W = 1100
d = Diagram(width=W)
d.header("Sampling: from logits to one token",
         "Made-up logits for 6 candidate tokens  ·  temperature 1.0, top_p 0.8, top_k 2  ·  order as in DeepInfer's sampler")

toks = ["mat", "floor", "sofa", "bed", "roof", "moon"]
L = [3.0, 2.5, 2.0, 1.5, 0.5, -1.0]


def softmax(v):
    m = max(v)
    e = [math.exp(x - m) for x in v]
    s = sum(e)
    return [x / s for x in e]


p1 = softmax(L)
p05 = softmax([x / 0.5 for x in L])

# ---- panel 1: the pipeline ----------------------------------------------------------------
y0 = 92
P1 = 196
d.panel(y0, P1, 1, "Which steps turn logits into one token?",
        "Three steps, in this order. Each step only removes or reshapes probability; the draw comes last.")
cards = [
    ("1  Temperature", ["p = softmax(logits / T)", "T < 1: sharper", "T > 1: flatter"], BLUE),
    ("2  top-p, then top-k", ["keep the smallest top group", "with mass ≥ top_p, then cut", "it to top_k; renormalize"],
     VIOLET),
    ("3  Seeded draw", ["u = hash(seq_seed, position)", "pick the first token whose", "running sum passes u"], EMERALD),
]
for i, (t, lines, col) in enumerate(cards):
    bx = 46 + i * 354
    d.box(bx, y0 + 72, 300, 100, t, [], col=col, tsize=14)
    for j, s in enumerate(lines):
        d.text(bx + 18, y0 + 116 + j * 19, s, 12.5, INK, mono=(j == 0 and i != 1))
    if i < 2:
        d.arrow(bx + 300, y0 + 122, bx + 352, y0 + 122, INK)

# ---- panel 2: worked table ----------------------------------------------------------------------
y1 = y0 + P1 + 20
P2 = 84 + 6 * 30 + 44
d.panel(y1, P2, 2, "What happens to six candidates?",
        "Columns left to right follow the steps. A dash means the token is removed (probability 0).")
cols_x = [46, 140, 230, 400, 570, 760]
heads = ["token", "logit", "p at T = 1.0", "p at T = 0.5", "T = 1, top_p 0.8", "T = 1, top_p, top_k 2"]
hy = y1 + 82
for x, h in zip(cols_x, heads):
    d.text(x, hy, h, 12.5, MUTE, "bold")
cum = 0.0
kept_p = []
for i in range(6):
    if cum <= 0.8:
        kept_p.append(i)
    cum += p1[i]
kept_k = kept_p[:2]
sp = sum(p1[i] for i in kept_p)
sk = sum(p1[i] for i in kept_k)
for i, t in enumerate(toks):
    yy = hy + 14 + i * 30
    d.text(cols_x[0], yy + 17, t, 13, INK, mono=True)
    d.text(cols_x[1], yy + 17, f"{L[i]:+.1f}", 13, INK, mono=True)
    for c, (val, col, on) in enumerate([(p1[i], BLUE, True), (p05[i], BLUE, True),
                                         (p1[i] / sp, VIOLET, i in kept_p), (p1[i] / sk, EMERALD, i in kept_k)]):
        x = cols_x[2 + c]
        if on:
            d.rect(x, yy + 5, 110 * val, 15, fill=col[1], stroke=col, rx=2, sw=1.1)
            d.text(x + 116 * max(val, 0.02) + 4, yy + 17, f"{val:.3f}", 12.5, INK, mono=True)
        else:
            d.text(x + 4, yy + 17, "—", 13, MUTE, mono=True)
fy = hy + 14 + 6 * 30 + 10
d.text(cols_x[4], fy + 6, "mass before sofa: 0.699 ≤ 0.8 → sofa stays", 12, MUTE, italic=True)

# ---- panel 3: the draw -----------------------------------------------------------------------------
y2 = y1 + P2 + 20
P3 = 176
d.panel(y2, P3, 3, "How does the draw pick a token?",
        "Stack the kept probabilities from 0 to 1. A seeded number u falls into one bar; that token wins.")
bx, by, bw = 120, y2 + 92, 820
x = bx
for i in kept_k:
    w = bw * p1[i] / sk
    win = i == 1
    d.rect(x, by, w, 34, fill=EMERALD[1] if win else CELL_EMPTY, stroke=EMERALD if win else LINE, rx=0,
           sw=2.6 if win else 1.3)
    d.text(x + w / 2, by + 22, f"{toks[i]}  {p1[i] / sk:.3f}", 13, INK, anchor="middle", mono=True)
    x += w
d.text(bx - 10, by + 22, "0", 12.5, MUTE, anchor="end", mono=True)
d.text(bx + bw + 10, by + 22, "1", 12.5, MUTE, mono=True)
ux = bx + bw * 0.70
d.line(ux, by - 16, ux, by + 50, INK, sw=2)
d.text(ux, by - 22, "u = 0.70", 12.5, INK, "bold", anchor="middle", mono=True)
d.text(bx, by + 66, f"running sum: mat ends at {p1[0] / sk:.3f} < 0.70; floor ends at 1.000 ≥ 0.70 → the sampler picks floor",
       12.5, INK)

y = y2 + P3 + 22
d.legend(30, y, [(BLUE, "after temperature"), (VIOLET, "after top-p"), (EMERALD, "after top-k / token picked")])
y += 36
y = d.footnotes(30, y, [
    "DeepInfer computes this in one kernel per batch (fused_sample.py:94-117). The order follows the reference fused_sample_ref.",
    "u comes from a hash of the request seed and the token position, so the same seed gives the same token (random_sampling.py:76-84).",
    "Temperature 0 is replaced with 1e-5, top_p 1 and top_k -1, which picks the most likely token (sampling_params.py:76-79).",
])
d.save(height=y + 8)
