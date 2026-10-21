"""Diagram: one verification step of speculative decoding, and why the output still follows q.

Used by: src/concepts/speculative-decoding.html ("The picture")
Sources (commit 9bd9cf2):
  csrc/engine/prepare_sample.cpp:202-206, 220-225       decode: all seqlen_q rows; row j reads draft j; last row reads slot 0
  deepinfer/model_executor/layers/tilelang_ops/sampler.py:13-25    is_verify = every row except the last of a request
  deepinfer/model_executor/layers/tilelang_ops/fused_sample.py:227-246  accept if exp(min(lq - lp, 0)) > U, else residual
  deepinfer/model_executor/layers/tilelang_ops/sampler.py:227-248  accepted prefix; is_final = first blocked row
Panel 2 numbers are a toy example (4 tokens), not model output.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, GRAY_MID, INK, LINE, MUTE, NEUTRAL, PINK, WHITE, Diagram  # noqa: E402

d = Diagram(width=1100)
W = d.W

d.header(
    "Speculative decoding: one step checks 5 drafts",
    "Draft model proposes  →  target model runs once on all inputs  →  accept a prefix, then sample one more token",
    params="nextn = 5  ·  seqlen_q = 1 + 5 = 6 rows per request  ·  row j checks draft j+1  ·  p = draft, q = target",
)

# ---------------------------------------------------------------- panel 1
y0 = 112
P1 = 304
d.panel(y0, P1, 1, "Which row checks which draft? Row j checks draft j+1",
        "The target model sees the last real token and the 5 drafts. Each row predicts the token after its input.")

cw, gap = 150, 18
x0 = 46
tok_y = y0 + 96
labels = ["t (pos 49)", "d1 (50)", "d2 (51)", "d3 (52)", "d4 (53)", "d5 (54)"]
d.text(x0, tok_y - 12, "input tokens (positions)", 12.5, MUTE, "bold")
for i, lab in enumerate(labels):
    x = x0 + i * (cw + gap)
    col = BLUE if i == 0 else PINK
    d.rect(x, tok_y, cw, 34, fill=col[1], stroke=col[0], rx=6, sw=1.4)
    d.text(x + cw / 2, tok_y + 22, lab, 13, col[0], "bold", "middle", mono=True)

row_y = tok_y + 72
for i in range(6):
    x = x0 + i * (cw + gap)
    d.arrow(x + cw / 2, tok_y + 34, x + cw / 2, row_y - 2, INK)
    d.rect(x, row_y, cw, 34, fill=WHITE, stroke=INK, rx=6, sw=1.3)
    d.text(x + cw / 2, row_y + 22, f"target row {i}", 13, INK, "bold", "middle", mono=True)

dec_y = row_y + 58
decisions = [
    ("check d1: accept", EMERALD),
    ("check d2: accept", EMERALD),
    ("check d3: reject", AMBER),
    ("not used", NEUTRAL),
    ("not used", NEUTRAL),
    ("bonus (if all pass)", NEUTRAL),
]
for i, (s, col) in enumerate(decisions):
    x = x0 + i * (cw + gap)
    d.arrow(x + cw / 2, row_y + 34, x + cw / 2, dec_y - 2, col[0] if col is not NEUTRAL else GRAY_MID,
            dash=None if col is not NEUTRAL else "5 4")
    d.rect(x, dec_y, cw, 34, fill=col[1], stroke=col[0], rx=6, sw=1.4, dash=None if col is not NEUTRAL else "4 3")
    d.text(x + cw / 2, dec_y + 22, s, 12, col[0] if col is not NEUTRAL else MUTE, "bold", "middle")

out_y = dec_y + 56
d.text(x0, out_y, "Output of this step:", 13, INK, "bold")
d.text(x0 + 148, out_y, "d1, d2, r   (r = sample from the residual of row 2)   →  3 tokens, 2 accepted drafts", 13, INK, mono=True)

# ---------------------------------------------------------------- panel 2
y1 = y0 + P1 + 20
P2 = 360
d.panel(y1, P2, 2, "Why is the output still correct? Worked example with 4 tokens",
        "Accept with min(1, q/p). On reject, sample max(q − p, 0). Together they give exactly q.")

toks = ["A", "B", "C", "D"]
p = [0.6, 0.3, 0.1, 0.0]
q = [0.4, 0.4, 0.1, 0.1]
mn = [min(a, b) for a, b in zip(p, q)]
res = [max(b - a, 0) for a, b in zip(p, q)]
reject = sum(res)  # 0.2

ch_top = y1 + 96
ch_h = 160          # height of probability 1.0 -> scale so 0.6 fits
scale = ch_h / 0.65
base = ch_top + ch_h
cols_x = [46, 400, 754]
titles = ["Draft p (proposes)", "Target q (wanted)", "Result of the rule"]
bw, bg = 52, 22
for k, title in enumerate(titles):
    cx = cols_x[k]
    d.text(cx, ch_top - 16, title, 14, INK, "bold")
    d.line(cx, base, cx + 4 * (bw + bg), base, LINE, 1)
    for i, t in enumerate(toks):
        bx = cx + 6 + i * (bw + bg)
        if k == 0:
            h = p[i] * scale
            d.rect(bx, base - h, bw, h, fill=PINK[1], stroke=PINK[0], rx=2, sw=1.2) if h > 0 else None
            d.text(bx + bw / 2, base - h - 6, f"{p[i]:.1f}", 12, PINK[0], "bold", "middle", mono=True)
        elif k == 1:
            h = q[i] * scale
            d.rect(bx, base - h, bw, h, fill=BLUE[1], stroke=BLUE[0], rx=2, sw=1.2)
            d.text(bx + bw / 2, base - h - 6, f"{q[i]:.1f}", 12, BLUE[0], "bold", "middle", mono=True)
        else:
            h1 = mn[i] * scale
            h2 = res[i] * scale
            if h1 > 0:
                d.rect(bx, base - h1, bw, h1, fill=EMERALD[1], stroke=EMERALD[0], rx=2, sw=1.2)
            if h2 > 0:
                d.rect(bx, base - h1 - h2, bw, h2, fill=AMBER[1], stroke=AMBER[0], rx=2, sw=1.2)
            d.text(bx + bw / 2, base - h1 - h2 - 6, f"{mn[i] + res[i]:.1f}", 12, INK, "bold", "middle", mono=True)
        d.text(bx + bw / 2, base + 18, t, 13, INK, "bold", "middle", mono=True)

ty = base + 46
d.text(46, ty, "Accept probability min(1, q/p):  A 0.67   B 1   C 1", 12.5, INK, mono=True)
d.text(46, ty + 20, "P(reject) = Σ max(q − p, 0) = 0.1 + 0.1 = 0.2", 12.5, INK, mono=True)
d.text(560, ty, "■ accepted part = min(p, q)", 12.5, EMERALD[0], "bold")
d.text(560, ty + 20, "■ residual part = P(reject) × max(q − p, 0) / 0.2", 12.5, AMBER[0], "bold")
d.text(560, ty + 40, "Sum per token = q:  0.4  0.4  0.1  0.1", 12.5, INK, "bold", mono=True)

y = y1 + P2 + 24
d.legend(30, y, [(PINK, "draft model p"), (BLUE, "target model q"), (EMERALD, "accepted"),
                 (AMBER, "rejected → residual sample")])
y += 36
y = d.footnotes(30, y, [
    "Panel 1 uses the example of the tour “One speculative decoding round”: request \"1\", input positions 49 to 54.",
    "Panel 2 is a toy example. DeepInfer uses max(q − α·p, 0) with α = exp(−5e-5) for the residual (tilelang_ops/common.py:3-19).",
])
d.save(height=y + 10)
