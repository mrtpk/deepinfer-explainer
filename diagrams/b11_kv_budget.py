"""Diagram: how start-up sizes the KV cache (memory budget of one rank, then the mean over ranks).

Used by: src/tours/startup.html (stop 11)
Sources (commit 9bd9cf2):
  deepinfer/worker/base.py:217-246    budget = total * gpu_memory_utilization - peak - 2 * state; blocks = budget // block row
  deepinfer/worker/base.py:264-267    all-reduce SUM over the world group, // world size, // 2 * 2
  deepinfer/engine/llm_engine.py:437-451   check: runtime_max_model_len <= int(128 * blocks * 0.8)
  deepinfer/worker/cache_engine.py:918-966  gpu_blocks [blocks, bytes_per_block], gpu_states [slots, bytes_per_slot]
Example values (not measured, same as code/worker-base): 80 GiB device, utilization 0.85, peak 50 GiB,
block row 2 MiB, state buffer 0.5 GiB, 8 ranks.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, NEUTRAL, VIOLET, WHITE, Diagram  # noqa: E402

d = Diagram(width=1100)
d.header(
    "Sizing the KV cache at start-up",
    "One rank measures its free memory, then all ranks take the mean  ·  example values, not measured",
    params="device 80 GiB   gpu_memory_utilization 0.85   peak 50 GiB   block row 2 MiB   state 0.5 GiB   8 ranks",
)

# ---------------------------------------------------------------------------
# Panel 1: the budget bar of one rank
# ---------------------------------------------------------------------------
y0 = 112
P1_H = 268
d.panel(y0, P1_H, 1, "How many blocks fit on one rank?",
        "Budget = 80 x 0.85 - 50 - 2 x 0.5 = 17 GiB.  17 GiB // 2 MiB = 8,704 blocks.")
X0, X1 = 46, 1054
scale = (X1 - X0) / 80.0
by = y0 + 100
BH = 46
segs = [
    (0, 50, VIOLET, "peak of the profile run: 50 GiB"),
    (50, 51, AMBER, "2 x state"),
    (51, 68, EMERALD, "KV blocks: 17 GiB"),
    (68, 80, NEUTRAL, "unused: 12 GiB"),
]
for a, b, col, label in segs:
    x = X0 + a * scale
    w = (b - a) * scale
    d.rect(x, by, w, BH, fill=col[1], stroke=col[0], rx=3, sw=1.3)
    if b - a >= 10:
        d.text(x + w / 2, by + BH / 2 + 4.5, label, 13, INK, "bold", "middle")
# small segment label above
xs = X0 + 50.5 * scale
d.line(xs, by - 4, xs, by - 16, AMBER[0], 1.2)
d.text(xs, by - 22, "2 x state = 1 GiB (store + copy buffer)", 12, AMBER[0], "bold", "middle")
# ticks
for v in (0, 50, 68, 80):
    x = X0 + v * scale
    d.line(x, by + BH, x, by + BH + 8, MUTE, 1)
    d.text(x, by + BH + 22, f"{v} GiB", 11.5, MUTE, anchor="middle" if 0 < v < 80 else ("start" if v == 0 else "end"), mono=True)
xu = X0 + 68 * scale
d.text(xu, by + BH + 38, "80 x 0.85 = 68 GiB", 11.5, MUTE, anchor="middle", mono=True)
ly = by + BH + 62
rows = [
    ("peak   = max_memory_allocated (profile run) + non-torch memory", "base.py:228-234"),
    ("budget = total * gpu_memory_utilization - peak - 2 * state_size", "base.py:235-244"),
    ("blocks = max(int(budget // bytes_per_block), 0)", "base.py:245-246"),
]
lines = [a.ljust(66) + b for a, b in rows]
for i, s in enumerate(lines):
    d.text(X0, ly + i * 17, s, 12, INK, mono=True)

# ---------------------------------------------------------------------------
# Panel 2: the mean over ranks
# ---------------------------------------------------------------------------
y1 = y0 + P1_H + 20
P2_H = 222
d.panel(y1, P2_H, 2, "Which value do all ranks use?",
        "The mean over all ranks, rounded down to an even number. Not the minimum.")
cy = y1 + 72
bw, bh = 310, 104
d.box(46, cy, bw, bh, "each rank measures", [
    "8,704  8,704  8,704  8,704",
    "8,600  8,600  8,600  8,601",
    "",
    "minimum: 8,600",
], col=BLUE, mono_size=12)
d.box(395, cy, bw, bh, "all_reduce(SUM, world)", [
    "sum      = 69,217",
    "// 8     = 8,652",
    "// 2 * 2 = 8,652",
    "every rank: 8,652 blocks",
], col=EMERALD, mono_size=12)
d.box(744, cy, bw, bh, "engine check", [
    "int(128 * 8,652 * 0.8)",
    "  = 885,964 tokens",
    ">= runtime_max_model_len 32,784",
    "-> OK, else ValueError",
], col=VIOLET, mono_size=12)
ay = cy + bh / 2
d.arrow(46 + bw, ay, 393, ay, BLUE)
d.arrow(395 + bw, ay, 742, ay, EMERALD)
d.text(46, cy + bh + 26, "Ranks that measured 8,600 get 52 blocks more than they measured.", 12.5, MUTE, italic=True)

y = y1 + P2_H + 22
d.legend(30, y, [(VIOLET, "model and activations"), (AMBER, "state slots"), (EMERALD, "KV blocks"),
                 (BLUE, "per-rank measurement")])
y += 38
y = d.footnotes(30, y, [
    "All GiB values are invented for the example. The real peak depends on the checkpoint and on the profile batch.",
    "The docstring of _init_cache says 'minimum' (llm_engine.py:426-428); the code takes the mean (base.py:264-266).",
])
d.save(height=y + 10)
