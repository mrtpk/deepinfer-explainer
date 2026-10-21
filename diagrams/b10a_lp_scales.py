"""Diagram: how DeepInfer makes, packs and loads UE8M0 scales.

Used by: src/concepts/low-precision-formats.html ("In the code")
Sources (commit 9bd9cf2):
  deepinfer/model_executor/layers/tilelang_ops/cuda/store_kv_cache.py:9-16   scale = max(amax, 1e-4) / 448; exp; byte
  deepinfer/model_executor/layers/tilelang_ops/cuda/quant.py:4-9              ceil(log2) with a bit trick
  deepinfer/model_executor/layers/tilelang_ops/common.py:23-27                margins and maxima
  deepinfer/platform.py:63, 138                                                int32 on GPU, int16 on Ascend
  deepinfer/model_executor/models/v4_modules/containers.py:78-87             sf_pack_granularity = 32 * itemsize; column-major sf
  deepinfer/hugging_face/weights.py:163-167, 315-323, 418-427                 F8_E8M0 -> fp32; expert bytes viewed as int32/int16
  deepinfer/model_executor/layers/linear.py:67-76                             FP32 sf -> transform_sf_into_required_layout
Panel 1 values: example block, computed with assets/viz/number_format.js (same rule).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, PINK, VIOLET, Diagram  # noqa: E402

d = Diagram(width=1100)
W = d.W

d.header(
    "UE8M0 scales: make, pack, load",
    "A scale is one byte: a power of two  ·  kernels pack 4 bytes per int32 on NVIDIA, 2 per int16 on Ascend",
    params="byte = ceil(log2(amax / max)) + 127  ·  amax floor: 1e-4 (FP8), 6 · 2^-126 (FP4)  ·  example: MXFP8 block",
)

# ---------------------------------------------------------------- panel 1
y0 = 112
P1 = 208
d.panel(y0, P1, 1, "How is the scale chosen? Round amax / 448 up to a power of two",
        "Rounding up keeps the largest value at or below the format maximum, so nothing overflows.")

bw, bh = 300, 104
by = y0 + 72
d.box(46, by, bw, bh, "1  amax of the block", [
    "block: 3.1, 0.05, −1.2, 0.7 …", "amax = 3.1", "r = 3.1 / 448 = 0.006920", "store_kv_cache.py:13"], col=BLUE)
d.box(400, by, bw, bh, "2  power of two", [
    "log2(0.006920) = −7.18", "ceil → −7", "scale = 2^−7 = 0.0078125", "byte = −7 + 127 = 120 (0x78)"], col=AMBER)
d.box(754, by, bw, bh, "3  codes = x × 2^7", [
    " 3.1  → 396.8 → 384  → 3.0", " 0.05 → 6.4   → 6.5  → 0.0508", "−1.2  → −153.6 → −160 → −1.25", " 0.7  → 89.6  → 88   → 0.6875"], col=PINK, align="start")
d.arrow(46 + bw, by + bh / 2, 398, by + bh / 2, BLUE)
d.arrow(400 + bw, by + bh / 2, 752, by + bh / 2, AMBER)

# ---------------------------------------------------------------- panel 2
y1 = y0 + P1 + 20
P2 = 220
d.panel(y1, P2, 2, "How are scale bytes packed? By the platform scale dtype",
        "PLATFORM.fp8_sf_type is int32 on NVIDIA and int16 on Ascend. GEMMs assert it for both inputs.")


def bytes_row(x, y, labels, col, cell=58):
    for i, lab in enumerate(labels):
        d.rect(x + i * (cell + 4), y, cell, 30, fill=col[1], stroke=col[0], rx=4, sw=1.3)
        d.text(x + i * (cell + 4) + cell / 2, y + 20, lab, 12, col[0], "bold", "middle", mono=True)
    return x + len(labels) * (cell + 4)


ry = y1 + 84
d.text(46, ry - 10, "NVIDIA: one int32 = 4 scale bytes (platform.py:63)", 12.5, INK, "bold")
xe = bytes_row(46, ry, ["g0", "g1", "g2", "g3"], VIOLET)
d.text(xe + 10, ry + 20, "→ 4 groups of 32 values = 128 values of K", 12, INK, mono=True)
ry2 = ry + 76
d.text(46, ry2 - 10, "Ascend: one int16 = 2 scale bytes (platform.py:138)", 12.5, INK, "bold")
xe2 = bytes_row(46, ry2, ["g0", "g1"], EMERALD)
d.text(xe2 + 10, ry2 + 20, "→ 2 groups of 32 values = 64 values of K", 12, INK, mono=True)
d.text(640, ry + 52, "Expert scales: sf_pack_granularity = 32 × itemsize", 12, MUTE, italic=True)
d.text(640, ry + 70, "= 128 (int32) or 64 (int16) values (containers.py:80)", 12, MUTE, italic=True)

# ---------------------------------------------------------------- panel 3
y2 = y1 + P2 + 20
P3 = 206
d.panel(y2, P3, 3, "What happens to checkpoint scales at load time? Two paths",
        "Both start from F8_E8M0 bytes in safetensors. The loader keeps every scale value (weights.py:13-16, 286-288).")

bh3 = 104
by3 = y2 + 72
d.box(46, by3, bw, bh3, "FP8 linear weights", [
    "F8_E8M0 → FP32: 2^(byte − 127)", "param.sf = FP32 [N/32, K/32]", "weights.py:163-167, 418-420"], col=BLUE)
d.box(400, by3, bw, bh3, "at layer build", [
    "sf dtype FP32 ≠ int32/int16", "→ transform_sf_into_", "   required_layout(1, 32, 32)", "linear.py:67-76"], col=BLUE)
d.box(754, by3, bw, bh3, "MXFP4 routed experts", [
    "HF bytes, row-major [h_out, h_in/32]", "view(int32 or int16)", "copy into column-major sf", "weights.py:315-323"], col=PINK)
d.arrow(46 + bw, by3 + bh3 / 2, 398, by3 + bh3 / 2, BLUE)

y = y2 + P3 + 22
d.legend(30, y, [(BLUE, "FP8 path"), (AMBER, "scale exponent"), (PINK, "FP4 / codes"), (VIOLET, "NVIDIA packing"),
                 (EMERALD, "Ascend packing")])
y += 36
y = d.footnotes(30, y, [
    "The byte order inside one int32 and the TMA-aligned layout are chosen by the GEMM libraries (not in this repository).",
    "Panel 1 uses the FP8 rule of store_kv_cache.py. The FP4 rule is the same with 6 instead of 448 (fused_transform.py:514-520).",
])
d.save(height=y + 10)
