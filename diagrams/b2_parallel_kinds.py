"""Diagram: five ways to split model work over devices, and which ones DeepInfer uses.

Used by: src/learn/parallelism.html
Toy example: 2 devices, a 4-layer model, 8 experts.
Sources (commit 9bd9cf2):
  deepinfer/model_executor/parallel_utils/parallel_state.py:51-68  groups: dp, cp, ep, ep_in_dp, enp, world, local (no TP, no PP)
  deepinfer/model_executor/layers/linear.py:36-45                  only a ReplicatedLinear layer, no column/row-parallel linear
  deepinfer/config.py:171                                          model_parallel_size = context_parallel_size
  README.md:12                                                     "Attention DP / balanced CP, MoE EP + EPLB"
  doc/inference_deployment_qa.md:53                                "TP and CP are not used for now" (in production)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, NEUTRAL, PINK, VIOLET, WHITE, Diagram, text_width  # noqa: E402

d = Diagram(width=1100)
W = d.W
d.header("Five ways to split the work, and the three that DeepInfer uses",
         "Toy example: 2 devices (dev 0, dev 1)  ·  a 4-layer model  ·  8 experts per MoE layer",
         params="DeepInfer groups: dp, cp, ep (+ engram)      no tensor-parallel group      no pipeline-parallel group")

BW, GAP = 330, 13
USED, NOT = EMERALD, PINK


def card(col_i, y, h, title, what, comm, used):
    x = 46 + col_i * (BW + GAP)
    role = USED if used else NOT
    d.rect(x, y, BW, h, fill=WHITE, stroke=role[0], sw=1.6, dash=None if used else "5 4")
    d.text(x + 14, y + 24, title, 14.5, INK, "bold")
    tag = "DeepInfer: yes" if used else "DeepInfer: no"
    tw = text_width(tag, 11, mono=True) + 20
    d.pill(x + BW - tw - 10, y + 10, tw, tag, role[0])
    d.text(x + 14, y + 44, what, 12, MUTE)
    d.text(x + 14, y + h - 14, comm, 12, INK, "bold", mono=True)
    return x


def dev(x, y, w, h, label):
    d.rect(x, y, w, h, fill=NEUTRAL[2], stroke=NEUTRAL[0], rx=6, sw=1.2)
    d.text(x + 8, y + 16, label, 11.5, MUTE, "bold", mono=True)


def blk(x, y, w, s, col, h=22):
    d.rect(x, y, w, h, fill=col[1], stroke=col[0], rx=3, sw=1.2)
    d.text(x + w / 2, y + h / 2 + 4.3, s, 11.5, col[0], "bold", "middle", mono=True)


# ============================================================================
# Panel 1: DP, TP, PP
# ============================================================================
y0 = 112
P1_H = 300
d.panel(y0, P1_H, 1, "Split the requests, the matrices, or the layers?",
        "Data parallel copies the model. Tensor parallel splits each matrix. Pipeline parallel splits the layer list.")
cy, ch = y0 + 70, 212

# DP
x = card(0, cy, ch, "Data parallel (DP)", "each device: full model, own requests", "no talk in the forward pass", True)
for i, (lab, reqs) in enumerate([("dev 0", "R1 R2"), ("dev 1", "R3 R4")]):
    dx = x + 14 + i * 152
    dev(dx, cy + 58, 140, 116, lab)
    for l in range(4):
        blk(dx + 10, cy + 82 + l * 22, 64, f"L{l + 1}", BLUE, h=19)
    d.text(dx + 84, cy + 112, reqs, 12, INK, "bold", mono=True)

# TP
x = card(1, cy, ch, "Tensor parallel (TP)", "each device: half of every weight matrix", "all-reduce in every layer", False)
for i, lab in enumerate(["dev 0", "dev 1"]):
    dx = x + 14 + i * 152
    dev(dx, cy + 58, 140, 116, lab)
    for l in range(4):
        blk(dx + 10, cy + 82 + l * 22, 120, f"L{l + 1}  cols {'0..n/2' if i == 0 else 'n/2..n'}", BLUE, h=19)

# PP
x = card(2, cy, ch, "Pipeline parallel (PP)", "each device: some layers (a stage)", "send activations to next stage", False)
for i, lab in enumerate(["dev 0", "dev 1"]):
    dx = x + 14 + i * 152
    dev(dx, cy + 58, 140, 116, lab)
    for l in range(2):
        blk(dx + 10, cy + 82 + l * 22, 64, f"L{2 * i + l + 1}", BLUE, h=19)
d.arrow(x + 14 + 140 + 1, cy + 116, x + 14 + 152 - 2, cy + 116, INK)

# ============================================================================
# Panel 2: CP, EP
# ============================================================================
y1 = y0 + P1_H + 20
P2_H = 300
d.panel(y1, P2_H, 2, "Split the tokens of one prompt, or the experts?",
        "Context parallel shares one long prefill. Expert parallel puts different experts on different devices.")
cy, ch = y1 + 70, 212

# CP
x = card(0, cy, ch, "Context parallel (CP)", "each device: part of the tokens of one prompt", "all-gather of keys and values", True)
for i, lab in enumerate(["dev 0", "dev 1"]):
    dx = x + 14 + i * 152
    dev(dx, cy + 58, 140, 116, lab)
    toks = ["t0-1", "t6-7"] if i == 0 else ["t2-3", "t4-5"]
    for k, t in enumerate(toks):
        blk(dx + 10, cy + 84 + k * 30, 76, t, VIOLET)

# EP
x = card(1, cy, ch, "Expert parallel (EP)", "each device: 4 of the 8 experts", "all-to-all: dispatch and combine", True)
for i, lab in enumerate(["dev 0", "dev 1"]):
    dx = x + 14 + i * 152
    dev(dx, cy + 58, 140, 116, lab)
    for k in range(4):
        e = 4 * i + k
        blk(dx + 10 + (k % 2) * 62, cy + 84 + (k // 2) * 30, 56, f"E{e}", AMBER)

# DeepInfer summary
x = 46 + 2 * (BW + GAP)
d.rect(x, cy, BW, ch, fill=EMERALD[1], stroke=EMERALD[0], sw=1.5)
d.text(x + 14, cy + 24, "DeepInfer, one rank per device", 14.5, EMERALD[0], "bold")
lines = [
    ("attention", "DP: full weights on each rank"),
    ("long prefill", "CP: ranks share one prompt"),
    ("MoE experts", "EP: 1 / ep_size of the experts"),
    ("Engram tables", "rows split over a group"),
    ("TP and PP", "no group exists"),
]
for i, (k, v) in enumerate(lines):
    ly = cy + 62 + i * 30
    d.text(x + 14, ly, k, 12.5, INK, "bold")
    d.text(x + 124, ly, v, 12.5, INK)

y = y1 + P2_H + 24
d.legend(30, y, [(EMERALD, "used by DeepInfer"), (PINK, "not used by DeepInfer"), (BLUE, "layer weights"),
                 (VIOLET, "tokens of one prompt"), (AMBER, "experts")])
y += 36
y = d.footnotes(30, y, [
    "CP token split shown as DeepInfer's balanced 'mirror' order: rank i gets chunk i and chunk 2·cp − 1 − i (prepare_cp_mirror.py:145-146).",
    "Simplified: with CP and EP, the same ranks also do DP for attention. See panel 2 of the groups diagram.",
])
d.save(height=y + 10)
