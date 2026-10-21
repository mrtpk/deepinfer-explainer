"""Diagram: mHC residual mixing around one sub-layer, with a toy example, and where the mixes run.

Used by: src/concepts/mhc-residual.html ("The picture")
Sources (commit 9bd9cf2):
  deepinfer/model_executor/models/v4_modules/hc.py:57-69        HCLayerMixin docstring: pre / post, lazy post data, shifted
  deepinfer/model_executor/models/v4_modules/hc.py:174-227      _hc_fused_post_pre: previous post + this pre
  deepinfer/model_executor/models/v4_modules/hc.py:317-364      _hc_pre: mixes, Sinkhorn, apply, layer norm
  deepinfer/model_executor/models/v4_modules/mhc_ops.py:60-92   split into pre [m], post [m], comb [m, m]
  deepinfer/model_executor/models/v4_modules/mhc_ops.py:117-148 mhc_pre_norm_fn: fn GEMM + RMS epilogue
  deepinfer/model_executor/models/deepseek.py:225-239           fold at the end of the model
  csrc/engine/flops_estimator.hpp:107-111                       fn [C*H, C*(C+2)], post = C*(C+1)*H terms
The toy numbers (m = 2, H = 3, mix values, F output) are illustrative. The exact kernel formulas
are in tile_kernels / DeepGEMM, which are not in the repo.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import INK, MUTE, NEUTRAL, TEAL, VIOLET, AMBER, Diagram  # noqa: E402

d = Diagram(width=1100)
d.header(
    "mHC: the residual stream as hc_mult parallel streams",
    "One sub-layer (attention or MoE)  ·  toy sizes: m = 2 streams, H = 3  ·  mix values are illustrative",
    params="trunk R [T, m, H]  ·  pre [T, m, 1]  ·  post [T, m, 1]  ·  comb [T, m, m]  ·  m = hc_mult",
)

TS, MS = 14, 12.5


def card(x, y, w, h, title, lines, col, sub=None):
    d.rect(x, y, w, h, fill=col[1], stroke=col, sw=1.5)
    d.text(x + 14, y + 24, title, TS, col[0], "bold")
    yy = y + 24
    if sub:
        d.text(x + 14, y + 43, sub, 12, MUTE)
        yy = y + 43
    for i, s in enumerate(lines):
        d.text(x + 14, yy + 21 + i * 18, s, MS, INK, mono=True)


# ============================================================================
# Panel 1: plain residual vs mHC
# ============================================================================
y0 = 112
P1_H = 236
d.panel(y0, P1_H, 1, "How is mHC different from a plain residual?",
        "A plain residual adds F(x) to one stream. mHC keeps m streams and mixes them with weights per token.")
bw, bh = 489, 140
xa, xb = 46, 46 + bw + 30
r1 = y0 + 72
card(xa, r1, bw, bh, "Plain residual (one stream)", [
    "x                 [T, H]",
    "y = F(RMSNorm(x)) [T, H]",
    "x_next = x + y    [T, H]",
    "the same 1.0 weights for every token",
], NEUTRAL, sub="what most transformers do")
card(xb, r1, bw, bh, "mHC (m streams)", [
    "R                            [T, m, H]",
    "x_in = sum_j pre_j * R_j     [T, H]",
    "y = F(RMSNorm(x_in))         [T, H]",
    "R_next = comb @ R + post * y [T, m, H]",
], TEAL, sub="HCLayerMixin (hc.py:57-69)")

# ============================================================================
# Panel 2: one sub-layer with toy numbers
# ============================================================================
y0b = y0 + P1_H + 22
P2_H = 266
d.panel(y0b, P2_H, 2, "What happens around one sub-layer?",
        "Pre makes one input from the m streams. Post writes the sub-layer output back into all m streams.")
cw, ch, gx = 310, 172, 39
xs = [46, 46 + cw + gx, 46 + 2 * (cw + gx)]
r2 = y0b + 72
card(xs[0], r2, cw, ch, "1  Mixes from the trunk", [
    "R0 = [1, 2, 3]",
    "R1 = [3, 0, -1]",
    "fn @ RMSnorm(R) -> 2m + m² = 8",
    "pre  = [0.75, 0.25]",
    "post = [1.2, 0.8]",
    "comb = [[0.9, 0.1], [0.1, 0.9]]",
], TEAL, sub="_hc_pre: norm_fn, split, Sinkhorn")
card(xs[1], r2, cw, ch, "2  Pre apply, norm, sub-layer", [
    "x_in = 0.75*R0 + 0.25*R1",
    "     = [1.5, 1.5, 2.0]",
    "RMSNorm(x_in) -> F",
    "y = [0.2, -0.4, 0.6]",
    "(F = attention or MoE)",
], VIOLET, sub="layer_input -> layer_norm -> F")
card(xs[2], r2, cw, ch, "3  Post: back into the trunk", [
    "R0' = 0.9*R0 + 0.1*R1 + 1.2*y",
    "    = [1.44, 1.32, 3.32]",
    "R1' = 0.1*R0 + 0.9*R1 + 0.8*y",
    "    = [2.96, -0.12, -0.12]",
    "comb part keeps the sum",
    "R0 + R1 = [4, 2, 2]",
], TEAL, sub="hc_post -> mhc_post")
cy = r2 + ch / 2
d.arrow(xs[0] + cw, cy, xs[1] - 2, cy, TEAL[0], sw=2)
d.arrow(xs[1] + cw, cy, xs[2] - 2, cy, VIOLET[0], sw=2)

# ============================================================================
# Panel 3: where the mixes run
# ============================================================================
y0c = y0b + P2_H + 22
P3_H = 250
d.panel(y0c, P3_H, 3, "Where do the mixes run in DeepInfer?",
        "The post of one sub-layer and the pre of the next run in one call. The model ends with one fold.")
r3 = y0c + 72
card(xs[0], r3, cw, 140, "Start: first layer", [
    "embedding  [T, H]",
    "expand_to_mhc -> [T, m, H]",
    "(the same row in each stream)",
    "no post yet, only pre",
], AMBER, sub="_hc_fused_post_pre (hc.py:203-208)")
card(xs[1], r3, cw, 140, "Each sub-layer boundary", [
    "post of the previous sub-layer",
    "+ pre of this sub-layer",
    "+ RMSNorm (+ FP8 cast)",
    "one mega_mhc call when it can",
], TEAL, sub="attn_norm_forward / ffn_norm_forward")
card(xs[2], r3, cw, 140, "End: fold to one stream", [
    "last post -> [T, m, H]",
    "shifted: apply last pre mix",
    "else: HCHead",
    "output_norm -> [T, H]",
], AMBER, sub="deepseek.py:225-239")
cy3 = r3 + 70
d.arrow(xs[0] + cw, cy3, xs[1] - 2, cy3, INK, sw=2)
d.arrow(xs[1] + cw, cy3, xs[2] - 2, cy3, INK, sw=2)
d.text(xs[1] + cw / 2, r3 + 140 + 22, "x 2 per layer (attention, MoE)", 12, MUTE, anchor="middle", italic=True)

y = y0c + P3_H + 24
d.legend(30, y, [(TEAL, "mHC mixing"), (VIOLET, "sub-layer F"), (AMBER, "model start / end"),
                 (NEUTRAL, "plain residual")])
y += 40
y = d.footnotes(30, y, [
    "Simplified: the formulas are a model of the kernels (tile_kernels, DeepGEMM), which are not in the repo. They match the",
    "  kernel names, the shapes and the FLOP counts in flops_estimator.hpp:107-111. All numbers are toy values.",
    "With hc_shifted (HF default), the pre mix that a sub-layer applies comes from the sub-layer before it (hc.py:64-67).",
])
d.save(height=y + 10)
