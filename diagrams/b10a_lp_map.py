"""Diagram: which number format each tensor of DeepInfer uses (V4.1 checkpoint, default config).

Used by: src/concepts/low-precision-formats.html ("The picture")
Sources (commit 9bd9cf2):
  deepinfer/hugging_face/config.py:253-264, 301-306   fp8 + fp4 experts + [32, 32] + ue8m0 + dynamic; flags
  deepinfer/model_executor/models/v4_modules/containers.py:62-87, 113-135   packed FP4 experts; FP8 meta weights; BF16 skips
  deepinfer/model_executor/models/v4_modules/moe.py:66-67   gate in BF16
  deepinfer/model_executor/layers/linear.py:17-24, 140-166   per-token FP8 cast; fp8_fp4_gemm_nt; BF16 out
  deepinfer/model_executor/models/v4_modules/mlp.py:109-128, 255  grouped FP8 x FP4 expert GEMM; mega-MoE function
  deepinfer/model_executor/layers/sampler_utils.py:20-28    logits: BF16 GEMM, FP32 out
  deepinfer/model_executor/layers/tilelang_ops/cache_common.py:109-137  KV formats
  deepinfer/model_executor/model_metadata_utils.py:37-39    16 values per scale for FP4 main KV, else 32
  deepinfer/model_executor/models/v4_modules/attn.py:412-428   SWA cast: e4m3, ue8m0
  deepinfer/model_executor/models/v4_modules/index_attn.py:85-86   indexer: FP4_INDEX_KV_FORMAT
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import BLUE, EMERALD, MUTE, PINK, Diagram  # noqa: E402

d = Diagram(width=1100)
W = d.W

d.header(
    "Low precision in DeepInfer: one format per tensor",
    "V4.1 checkpoint with the default config  ·  every scale is a power of two (UE8M0) except the FP4 main KV",
    params="E4M3 max 448  ·  E2M1 max 6  ·  UE8M0 = 2^(byte − 127)  ·  block 32 × 32 (weights), 1 × 32 (activations)",
)

y0 = 112
P1 = 486
d.panel(y0, P1, 1, "Which format does each tensor use? Weights, compute, KV cache",
        "Read each column from top to bottom. The colour of a box is its value format.")

colw = 320
xs = [46, 390, 734]
heads = ["Weights (loaded once)", "Activations and GEMMs (every step)", "KV cache (per token)"]
for x, h in zip(xs, heads):
    d.text(x, y0 + 82, h, 13, MUTE, "bold")

GAP = 16


def col(x, items, y):
    for title, lines, c in items:
        h = 38 + 15 * len(lines)
        d.box(x, y, colw, h, title, lines, col=c, align="start")
        y += h + GAP
    return y


yA = y0 + 96
col(xs[0], [
    ("Most linear layers: FP8 E4M3", ["one scale per 32 × 32 block", "attention projections, shared expert", "config.py:254-262"], BLUE),
    ("Routed experts: MXFP4", ["E2M1, two codes per int8 byte", "one UE8M0 scale per 32 values", "int8 [n_local, h_out, h_in / 2]", "containers.py:72-87"], PINK),
    ("BF16 (not quantized)", ["MoE gate (moe.py:66-67)", "compressor A and Gate (mla_attn.py:79-95)", "indexer weights_proj, k_proj", "embedding, head (containers.py:122)"], EMERALD),
], yA)
col(xs[1], [
    ("Input of an FP8 linear", ["BF16 → FP8 E4M3 per token row", "UE8M0 scale per 32 values", "linear.py:17-24, 150"], BLUE),
    ("FP8 GEMM", ["deep_gemm.fp8_fp4_gemm_nt", "recipe (1, 1, 32) · out: BF16", "linear.py:153-165"], BLUE),
    ("Expert GEMM: FP8 × FP4", ["grouped: m_grouped_fp8_fp4_gemm_nt", "  recipe_a (1, 32), recipe_b (1, 32)", "or mega-MoE: fp8_fp4_mega_moe", "mlp.py:118-128, 255"], PINK),
    ("Logits", ["BF16 GEMM with FP32 output", "sampler_utils.py:25-26"], EMERALD),
], yA)
col(xs[2], [
    ("Main (compressed) KV: FP4", ["512 × E2M1 + 32 E4M3 scales", "16 values per scale · 288 B", "cache_common.py:119-128"], PINK),
    ("Main KV option: MXFP8", ["512 × E4M3 + 16 UE8M0 scales", "32 per scale · 528 B", "if use_fp4_sparse_kv = False"], BLUE),
    ("Sliding-window KV: MXFP8", ["same 528 B format as above", "attn.py:412-428"], BLUE),
    ("Indexer keys: MXFP4", ["128 × E2M1 + 4 UE8M0 scales", "32 per scale · 68 B", "index_attn.py:85-86"], PINK),
], yA)

y = y0 + P1 + 22
d.legend(30, y, [(BLUE, "FP8 E4M3 values"), (PINK, "FP4 E2M1 values"), (EMERALD, "BF16 or FP32")])
y += 36
y = d.footnotes(30, y, [
    "The main KV uses MXFP8 when the checkpoint config.json sets use_fp4_sparse_kv to false (config.py:303).",
    "Not shown: Engram tables, the DFlash draft model, the vision encoder, and the mega-MoE weight layout (vendor library).",
])
d.save(height=y + 10)
