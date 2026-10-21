"""Diagram: AFD (attention-FFN disaggregation) compared with what DeepInfer does.

Used by: src/concepts/hardware-platforms.html (section "Is DeepInfer AFD?")
Sources (commit 9bd9cf2):
  deepinfer/model_executor/models/decoder_layer.py:155-173   attention, then MoE, in one forward()
  deepinfer/model_executor/models/v4_modules/mlp.py:461-511 DeepEP dispatch / combine
  deepinfer/model_executor/parallel_utils/parallel_state.py:82-117  one backend for all groups
  README.md:38-41, doc/inference_deployment_qa.md:29-63
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, GRAY_MID, INK, MUTE, NEUTRAL, VIOLET, WHITE, Diagram  # noqa: E402

d = Diagram()
d.header(
    "Is DeepInfer AFD? No.",
    "AFD puts attention and FFN on different devices. DeepInfer runs both on every device and moves tokens only for the MoE experts.",
    params="AFD = Attention-FFN Disaggregation     DP = data parallel     EP = expert parallel",
)

# ============================================================================
# Panel 1: AFD
# ============================================================================
y0 = 112
P1_H = 252
d.panel(y0, P1_H, 1, "AFD (a design DeepInfer does NOT use): two pools of devices",
        "Attention runs on one pool, the FFN (experts) on another pool. Hidden states cross between the pools in every layer.")
ly = y0 + 70
lh = P1_H - 90
d.lane(46, ly, 500, lh, BLUE, "Attention pool", ["only attention layers + KV cache"])
d.lane(954, ly, 500, lh, VIOLET, "FFN / expert pool", ["only FFN or MoE expert layers"])
for i in range(4):
    bx = 62 + i * 118
    d.rect(bx, ly + 82, 106, 64, fill=BLUE[1], stroke=BLUE, sw=1.2, rx=6)
    d.text(bx + 53, ly + 110, f"device {i}", 12, BLUE, "bold", "middle", mono=True)
    d.text(bx + 53, ly + 128, "attention", 11.5, INK, anchor="middle", mono=True)
    fx = 970 + i * 118
    d.rect(fx, ly + 82, 106, 64, fill=VIOLET[1], stroke=VIOLET, sw=1.2, rx=6)
    d.text(fx + 53, ly + 110, f"device {i + 4}", 12, VIOLET, "bold", "middle", mono=True)
    d.text(fx + 53, ly + 128, "FFN", 11.5, INK, anchor="middle", mono=True)
a1 = ly + 96
a2 = ly + 136
d.arrow(546, a1, 952, a1, AMBER, sw=2)
d.arrow_label(750, a1, "hidden states after attention, every layer", AMBER)
d.arrow(954, a2, 548, a2, AMBER, sw=2)
d.arrow_label(750, a2, "FFN output, back for the next layer", AMBER)

# ============================================================================
# Panel 2: DeepInfer
# ============================================================================
y0 = y0 + P1_H + 20
ranks = 4
cw, cg = 337, 20
top = y0 + 92
att_y, att_h = top + 34, 62
bus1_y = att_y + att_h + 34
bus_h = 34
moe_y = bus1_y + bus_h + 34
moe_h = 62
bus2_y = moe_y + moe_h + 34
nxt_y = bus2_y + bus_h + 34
col_bottom = moe_y + moe_h + 12
P2_H = nxt_y - y0 + 64
d.panel(y0, P2_H, 2, "DeepInfer: every device runs attention AND the MoE layer",
        "Attention is data parallel (each device has its own requests). Only the MoE layer sends tokens to other devices, and it sends them back.")
for i in range(ranks):
    x = 46 + i * (cw + cg)
    # same-device container (neutral, dashed)
    d.rect(x, top, cw, col_bottom - top, fill=WHITE, stroke=GRAY_MID, rx=12, sw=1.2, dash="4 4")
    d.text(x + 14, top + 22, f"device {i}  (one GPU or one NPU)", 12, INK, "bold", mono=True)
    d.box(x + 16, att_y, cw - 32, att_h, "attention", [f"own requests (DP rank {i})  ·  own KV cache"], col=BLUE)
    d.box(x + 16, moe_y, cw - 32, moe_h, "MoE layer", [f"its slice of the experts (EP rank {i})"], col=VIOLET)
    cxm = x + cw / 2
    d.arrow(cxm, att_y + att_h, cxm, bus1_y - 2, AMBER)
    d.arrow(cxm, bus1_y + bus_h, cxm, moe_y - 2, AMBER)
    d.arrow(cxm, moe_y + moe_h, cxm, bus2_y - 2, AMBER)
    d.arrow(cxm, bus2_y + bus_h, cxm, nxt_y - 2, INK)
    d.text(cxm, nxt_y + 16, "next layer, same device", 11.5, MUTE, anchor="middle", italic=True)
for by, lead, body in (
    (bus1_y, "dispatch", "DeepEP all-to-all: each token goes to the devices that hold its top-k experts  (mlp.py:461-490)"),
    (bus2_y, "combine", "DeepEP all-to-all: expert outputs return to the token's own device  (mlp.py:493-511)"),
):
    d.rect(46, by, 1408, bus_h, fill=AMBER[1], stroke=AMBER, rx=6, sw=1.4)
    d.text(62, by + 22, lead, 12.5, AMBER, "bold", mono=True)
    d.text(146, by + 22, body, 12, INK)
d.text(46, nxt_y + 44, "All device process groups use ONE backend: PLATFORM.distributed_backend = \"nccl\" or \"hccl\"  (parallel_state.py:82-117). "
       "NCCL and HCCL cannot talk to each other.", 12, INK, "bold")

# ============================================================================
# Panel 3: E/P/D
# ============================================================================
y0 = y0 + P2_H + 20
P3_H = 196
d.panel(y0, P3_H, 3, "What the docs DO split: vision encoder / prefill / decode (E/P/D)",
        "Separate instances per stage, not per layer. P and D instances run the whole LLM; VE runs only the vision encoder. Not in this release.")
by = y0 + 76
bw, bh = 400, 78
xs = [46, 550, 1054]
labels = [
    ("VE instances", ["vision encoder, about 1 GPU each", "qa.md:51"]),
    ("Prefill instances", ["EP2-8 / DP2-8, attention + MoE", "qa.md:47"]),
    ("Decode instances", ["EP64-128 / DP64-128, attention + MoE", "qa.md:49"]),
]
for x, (t, ls) in zip(xs, labels):
    d.rect(x, by, bw, bh, fill=NEUTRAL[2], stroke=GRAY_MID, rx=8, sw=1.4, dash="4 3")
    d.text(x + bw / 2, by + 22, t, 13.5, INK, "bold", "middle")
    for j, s in enumerate(ls):
        d.text(x + bw / 2, by + 42 + j * 16, s, 11.5, INK if j == 0 else MUTE, anchor="middle", mono=True)
d.arrow(xs[0] + bw, by + bh / 2, xs[1] - 2, by + bh / 2, GRAY_MID, dash="5 4")
d.arrow(xs[1] + bw, by + bh / 2, xs[2] - 2, by + bh / 2, GRAY_MID, dash="5 4")
d.text(46, by + bh + 26, "README.md:41: \"VE/Prefill/Decode disaggregation (most required engine functionality is already implemented)\" is listed under \"not included in this release\".",
       11.5, MUTE, italic=True)

y = y0 + P3_H + 24
d.legend(30, y, [
    (BLUE, "attention"),
    (VIOLET, "FFN / MoE experts"),
    (AMBER, "tokens moving between devices"),
    (NEUTRAL, "not in this release"),
])
y += 40
y = d.footnotes(30, y, [
    "Simplified: panel 2 shows 4 devices and one layer. Real decode uses EP64-128. Not shown: DeepInfer calls DeepEP with async_with_compute_stream=True (mlp.py:479, 507).",
    "qa.md = doc/inference_deployment_qa.md. Attention uses data parallelism with #DP = #EP (qa.md:33).",
])
d.save(height=y + 14)
