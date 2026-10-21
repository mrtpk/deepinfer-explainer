"""Diagram: GPU memory hierarchy, the roofline model, and why CUDA graphs cut launch cost.

Used by: src/learn/gpus-kernels.html
Generic GPU numbers are rounded and illustrative (recent NVIDIA data-center GPUs).
Sources for the DeepInfer numbers (commit 9bd9cf2):
  deep_cluster/hardware/device.py:151-156   BF16 TFLOP/s limit: 2250 (SM100, x86) / 2500 (SM100, arm) / 432 (Ascend)
  deepinfer/worker/cuda_graph_runner.py:150-154  replay(): one graph.replay() call
  deepinfer/worker/model_runner.py:182          graphs only for decode steps
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, LINE, MUTE, NEUTRAL, PINK, TEAL, VIOLET, WHITE, Diagram  # noqa: E402

d = Diagram(width=1100)
W = d.W
d.header("Where a GPU spends its time: memory, math and launches",
         "One device  ·  rounded, illustrative numbers for a recent NVIDIA data-center GPU  ·  peak BF16 from deep_cluster",
         params="peak BF16 = 2,250 TFLOP/s (device.py:155)     HBM bandwidth = 8 TB/s (illustrative)     ridge = 2,250 / 8 ≈ 281 FLOP/byte")

# ============================================================================
# Panel 1: memory hierarchy
# ============================================================================
y0 = 112
P1_H = 268
d.panel(y0, P1_H, 1, "Where does the data live?",
        "Large memory is far and slow. Small memory is near the math units and fast. Kernels move data inward, compute, and write back.")

by = y0 + 76
bh = 160
# HBM
d.box(46, by, 270, bh, "HBM (device memory)", [
    "80-192 GB per device",
    "3-8 TB/s",
    "",
    "weights, KV cache,",
    "activations",
], col=BLUE, mono_size=12.5)
# L2
d.box(390, by + 30, 200, 100, "L2 cache", ["tens of MB", "shared by all SMs"], col=VIOLET, mono_size=12.5)
# SM
sx, sw = 664, W - 46 - 664
d.rect(sx, by, sw, bh, fill=TEAL[1], stroke=TEAL[0], sw=1.5)
d.text(sx + sw / 2, by + 20, "One SM (more than 100 per device)", 13.5, TEAL[0], "bold", "middle")
inner = [("shared memory (SMEM)", "up to ~228 KiB"), ("registers", "256 KiB per SM"),
         ("Tensor Cores", "matrix tiles: BF16/FP8/FP4")]
for i, (t, v) in enumerate(inner):
    iy = by + 36 + i * 40
    d.rect(sx + 14, iy, sw - 28, 34, fill=WHITE, stroke=TEAL[0], rx=6, sw=1.1)
    d.text(sx + 26, iy + 22, t, 13, INK, "bold")
    d.text(sx + sw - 26, iy + 22, v, 12, INK, anchor="end", mono=True)
# arrows
d.arrow(316, by + 80, 388, by + 80, BLUE, sw=2)
d.arrow(590, by + 80, 662, by + 80, VIOLET, sw=2)
d.arrow_label(352, by + 80, "load", BLUE)
d.arrow_label(626, by + 80, "load", VIOLET)

# ============================================================================
# Panel 2: roofline
# ============================================================================
y1 = y0 + P1_H + 20
P2_H = 400
d.panel(y1, P2_H, 2, "Memory-bound or compute-bound? The roofline answers",
        "Speed = min(peak FLOP/s, bandwidth × FLOP per byte). Left of the ridge, more batch is almost free.")

# plot area
px0, py0 = 140, y1 + 90
pw, ph = 600, 250
x_lo, x_hi = 0, 12      # log2 FLOP/byte: 1 .. 4096
y_lo, y_hi = 2, 12      # log2 TFLOP/s: 4 .. 4096
PEAK, BW = 2250.0, 8.0


def X(i):
    return px0 + (math.log2(i) - x_lo) / (x_hi - x_lo) * pw


def Y(t):
    return py0 + ph - (math.log2(t) - y_lo) / (y_hi - y_lo) * ph


d.rect(px0, py0, pw, ph, fill=WHITE, stroke=LINE, rx=0, sw=1)
for e in range(x_lo, x_hi + 1, 2):
    xx = X(2 ** e)
    d.line(xx, py0, xx, py0 + ph, col="#eef0f3", sw=1)
    d.text(xx, py0 + ph + 18, f"{2 ** e:,}", 11, MUTE, anchor="middle", mono=True)
for e in range(y_lo, y_hi + 1, 2):
    yy = Y(2 ** e)
    d.line(px0, yy, px0 + pw, yy, col="#eef0f3", sw=1)
    d.text(px0 - 8, yy + 4, f"{2 ** e:,}", 11, MUTE, anchor="end", mono=True)
d.text(px0 + pw / 2, py0 + ph + 40, "arithmetic intensity (FLOP per byte, log scale)", 12, MUTE, anchor="middle")
d.text(px0 - 94, py0 - 10, "TFLOP/s (log)", 12, MUTE)

ridge = PEAK / BW
# memory slope from x=1 to ridge
d.line(X(1), Y(BW * 1), X(ridge), Y(PEAK), col=BLUE[0], sw=2.4)
d.line(X(ridge), Y(PEAK), X(4096), Y(PEAK), col=AMBER[0], sw=2.4)
d.line(X(ridge), Y(PEAK), X(ridge), py0 + ph, col=MUTE, sw=1, dash="3 3")
d.text(X(ridge) + 6, py0 + ph - 8, "ridge ≈ 281", 11.5, MUTE, mono=True)
d.text(X(12), Y(BW * 12) + 30, "8 TB/s × intensity", 12, BLUE[0], "bold")
d.text(X(4096) - 4, Y(PEAK) - 10, "2,250 TFLOP/s", 12, AMBER[0], "bold", anchor="end")

pts = [
    (1.0, "decode GEMM, 1 token", PINK[0], 10, 20),
    (64.0, "decode GEMM, 64 tokens", PINK[0], 10, 22),
    (409.0, "GEMM, 512 tokens", EMERALD[0], 10, 26),
    (1365.0, "prefill GEMM, 4,096 tokens", EMERALD[0], 10, 46),
]
for i_, label, col, dx, dy in pts:
    perf = min(PEAK, BW * i_)
    cx, cy = X(i_), Y(perf)
    d.circle(cx, cy, 6, fill=col, stroke=WHITE, sw=1.5)
    d.text(cx + dx, cy + dy, label, 12, col, "bold")

# side notes
nx = 770
notes = [
    ("Worked example: W = [4096, 4096] BF16", INK, True),
    ("FLOPs  = 2·M·4096·4096", INK, False),
    ("bytes ≈ 2·4096² + 4·M·4096", INK, False),
    ("intensity ≈ M for small M", INK, False),
    ("", INK, False),
    ("M = 1:    4.2 µs (memory)", PINK[0], False),
    ("M = 64:   4.3 µs (memory)", PINK[0], False),
    ("M = 512:  7.6 µs (math)", EMERALD[0], False),
]
for i, (s, col, bold) in enumerate(notes):
    d.text(nx, py0 + 104 + i * 20, s, 12.5 if bold else 12, col, "bold" if bold else "normal", mono=not bold)

# ============================================================================
# Panel 3: launches vs CUDA graph
# ============================================================================
y2 = y1 + P2_H + 20
P3_H = 262
d.panel(y2, P3_H, 3, "Why launch overhead matters, and what a CUDA graph changes",
        "Small decode kernels finish faster than the CPU can launch them. A graph replays all launches with one call.")

lx0 = 150
unit = 26


def lane_label(y, s):
    d.text(46, y + 17, s, 12.5, INK, "bold")


# eager
ey = y2 + 84
d.text(46, ey - 10, "Eager: one launch per kernel", 13.5, INK, "bold")
lane_label(ey + 4, "CPU")
lane_label(ey + 40, "GPU")
for k in range(9):
    cx = lx0 + k * (unit * 3)
    d.rect(cx, ey + 4, unit * 2.6, 24, fill=VIOLET[1], stroke=VIOLET[0], rx=3, sw=1.1)
    d.text(cx + unit * 1.3, ey + 20, "launch", 11, VIOLET[0], "bold", "middle")
    gx = cx + unit * 2.6 + 4
    d.rect(gx, ey + 40, unit * 0.9, 24, fill=TEAL[1], stroke=TEAL[0], rx=3, sw=1.1)
d.text(lx0 + 9 * unit * 3 + 24, ey + 56, "GPU idle between kernels", 11.5, MUTE, italic=True)

# graph
gy = ey + 108
d.text(46, gy - 10, "CUDA graph: one replay() call", 13.5, TEAL[0], "bold")
lane_label(gy + 4, "CPU")
lane_label(gy + 40, "GPU")
d.rect(lx0, gy + 4, unit * 2.6, 24, fill=VIOLET[1], stroke=VIOLET[0], rx=3, sw=1.1)
d.text(lx0 + unit * 1.3, gy + 20, "replay", 11, VIOLET[0], "bold", "middle")
d.text(lx0 + unit * 2.6 + 12, gy + 21, "CPU is free for the next step", 11.5, MUTE, italic=True)
for k in range(9):
    gx = lx0 + unit * 2.6 + 4 + k * (unit * 0.9 + 3)
    d.rect(gx, gy + 40, unit * 0.9, 24, fill=TEAL[1], stroke=TEAL[0], rx=3, sw=1.1)

y = y2 + P3_H + 24
d.legend(30, y, [(BLUE, "memory traffic"), (AMBER, "math limit"), (PINK, "decode (memory-bound)"),
                 (EMERALD, "compute-bound"), (VIOLET, "CPU work"), (TEAL, "GPU kernel")])
y += 36
y = d.footnotes(30, y, [
    "Simplified: one GEMM only. Real steps also run attention, norms and communication. Times assume perfect overlap and full peak.",
    "Panel 3 is a sketch, not to scale. DeepInfer replays graphs only in decode steps (model_runner.py:182).",
])
d.save(height=y + 10)
