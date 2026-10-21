"""Diagram: block scaling (MXFP4 worked example) and the formats that DeepInfer uses for weights, activations and the KV cache.

Used by: src/learn/number-formats.html
Sources (commit 9bd9cf2):
  deepinfer/hugging_face/config.py:253-264                  checkpoint must be fp8 + fp4 experts, block [32, 32], scale ue8m0
  deepinfer/model_executor/models/v4_modules/containers.py:113-135   FP8 weights with square 32x32 scale blocks; heads BF16
  deepinfer/model_executor/layers/linear.py:13-24           activations: per-token e4m3, 32 values per scale, packed ue8m0
  deepinfer/model_executor/models/v4_modules/mlp.py:118-128  expert GEMM: FP8 activations x FP4 weights, 32 values per weight scale
  deepinfer/model_executor/layers/tilelang_ops/cache_common.py:109-137  KV formats (MXFP8 528 B, FP4 288 B, FP4 index keys)
  deepinfer/model_executor/layers/tilelang_ops/cache_common.py:339-345  FP4 KV scale = amax / 6 as E4M3, 16 values
  deepinfer/platform.py:63, 138                             UE8M0 scales packed in int32 (NVIDIA) / int16 (Ascend)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, INK, MUTE, NEUTRAL, VIOLET, WHITE, Diagram  # noqa: E402

d = Diagram(width=1100)
W = d.W
d.header("Block scaling: small numbers with a shared scale",
         "Panel 1: 8 of the 32 values of one MXFP4 block  ·  Panel 2: the formats in DeepInfer (V4.1 checkpoint)",
         params="real value ≈ code × scale        MXFP4: 32 × E2M1 + 1 × UE8M0 = 17 bytes = 4.25 bits per value")

# ============================================================================
# Panel 1: worked MXFP4 block
# ============================================================================
y0 = 112
P1_H = 330
d.panel(y0, P1_H, 1, "How does one block get its scale and codes?",
        "Find the largest magnitude, pick a power-of-two scale so that it fits in E2M1 (max 6), divide, round.")

vals = [0.12, -0.53, 1.70, 0.04, -2.90, 0.88, 0.31, -0.07]
scaled = [0.24, -1.06, 3.4, 0.08, -5.8, 1.76, 0.62, -0.14]
codes = ["0", "-1", "3", "0", "-6", "2", "0.5", "-0"]
deq = ["0", "-0.5", "1.5", "0", "-3.0", "1.0", "0.25", "-0"]
err = ["0.12", "0.03", "0.20", "0.04", "0.10", "0.12", "0.06", "0.07"]
labels = [("x (BF16)", INK, vals), ("x / scale", MUTE, scaled), ("E2M1 value", AMBER[0], codes),
          ("code × scale", BLUE[0], deq), ("|error|", MUTE, err)]
cx0, cw = 200, 96
for j in range(8):
    d.text(cx0 + j * cw + cw / 2, y0 + 82, f"v{j}", 11.5, MUTE, anchor="middle", mono=True)
for i, (lab, col, row) in enumerate(labels):
    ry = y0 + 92 + i * 34
    d.text(46, ry + 20, lab, 13, col if col != MUTE else INK, "bold")
    for j, v in enumerate(row):
        hot = (j == 4)
        fill = AMBER[1] if i == 2 else (BLUE[1] if i == 3 else WHITE)
        stroke = AMBER[0] if i == 2 else (BLUE[0] if i == 3 else NEUTRAL[0])
        d.rect(cx0 + j * cw + 4, ry, cw - 8, 28, fill=fill, stroke=stroke, rx=4, sw=2.2 if hot and i == 0 else 1.1)
        d.text(cx0 + j * cw + cw / 2, ry + 19, f"{v}", 12.5, col, "bold" if i in (2, 3) else "normal", "middle", mono=True)
sy = y0 + 92 + 5 * 34 + 14
d.text(46, sy + 4, "amax = 2.90 (v4)    scale = 2^ceil(log2(2.90 / 6)) = 2^-1 = 0.5    UE8M0 code = -1 + 127 = 126 = 0x7E",
       12.5, VIOLET[0], "bold", mono=True)
d.text(46, sy + 24, "Bytes for 32 values: 32 × 4 bits = 16 B of codes + 1 B scale = 17 B (BF16 would need 64 B).", 12, MUTE)

# ============================================================================
# Panel 2: DeepInfer formats
# ============================================================================
y1 = y0 + P1_H + 20
P2_H = 318
d.panel(y1, P2_H, 2, "Which format does DeepInfer use where?",
        "The checkpoint must be FP8 with FP4 experts. The KV cache has its own formats. Some small parts stay in BF16.")

bw, gap = 330, 13
cards = [
    ("Weights", [
        ("linear layers", ["FP8 E4M3", "UE8M0 scale per 32 × 32 block"]),
        ("routed experts", ["FP4 E2M1 (MXFP4), 2 per byte", "UE8M0 scale per 32 values"]),
        ("gate, embedding, head", ["BF16"]),
    ]),
    ("Activations", [
        ("GEMM input, cast per token", ["FP8 E4M3", "UE8M0 scale per 32 values"]),
        ("GEMM output", ["BF16 (gate: FP32)"]),
        ("scale storage", ["NVIDIA: 4 UE8M0 in one int32", "Ascend: 2 UE8M0 in one int16"]),
    ]),
    ("KV cache (per token, per layer)", [
        ("main cache, default", ["FP4 + E4M3 per 16 = 288 B"]),
        ("main cache, other option", ["MXFP8: 512 + 16 = 528 B"]),
        ("sliding-window cache", ["MXFP8, 528 B"]),
        ("indexer keys", ["FP4 + UE8M0 per 32"]),
    ]),
]
for c, (title, items) in enumerate(cards):
    bx = 46 + c * (bw + gap)
    by = y1 + 70
    d.rect(bx, by, bw, 228, fill=WHITE, stroke=NEUTRAL[0], sw=1.5)
    d.text(bx + 14, by + 24, title, 14, INK, "bold")
    yy = by + 52
    for k, lines in items:
        d.text(bx + 14, yy, k, 12, MUTE, "bold")
        for j, v in enumerate(lines):
            d.text(bx + 14, yy + 17 + j * 16, v, 12.5, INK, mono=True)
        yy += 17 + len(lines) * 16 + 12

y = y1 + P2_H + 24
d.legend(30, y, [(AMBER, "E2M1 values"), (BLUE, "dequantized values"), (VIOLET, "shared scale")])
y += 36
y = d.footnotes(30, y, [
    "Panel 1 uses the common power-of-two rule; DeepInfer passes round_sf=True (linear.py:21); the kernel math is in tile_kernels, not in this repo.",
    "Panel 2 sources: hugging_face/config.py:253-264, 303; containers.py:113-135; linear.py:13-24; cache_common.py:109-137; platform.py:63, 138.",
])
d.save(height=y + 10)
