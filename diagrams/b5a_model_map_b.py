"""Diagram: inside one decoder layer, and which v4_modules file owns which part.

Used by: src/concepts/model-map.html ("In the code")
Sources (commit 9bd9cf2):
  deepinfer/model_executor/models/decoder_layer.py:111-118   Engram as hc_post_intervention
  deepinfer/model_executor/models/decoder_layer.py:143       attn_norm_forward (mHC post of previous sub-layer + pre)
  deepinfer/model_executor/models/decoder_layer.py:155-161   self_attn (V4Attention)
  deepinfer/model_executor/models/decoder_layer.py:162       ffn_norm_forward
  deepinfer/model_executor/models/decoder_layer.py:169-175   mlp (DeepseekMoE), returns (hidden, residual)
  deepinfer/model_executor/models/decoder_layer.py:43-44     attention / FFN norms with FP8 output
  deepinfer/model_executor/models/v4_modules/hc.py:57-70     HCLayerMixin: pre/post pair, lazy post data
  deepinfer/model_executor/models/v4_modules/__init__.py:6-20   the four file roles
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, INK, MUTE, TEAL, VIOLET, Diagram  # noqa: E402

RET = (INK, "#f9fafb", None)
FILE = ("#374151", "#ffffff", None)

d = Diagram(width=1100)
d.header(
    "Inside one decoder layer, and where each part lives",
    "DeepseekDecoderLayer.forward (decoder_layer.py:97-175)  ·  mHC on (hc_enabled)  ·  commit 9bd9cf2",
    params="in: hidden [T, hidden] + residual (HCLazyPostData)    out: hidden [T, hidden] + residual",
)

TS, MS = 14, 12.5


def card(x, y, w, h, title, lines, col, sub=None, mono_title=False):
    d.rect(x, y, w, h, fill=col[1], stroke=col, sw=1.5)
    d.text(x + 14, y + 24, title, TS, col[0], "bold", mono=mono_title)
    yy = y + 24
    if sub:
        d.text(x + 14, y + 43, sub, 12, MUTE)
        yy = y + 43
    for i, s in enumerate(lines):
        d.text(x + 14, yy + 21 + i * 18, s, MS, INK, mono=True)


# ============================================================================
# Panel 1: the layer
# ============================================================================
y0 = 112
P1_H = 452
d.panel(y0, P1_H, 1, "What does one decoder layer do?",
        "Two sub-layers: attention, then MoE. mHC mixes the residual trunk before and after each sub-layer.")

bw, bh, gx = 306, 140, 45
xs = [46, 46 + bw + gx, 46 + 2 * (bw + gx)]
r1 = y0 + 76
card(xs[0], r1, bw, bh, "1  mHC + attention norm", [
    "post of the previous sub-layer",
    "pre: mix hc paths → 1 input",
    "RMSNorm → FP8 + bf16 copy",
], TEAL, sub="attn_norm_forward  ·  :143")
card(xs[1], r1, bw, bh, "2  Attention", [
    "V4Attention",
    "SWA KV + compressed KV",
    "+ indexer (sparse layers)",
], VIOLET, sub="self_attn(...)  ·  :155-161")
card(xs[2], r1, bw, bh, "3  mHC + FFN norm", [
    "post: write attention out",
    "pre: mix hc paths → 1 input",
    "RMSNorm → FP8 + bf16 copy",
], TEAL, sub="ffn_norm_forward  ·  :162")
cy = r1 + bh / 2
d.arrow(xs[0] + bw, cy, xs[1] - 2, cy, INK, sw=2)
d.arrow(xs[1] + bw, cy, xs[2] - 2, cy, INK, sw=2)

r2 = r1 + bh + 56
card(xs[2], r2, bw, bh, "4  MoE", [
    "DeepseekMoE (mlp.py)",
    "router + routed experts",
    "+ shared expert",
], BLUE, sub="self.mlp(...)  ·  :169-173")
card(xs[1], r2, bw, bh, "5  Return", [
    "hidden [T, hidden]",
    "residual: HCLazyPostData",
    "post runs in the next layer",
], RET, sub="return  ·  :175")
card(xs[0], r2, bw, bh, "Engram (some layers)", [
    "hook inside step 1:",
    "changes the trunk after",
    "the post mix",
], AMBER, sub="hc_post_intervention  ·  :111-118")
d.arrow(xs[2] + bw / 2, r1 + bh, xs[2] + bw / 2, r2 - 2, INK, sw=2)
d.arrow(xs[2], r2 + bh / 2, xs[1] + bw + 2, r2 + bh / 2, INK, sw=2)
d.arrow(xs[0] + bw / 2, r2, xs[0] + bw / 2, r1 + bh + 2, AMBER, dash="5 4")
d.text(46, r2 + bh + 30,
       "The next layer starts with step 1, so the post mix of step 4 and the pre mix of the next attention run in one fused call.",
       12, MUTE, italic=True)

# ============================================================================
# Panel 2: file roles
# ============================================================================
y0b = y0 + P1_H + 22
P2_H = 394
d.panel(y0b, P2_H, 2, "Which file owns which part?",
        "v4_modules/__init__.py sorts the files into four roles. Containers hold weights; runtime files own the forward.")

rw, rh = 489, 124
rx = [46, 46 + rw + 30]
ry = [y0b + 72, y0b + 72 + rh + 22]
card(rx[0], ry[0], rw, rh, "1  Parameter containers (no forward)", [
    "containers.py  linear.py  norm.py  rope.py",
    "mla_attn.py  moe.py  hc_blocks.py",
    "engram_parameters.py  heads.py",
    "HF names, shapes and dtypes",
], FILE)
card(rx[1], ry[0], rw, rh, "2  Runtime adapters and forward", [
    "attn.py  compress.py  index_attn.py",
    "mlp.py  hc.py  engram.py  utils.py",
    "convert a container to the runtime",
    "layout and own the computation",
], FILE)
card(rx[0], ry[1], rw, rh, "3  Tensor operators", [
    "mhc_ops.py  mhc_modeling.py  yoco.py",
    "hc_lazy.py (shared data type)",
    "no parameters, no forward",
], FILE)
card(rx[1], ry[1], rw, rh, "4  Topology and assembly", [
    "cross_layer.py  engram_metadata.py",
    "builder.py",
    "derive and check structure from",
    "the config, build the parameter tree",
], FILE)
d.text(46, ry[1] + rh + 32,
       "Above v4_modules/: deepseek.py (whole model), decoder_layer.py (one layer), deepseek_vl.py (VL), mtp/dflash.py (draft head).",
       12, MUTE, italic=True)

y = y0b + P2_H + 24
d.legend(30, y, [(TEAL, "mHC + norm"), (VIOLET, "attention"), (BLUE, "MoE"), (AMBER, "Engram"),
                 (RET, "layer output")], title="Legend (panel 1)")
y += 40
y = d.footnotes(30, y, [
    "Simplified: with hc_shifted, each pre mix uses the mix of the sub-layer before it (hc.py:64-67). The YOCO boundary,",
    "  the DFlash feature copy and the timers in DeepseekDecoderLayer.forward are not shown.",
])
d.save(height=y + 10)
