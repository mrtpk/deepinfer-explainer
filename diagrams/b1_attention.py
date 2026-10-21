"""Diagram: scaled dot-product attention with a causal mask, a worked row, and KV-head sharing.

Used by: src/learn/attention.html (section "The picture")
Worked numbers (one head, d_h = 2) match the example on src/learn/kv-cache.html:
  keys  The (1,0), cat (0,1), sat (1,1), on (2,1); values (2,0), (0,2), (1,1), (0,3); q(on) = (1,2)
  scores 1, 2, 3, 4; scaled by 1/sqrt(2); softmax -> 0.065, 0.131, 0.266, 0.539; output (0.395, 2.144)
DeepInfer notes (commit 9bd9cf2):
  deepinfer/model_executor/models/v4_modules/attn.py:78   softmax_scale = head_dim ** -0.5
  deepinfer/worker/cache_engine.py:624                     num_key_value_heads == 1 (one KV head)
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, CELL_EMPTY, EMERALD, INK, LINE, MUTE, PINK, VIOLET, WHITE, Diagram  # noqa: E402

W = 1100
d = Diagram(width=W)
d.header("Attention, step by step",
         "One head  ·  4 tokens  ·  head size d_h = 2  ·  made-up numbers, the same as on the KV cache page")

toks = ["The", "cat", "sat", "on"]
Q = [(1, 0), (0, 1), (0, 2), (1, 2)]
K = [(1, 0), (0, 1), (1, 1), (2, 1)]
V = [(2, 0), (0, 2), (1, 1), (0, 3)]

# ---- panel 1: Q K V ------------------------------------------------------------------
y0 = 92
P1 = 214
d.panel(y0, P1, 1, "Where do queries, keys and values come from?",
        "Three weight matrices turn each token's hidden state into a query, a key and a value.")
by = y0 + 74
d.text(46, by + 50, "X", 15, BLUE[0], "bold", mono=True)
d.text(46, by + 72, "[T, d]", 13, INK, mono=True)
d.text(46, by + 92, "hidden", 12, MUTE)
d.text(46, by + 108, "states", 12, MUTE)
mats = [("Q = X·W_Q", Q, BLUE, "what this token looks for"), ("K = X·W_K", K, AMBER, "what this token offers"),
        ("V = X·W_V", V, EMERALD, "what this token gives")]
d.circle(118, by + 56, 4, INK)
d.line(102, by + 56, 118, by + 56, INK, sw=1.6)
for i, (name, M, col, note) in enumerate(mats):
    bx = 160 + i * 300
    d.box(bx, by, 266, 112, name, [], col=col, tsize=14)
    for r, t in enumerate(toks):
        d.text(bx + 24, by + 42 + r * 16, f"{t:<4}({M[r][0]}, {M[r][1]})", 12.5, INK, mono=True)
    d.text(bx + 133, by + 128, note, 12, MUTE, anchor="middle", italic=True)
d.arrow(118, by + 56, 158, by + 56, INK)
d.path_arrow(f"M 118,{by + 56} L 118,{by - 8} L 593,{by - 8} L 593,{by - 2}", INK)
d.path_arrow(f"M 118,{by - 8} L 893,{by - 8} L 893,{by - 2}", INK)

# ---- panel 2: the worked row -----------------------------------------------------------
y1 = y0 + P1 + 20
P2 = 280
d.panel(y1, P2, 2, "How does one token mix the others?",
        "Scores, then the causal mask, then softmax, then a weighted sum of values. Row \"on\" is worked out.")
gy = y1 + 104
cs = 46
gx = 120
d.text(46, gy - 22, "S = Q·Kᵀ / √d_h", 13, INK, "bold", mono=True)
for j, t in enumerate(toks):
    d.text(gx + j * cs + cs / 2, gy - 0, t, 11.5, MUTE, anchor="middle", mono=True)
for i in range(4):
    yy = gy + 8 + i * 34
    d.text(gx - 8, yy + 21, toks[i], 12, BLUE[0] if i == 3 else MUTE, "bold" if i == 3 else "normal", anchor="end",
           mono=True)
    for j in range(4):
        xx = gx + j * cs
        if j > i:
            d.rect(xx, yy, cs - 4, 30, fill=CELL_EMPTY, stroke=LINE, rx=2, sw=0.8)
            d.text(xx + (cs - 4) / 2, yy + 20, "−∞", 12, MUTE, anchor="middle", mono=True)
        else:
            s = (Q[i][0] * K[j][0] + Q[i][1] * K[j][1]) / math.sqrt(2)
            hl = i == 3
            d.rect(xx, yy, cs - 4, 30, fill=BLUE[1] if hl else WHITE, stroke=BLUE if hl else LINE, rx=2,
                   sw=1.2 if hl else 0.8)
            d.text(xx + (cs - 4) / 2, yy + 20, f"{s:.2f}", 11.5, INK, anchor="middle", mono=True)
d.text(gx, gy + 160, "grey: future token, masked", 12, MUTE, italic=True)

# softmax box
sx = 440
sc = [1 / math.sqrt(2), 2 / math.sqrt(2), 3 / math.sqrt(2), 4 / math.sqrt(2)]
m = max(sc)
e = [math.exp(v - m) for v in sc]
w = [v / sum(e) for v in e]
d.arrow(gx + 4 * cs + 4, gy + 125, sx - 2, gy + 125, BLUE)
d.arrow_label((gx + 4 * cs + sx) / 2, gy + 125, "row on", BLUE)
d.rect(sx, gy - 24, 290, 190, fill=VIOLET[1], stroke=VIOLET, rx=8, sw=1.5)
d.text(sx + 145, gy - 2, "softmax → weights", 14, VIOLET[0], "bold", "middle")
for j, t in enumerate(toks):
    yy = gy + 16 + j * 34
    d.text(sx + 16, yy + 15, f"{t:<4}", 12.5, INK, mono=True)
    d.rect(sx + 62, yy + 2, 150 * w[j] / max(w), 16, fill=VIOLET[0], stroke=VIOLET, rx=2, sw=1)
    d.text(sx + 70 + 150 * w[j] / max(w), yy + 15, f"{w[j]:.3f}", 12.5, INK, mono=True)
d.text(sx + 145, gy + 156, "sum = 1.000", 12, MUTE, anchor="middle", mono=True)

# output box
ox = 790
o = [sum(w[j] * V[j][c] for j in range(4)) for c in range(2)]
d.arrow(sx + 290, gy + 70, ox - 2, gy + 70, VIOLET)
d.rect(ox, gy - 24, 264, 190, fill=EMERALD[1], stroke=EMERALD, rx=8, sw=1.5)
d.text(ox + 132, gy - 2, "output = Σ weight · value", 14, EMERALD[0], "bold", "middle")
for j in range(4):
    d.text(ox + 16, gy + 30 + j * 22, f"{w[j]:.3f} × ({V[j][0]}, {V[j][1]})", 12.5, INK, mono=True)
d.line(ox + 16, gy + 110, ox + 248, gy + 110, LINE, sw=1)
d.text(ox + 16, gy + 134, f"= ({o[0]:.3f}, {o[1]:.3f})", 13.5, EMERALD[0], "bold", mono=True)

# ---- panel 3: KV heads ------------------------------------------------------------------
y2 = y1 + P2 + 20
P3 = 210
d.panel(y2, P3, 3, "Why do GQA, MQA and MLA save memory?",
        "The KV cache keeps K and V for every KV head. Fewer KV heads means fewer bytes per token. MLA: see below.")
kinds = [("MHA: 8 KV heads", 8, "every query head has its own K, V"),
         ("GQA: 2 KV heads", 2, "4 query heads share one K, V"),
         ("MQA: 1 KV head", 1, "all 8 query heads share one K, V")]
for i, (t, nkv, note) in enumerate(kinds):
    bx = 46 + i * 354
    d.rect(bx, y2 + 70, 300, 116, fill=WHITE, stroke=INK, rx=8, sw=1.2)
    d.text(bx + 150, y2 + 92, t, 14, INK, "bold", "middle")
    d.text(bx + 14, y2 + 120, "Q", 12, BLUE[0], "bold", mono=True)
    d.text(bx + 14, y2 + 158, "KV", 12, AMBER[0], "bold", mono=True)
    for h in range(8):
        cx = bx + 46 + h * 30
        d.rect(cx, y2 + 106, 22, 20, fill=BLUE[1], stroke=BLUE, rx=3, sw=1.2)
        g = h * nkv // 8
        gxk = bx + 46 + (g * (8 // nkv)) * 30 + (8 // nkv - 1) * 15
        d.line(cx + 11, y2 + 126, gxk + 11, y2 + 144, LINE, sw=1)
    for g in range(nkv):
        cx = bx + 46 + (g * (8 // nkv)) * 30 + (8 // nkv - 1) * 15
        d.rect(cx, y2 + 144, 22, 20, fill=AMBER[1], stroke=AMBER, rx=3, sw=1.2)
    d.text(bx + 150, y2 + 180, note, 12, MUTE, anchor="middle")

y = y2 + P3 + 22
d.legend(30, y, [(BLUE, "query"), (AMBER, "key / KV head"), (EMERALD, "value / output"), (VIOLET, "softmax weights"),
                 (PINK, "—")][:4])
y += 36
y = d.footnotes(30, y, [
    "MLA (DeepSeek, DeepInfer): one 512-number entry shared by all heads; compressed layers keep one entry per group of tokens.",
    "DeepInfer uses scale 1/√head_dim (v4_modules/attn.py:78) and checks one KV head (worker/cache_engine.py:624).",
    "Real heads have 64 to 512 numbers per vector, and a layer has many heads. See the page MLA attention.",
])
d.save(height=y + 8)
