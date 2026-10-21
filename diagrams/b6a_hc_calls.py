"""Diagram: the call paths inside HCLayerMixin (hc.py) and the operators they use.

Used by: src/code/v4-hc.html ("Where it sits")
Sources (commit 9bd9cf2):
  deepinfer/model_executor/models/v4_modules/hc.py:97-101     use_mega_mhc condition
  deepinfer/model_executor/models/v4_modules/hc.py:174-227    _hc_fused_post_pre: five cases
  deepinfer/model_executor/models/v4_modules/hc.py:229-315    _mega_mhc: one deep_gemm.mega_mhc call
  deepinfer/model_executor/models/v4_modules/hc.py:317-364    _hc_pre: non-shifted (big fuse) vs shifted
  deepinfer/model_executor/models/v4_modules/mhc_modeling.py:72-142   mhc_pre_big_fuse
  deepinfer/model_executor/models/v4_modules/mhc_ops.py:25-148        operators
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, INK, MUTE, TEAL, VIOLET, Diagram  # noqa: E402

d = Diagram(width=1100)
d.header(
    "Inside HCLayerMixin: one call per sub-layer boundary",
    "attn_norm_forward / ffn_norm_forward -> _hc_fused_post_pre -> _hc_pre  ·  hc_enabled  ·  commit 9bd9cf2",
    params="x = previous sub-layer output [T, H]  ·  lazy = HCLazyPostData  ·  R = trunk [T, m, H]  ·  m = hc_mult",
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


cw, gx = 310, 39
xs = [46, 46 + cw + gx, 46 + 2 * (cw + gx)]

# ============================================================================
# Panel 1: the five cases of _hc_fused_post_pre
# ============================================================================
y0 = 112
P1_H = 384
d.panel(y0, P1_H, 1, "Which path does _hc_fused_post_pre take?",
        "The checks run from top to bottom (hc.py:195-224). The first case that matches wins.")
r1 = y0 + 72
ch = 132
card(xs[0], r1, cw, ch, "A  Fused: mega_mhc", [
    "GPU, m == 4, fn width % 4096 == 0",
    "no Engram hook, x is 2-D,",
    "lazy has post data",
    "-> one deep_gemm.mega_mhc",
], BLUE, sub="hc.py:195-202, 229-315")
card(xs[1], r1, cw, ch, "B  First layer", [
    "lazy is None, x is 2-D",
    "R = expand_to_mhc(x, m)",
    "shifted: one-hot pre mix",
    "(read only stream 0)",
], AMBER, sub="hc.py:203-208")
card(xs[2], r1, cw, ch, "C  Full trunk as input", [
    "lazy is None, x is 3-D",
    "R = x  (the nextn input)",
    "assert: not shifted",
    "",
], AMBER, sub="hc.py:209-212")
r1b = r1 + ch + 26
card(xs[0], r1b, cw, ch, "D  Post already done", [
    "lazy.residual is None",
    "assert shifted, x is 3-D",
    "R = x, keep lazy.pre mix",
    "(no code path reaches it)",
], AMBER, sub="hc.py:213-219")
card(xs[1], r1b, cw, ch, "E  Normal: post, then pre", [
    "R = hc_post(x, lazy)",
    "  = mhc_post(x, R_old, post, comb)",
    "keep lazy.pre_layer_mix",
    "lazy.clear()",
], TEAL, sub="hc.py:220-224")
card(xs[2], r1b, cw, ch, "Then (B to E)", [
    "Engram hook on R (if any)",
    "_hc_pre(R, modules, pre mix)",
    "-> fp8/bf16 input [T, H]",
    "   + new HCLazyPostData",
], VIOLET, sub="hc.py:225-227")
d.arrow(xs[1] + cw, r1b + ch / 2, xs[2] - 2, r1b + ch / 2, TEAL[0], sw=2)

# ============================================================================
# Panel 2: _hc_pre
# ============================================================================
y0b = y0 + P1_H + 22
P2_H = 300
d.panel(y0b, P2_H, 2, "How does _hc_pre make the sub-layer input?",
        "Two ways. Without hc_shifted one fused operator does it all. With hc_shifted four operators run.")
r2 = y0b + 72
bw = 489
card(46, r2, bw, 150, "Not shifted: mhc_pre_big_fuse", [
    "mhc_prenorm_gemm(R, fn)  TF32 GEMM",
    "  -> partial sums [S, T, 2m+m²], sqr_sum",
    "mhc_pre_big_fuse_fwd: RMS, split,",
    "  Sinkhorn, apply -> post, comb, x_in",
], TEAL, sub="mhc_modeling.py:72-142")
card(46 + bw + 30, r2, bw, 150, "Shifted: four operators", [
    "x_in = mhc_pre_apply_mix(R, prev pre)",
    "mixes = mhc_pre_norm_fn(R, fn) [T, 2m+m²]",
    "pre, post, comb = mhc_pre_split_mixes",
    "comb = sinkhorn_normalize(comb)",
], TEAL, sub="hc.py:340-358")
r2b = r2 + 150 + 22
d.rect(46, r2b, 1008, 40, fill=VIOLET[1], stroke=VIOLET, sw=1.5)
d.text(60, r2b + 25, "Both:  layer_norm(x_in) -> (fp8, sf) and bf16 [T, H]   ·   "
       "HCLazyPostData(R, post, comb, pre or None)   (hc.py:359-364)", 12.5, INK, mono=True)

y = y0b + P2_H + 24
d.legend(30, y, [(TEAL, "post / pre mixing"), (BLUE, "fused DeepGEMM call"), (AMBER, "special start cases"),
                 (VIOLET, "result for the sub-layer")])
y += 40
y = d.footnotes(30, y, [
    "S = split-K count: 16 on CUDA, 1 on Ascend (mhc_ops.py:16-22). fn has 2m + m² rows and m x H columns (mhc_modeling.py:101-102).",
    "Case D: no code in commit 9bd9cf2 makes lazy data with residual None and keeps the layer output 3-D (checked by search).",
])
d.save(height=y + 10)
