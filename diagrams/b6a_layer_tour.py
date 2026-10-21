"""Diagram: the ten stops of the tour "Inside one decoder layer", with the shapes at each stop.

Used by: src/tours/decoder-layer.html ("The picture")
Sources (commit 9bd9cf2):
  deepinfer/model_executor/models/deepseek.py:209-218        the loop calls layer i
  deepinfer/model_executor/models/decoder_layer.py:97-175    DeepseekDecoderLayer.forward
  deepinfer/model_executor/models/v4_modules/hc.py:119-364   attn_norm_forward, ffn_norm_forward, post, pre
  deepinfer/model_executor/layers/tilelang_ops/dflash.py:130-155   dflash_input_store: mean over hc_mult
  deepinfer/model_executor/models/v4_modules/attn.py:752-880 V4Attention.forward
  deepinfer/model_executor/models/v4_modules/mlp.py:359-401, 528-616   gate, mega and normal MoE
  deepinfer/model_executor/models/deepseek.py:225-239        fold after the last layer
Example sizes (NOT in the repo): T = 192 tokens (32 sequences x 6 in decode), H = 4096, m = hc_mult = 4, k = top-k.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, INK, MUTE, PINK, TEAL, VIOLET, Diagram  # noqa: E402

d = Diagram(width=1100)
d.header(
    "Inside one decoder layer: ten stops, with shapes",
    "DeepseekDecoderLayer.forward in a decode step  ·  mHC on  ·  example sizes, not from the repo",
    params="T = 192 tokens  ·  H = 4096  ·  m = hc_mult = 4  ·  k = top-k experts  ·  trunk R = [T, m, H]",
)

CW = 1008
CH = 78
GAP = 14


def stops(y, items):
    for i, (num, title, col, tag, rows) in enumerate(items):
        yy = y + i * (CH + GAP)
        d.step_card(46, yy, CW, CH, num, title, col, tag=tag, rows=rows, key_w=48)
        if i < len(items) - 1:
            d.arrow(46 + 60, yy + CH, 46 + 60, yy + CH + GAP - 2, col, sw=1.6)
    return y + len(items) * (CH + GAP) - GAP


# ============================================================================
# Panel 1: into the layer and through attention
# ============================================================================
y0 = 112
items1 = [
    (1, "The layer gets its inputs", INK, "deepseek.py:209-218", [
        ("in", "hidden x [192, 4096] bf16 (MoE out of layer i-1, not yet in the trunk)"),
        ("in", "residual: HCLazyPostData, R [1, 192, 4, 4096]  (layer 0: embedding, None)"),
    ]),
    (2, "Hooks and the YOCO boundary (some layers only)", AMBER, "decoder_layer.py:111-142", [
        ("does", "Engram layers: make a hook that changes the trunk after the post mix"),
        ("does", "first YOCO consumer, compact prefill only: make compact copies of the rows"),
    ]),
    (3, "mHC post of the previous MoE", TEAL, "hc.py:174-224", [
        ("does", "R = mhc_post(x, R_old, post, comb): comb @ R_old + post * x"),
        ("out", "R [192, 4, 4096] bf16; layer 0: R = expand_to_mhc(embedding)"),
    ]),
    (4, "mHC pre and the attention norm", TEAL, "hc.py:317-364", [
        ("out", "x_in [192, 4096] -> RMSNorm -> (fp8 [192, 4096], scales) + bf16 copy"),
        ("out", "new lazy: R, post [1, 192, 4, 1], comb [1, 192, 4, 4], pre or None"),
    ]),
    (5, "DFlash hook and YOCO shared hidden", PINK, "decoder_layer.py:144-152", [
        ("does", "target layers: mean of the 4 streams of R -> dflash_input[:, j*4096:(j+1)*4096]"),
        ("does", "first YOCO consumer: keep a clone of the bf16 norm output as shared hidden"),
    ]),
    (6, "Attention: MLA, SWA and compressed keys, indexer", VIOLET, "attn.py:752-880", [
        ("in", "(fp8, scales) + bf16 [192, 4096], kv_cache of layer i, cross-layer runtime"),
        ("out", "bf16 [192, 4096] after the output projection"),
    ]),
]
n1 = len(items1)
P1_H = 72 + n1 * (CH + GAP) - GAP + 22
d.panel(y0, P1_H, 1, "Into the layer, and through attention",
        "The post mix of the previous MoE runs at the start of this layer, in the same call as the attention pre mix.")
stops(y0 + 72, items1)

# ============================================================================
# Panel 2: the MoE half
# ============================================================================
y0b = y0 + P1_H + 22
items2 = [
    (7, "mHC post of attention, and pre for the MoE", TEAL, "decoder_layer.py:162", [
        ("does", "ffn_norm_forward: same code as stop 3 + 4, with the MoE's cast arguments"),
        ("out", "fp8 input (mega MoE: written into its buffer) + bf16 [192, 4096], new lazy"),
    ]),
    (8, "The gate picks k experts per token", BLUE, "mlp.py:359-401", [
        ("in", "bf16 [192, 4096]"),
        ("out", "topk_idx, topk_weights [192, k]: physical expert slots and weights"),
    ]),
    (9, "Experts: dispatch, routed, shared, combine", BLUE, "mlp.py:528-616", [
        ("does", "mega MoE: one DeepGEMM call  ·  else DeepEP dispatch, 2 grouped GEMMs,"),
        ("does", "shared expert, combine (shared output added as bias)  ->  bf16 [192, 4096]"),
    ]),
    (10, "Out: the layer returns, the MoE post waits", INK, "decoder_layer.py:175", [
        ("out", "(MoE out [192, 4096], lazy residual): post runs in layer i+1, stop 3"),
        ("out", "after the last layer: post + fold (deepseek.py:225-239) -> [192, 4096]"),
    ]),
]
n2 = len(items2)
P2_H = 72 + n2 * (CH + GAP) - GAP + 22
d.panel(y0b, P2_H, 2, "The MoE half, and the way out",
        "The MoE output leaves the layer as a single stream. The trunk gets it only in the next layer.")
stops(y0b + 72, items2)

y = y0b + P2_H + 24
d.legend(30, y, [(TEAL, "mHC mixing + norm"), (VIOLET, "attention"), (BLUE, "MoE"),
                 (PINK, "DFlash / YOCO copy"), (AMBER, "optional hooks")])
y += 40
y = d.footnotes(30, y, [
    "Not shown: timers (decoder_layer.py:120-133, 164-168), CUDA graph capture, context parallelism.",
    "Simplified: 'comb @ R_old + post * x' is a model of the post kernel (not in the repo); it fits flops_estimator.hpp:107-111.",
    "On GPU with m = 4 and H a multiple of 1024, stops 3 and 4 (and 7) are one deep_gemm.mega_mhc call (hc.py:97-101, 195-202).",
])
d.save(height=y + 10)
