"""Diagram: three collectives with small numbers, and DeepInfer's process groups for 8 ranks.

Used by: src/learn/parallelism.html
Example: dp_size=4, cp_size=2, ep_size=8 (the default dp = ep // cp), enp_size default = cp * dp = 8.
Sources (commit 9bd9cf2):
  deepinfer/config.py:161-173                                      dp default, engram default, world size
  deepinfer/worker/base.py:329                                     rank = engine_rank * cp_size + cp_rank
  deepinfer/model_executor/parallel_utils/parallel_state.py:51-68  the group fields (no TP, no PP group)
  deepinfer/model_executor/parallel_utils/parallel_state.py:80-118 group layouts (world, local, dp, cp, ep, enp, ep_in_dp)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, NEUTRAL, SERIES, TEAL, VIOLET, WHITE, Diagram  # noqa: E402

d = Diagram(width=1100)
W = d.W
d.header("Collectives, and the process groups of DeepInfer",
         "Panel 1: 3 ranks, tiny tensors  ·  Panel 2: 8 ranks with dp_size = 4, cp_size = 2, ep_size = 8",
         params="rank = engine_rank × cp_size + cp_rank        engine_rank = DP index 0..3        cp_rank = 0..1")

RK = [SERIES[0], SERIES[1], SERIES[2]]
RT = ["#eff6ff", "#fdf2f8", "#f0fdf4"]


def row(x, y, r, vals, stroke, fill, ink):
    d.text(x, y + 15, f"r{r}", 12, RK[r], "bold", mono=True)
    for i, v in enumerate(vals):
        cx = x + 30 + i * 30
        d.rect(cx, y, 27, 22, fill=fill, stroke=stroke, rx=3, sw=1.1)
        d.text(cx + 13.5, y + 15.5, str(v), 12, ink, "bold", "middle", mono=True)


# ============================================================================
# Panel 1: collectives
# ============================================================================
y0 = 112
P1_H = 362
d.panel(y0, P1_H, 1, "What does each collective do?",
        "All ranks of a group call the same collective. Each rank gives a tensor and gets a tensor back.")

cols = [
    ("all-reduce (sum)", "each rank gets the element-wise sum", [[1, 2], [3, 4], [5, 6]], [[9, 12]] * 3, TEAL),
    ("all-gather", "each rank gets all parts, in rank order", [[1, 2], [3, 4], [5, 6]], [[1, 2, 3, 4, 5, 6]] * 3, TEAL),
    ("all-to-all", "rank j gets part j of every rank", [[1, 2, 3], [4, 5, 6], [7, 8, 9]],
     [[1, 4, 7], [2, 5, 8], [3, 6, 9]], TEAL),
]
bw, gap = 330, 13
for c, (title, sub, before, after, role) in enumerate(cols):
    bx = 46 + c * (bw + gap)
    by = y0 + 70
    d.rect(bx, by, bw, 272, fill=role[1], stroke=role[0], sw=1.4)
    d.text(bx + 14, by + 24, title, 14, role[0], "bold")
    d.text(bx + 14, by + 43, sub, 12, MUTE)
    d.text(bx + 14, by + 70, "before", 11.5, MUTE, "bold", mono=True)
    for r in range(3):
        row(bx + 14, by + 78 + r * 26, r, before[r], RK[r], RT[r], RK[r])
    d.text(bx + 14, by + 172, "after", 11.5, MUTE, "bold", mono=True)
    for r in range(3):
        row(bx + 14, by + 180 + r * 26, r, after[r], role[0], WHITE, INK)

# ============================================================================
# Panel 2: DeepInfer groups
# ============================================================================
y1 = y0 + P1_H + 20
P2_H = 446
d.panel(y1, P2_H, 2, "Which ranks talk to which? DeepInfer's groups for 8 ranks",
        "Each rank holds the full attention weights and 1/8 of the experts. There is no TP group and no PP group.")

n = 8
rw, rg = 110, 15.4
rx0 = 46
ry = y1 + 76
centers = []
for r in range(n):
    x = rx0 + r * (rw + rg)
    eng, cp = divmod(r, 2)
    d.rect(x, ry, rw, 58, fill=NEUTRAL[2], stroke=NEUTRAL[0], sw=1.3)
    d.text(x + rw / 2, ry + 22, f"rank {r}", 13.5, INK, "bold", "middle")
    d.text(x + rw / 2, ry + 43, f"DP {eng} · CP {cp}", 12, MUTE, anchor="middle", mono=True)
    centers.append(x + rw / 2)


def group_line(y, members, col, label, x_label=None):
    xs = [centers[m] for m in members]
    d.line(xs[0] - 30, y, xs[-1] + 30, y, col=col[0], sw=2.2)
    for x in xs:
        d.line(x, y - 9, x, y + 9, col=col[0], sw=2.2)
        d.circle(x, y, 4.5, fill=col[0])
    if label:
        d.text(x_label if x_label is not None else xs[0] - 30, y - 14, label, 12, col[0], "bold")


gy = ry + 100
# CP pairs
for e in range(4):
    group_line(gy, [2 * e, 2 * e + 1], VIOLET, f"CP group {e}")
gy += 62
group_line(gy, [0, 2, 4, 6], BLUE, "DP group A: ranks 0, 2, 4, 6 (cp_rank 0)")
gy += 54
group_line(gy, [1, 3, 5, 7], BLUE, "DP group B: ranks 1, 3, 5, 7 (cp_rank 1)")
gy += 54
group_line(gy, list(range(8)), AMBER, "EP group = world: all 8 ranks (ep_size = 8 = number of ranks)")
gy += 54
group_line(gy, list(range(8)), EMERALD, "Engram group: all 8 ranks (enp_size default = cp × dp = 8)")

y = y1 + P2_H + 24
d.legend(30, y, [(TEAL, "collective (panel 1)"), (VIOLET, "CP group"), (BLUE, "DP group"),
                 (AMBER, "EP group"), (EMERALD, "Engram group")])
y += 36
y = d.footnotes(30, y, [
    "Not shown: the world group, one 'local' group per rank, the EP-in-DP group, CPU (gloo) copies of the DP, CP and EP-in-DP groups.",
    "Layouts from parallel_state.py:92 (DP), 97 (CP), 102-106 (EP), 109 (Engram). With ep_size = 4, the EP groups are 0-3 and 4-7.",
])
d.save(height=y + 10)
