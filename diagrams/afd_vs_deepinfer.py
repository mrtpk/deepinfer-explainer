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
from svglib import AMBER, BLUE, GRAY_MID, INK, MUTE, NEUTRAL, VIOLET, WHITE, Diagram, text_width  # noqa: E402

W = 1100
R = W - 46          # right edge of panel content
d = Diagram(width=W)
d.header(
    "Is DeepInfer AFD? No.",
    "AFD puts attention and FFN on different devices. DeepInfer runs both on every device and moves tokens only for the MoE experts.",
    params="AFD = Attention-FFN Disaggregation     DP = data parallel     EP = expert parallel",
)


def wrap(s, size, max_w, indent="", bold=False):
    out, cur = [], ""
    for w in s.split(" "):
        t = (cur + " " + w) if cur else w
        if cur and text_width(t, size, bold=bold) > max_w:
            out.append(cur)
            cur = indent + w
        else:
            cur = t
    out.append(cur)
    return out


def panel(y, h, num, title, sub):
    """Panel with a subtitle that wraps to a second line when needed. Returns the extra height used."""
    d.panel(y, h, num, title)
    lines = wrap(sub, 12.5, R - 68)
    for i, s in enumerate(lines):
        d.text(68, y + 50 + i * 18, s, 12.5, MUTE)
    return (len(lines) - 1) * 18


def sub_lines(sub):
    return len(wrap(sub, 12.5, R - 68))


# ============================================================================
# Panel 1: AFD
# ============================================================================
y0 = 112
SUB1 = "Attention runs on one pool, the FFN (experts) on another pool. Hidden states cross between the pools in every layer."
ex1 = (sub_lines(SUB1) - 1) * 18
lw = 330
dev_w, dev_h, dev_g = 144, 58, 14
lh = 64 + 16 + 2 * dev_h + dev_g + 18
ly = y0 + 70 + ex1
P1_H = ly + lh + 20 - y0
panel(y0, P1_H, 1, "AFD (a design DeepInfer does NOT use): two pools of devices", SUB1)
lx1, lx2 = 46, R - lw
d.lane(lx1, ly, lw, lh, BLUE, "Attention pool", ["only attention layers + KV cache"])
d.lane(lx2, ly, lw, lh, VIOLET, "FFN / expert pool", ["only FFN or MoE expert layers"])
row_y = [ly + 64 + 16, ly + 64 + 16 + dev_h + dev_g]
for i in range(4):
    r_, c_ = divmod(i, 2)
    by = row_y[r_]
    bx = lx1 + 14 + c_ * (dev_w + 14)
    d.rect(bx, by, dev_w, dev_h, fill=BLUE[1], stroke=BLUE, sw=1.2, rx=6)
    d.text(bx + dev_w / 2, by + 24, f"device {i}", 12.5, BLUE, "bold", "middle", mono=True)
    d.text(bx + dev_w / 2, by + 44, "attention", 12.5, INK, anchor="middle", mono=True)
    fx = lx2 + 14 + c_ * (dev_w + 14)
    d.rect(fx, by, dev_w, dev_h, fill=VIOLET[1], stroke=VIOLET, sw=1.2, rx=6)
    d.text(fx + dev_w / 2, by + 24, f"device {i + 4}", 12.5, VIOLET, "bold", "middle", mono=True)
    d.text(fx + dev_w / 2, by + 44, "FFN", 12.5, INK, anchor="middle", mono=True)
a1 = row_y[0] + dev_h / 2
a2 = row_y[1] + dev_h / 2
ax1, ax2 = lx1 + lw, lx2
d.arrow(ax1, a1, ax2 - 2, a1, AMBER, sw=2)
d.arrow_label((ax1 + ax2) / 2, a1, "hidden states after attention, every layer", AMBER)
d.arrow(ax2, a2, ax1 + 2, a2, AMBER, sw=2)
d.arrow_label((ax1 + ax2) / 2, a2, "FFN output, back for the next layer", AMBER)

# ============================================================================
# Panel 2: DeepInfer  (one row per device; the two all-to-all steps span all rows)
# ============================================================================
y0 = y0 + P1_H + 20
SUB2 = ("Attention is data parallel (each device has its own requests). Only the MoE layer sends tokens to other devices, "
        "and it sends them back.")
ex2 = (sub_lines(SUB2) - 1) * 18
ranks = 4
top = y0 + 104 + ex2           # first device row; bus labels sit above it
row_h, row_g = 104, 12
box_h = 62
att_x, att_w = 60, 324
bus1_x, bus_w = 406, 88
moe_x, moe_w = 516, 240
bus2_x = 778
nxt_x = bus2_x + bus_w + 34
rows_bottom = top + ranks * row_h + (ranks - 1) * row_g
notes_y = rows_bottom + 30
BOLD_NOTE = ("All device process groups use ONE backend: PLATFORM.distributed_backend = \"nccl\" or \"hccl\"  (parallel_state.py:82-117). "
             "NCCL and HCCL cannot talk to each other.")
bold_lines = wrap(BOLD_NOTE, 12, R - 46, bold=True)
P2_H = notes_y + 2 * 26 + 10 + len(bold_lines) * 18 + 14 - y0
panel(y0, P2_H, 2, "DeepInfer: every device runs attention AND the MoE layer", SUB2)

for i in range(ranks):
    ry = top + i * (row_h + row_g)
    # same-device container (neutral, dashed)
    d.rect(46, ry, R - 46, row_h, fill=WHITE, stroke=GRAY_MID, rx=12, sw=1.2, dash="4 4")
    d.text(60, ry + 22, f"device {i}  (one GPU or one NPU)", 12.5, INK, "bold", mono=True)
    by = ry + 32
    for x, w, title, lines, col in (
        (att_x, att_w, "attention", [f"own requests (DP rank {i})  ·  own KV cache"], BLUE),
        (moe_x, moe_w, "MoE layer", ["its slice of the experts", f"(EP rank {i})"], VIOLET),
    ):
        d.rect(x, by, w, box_h, fill=col[1], stroke=col, sw=1.5)
        d.text(x + w / 2, by + 19, title, 14, col, "bold", "middle")
        ly0 = by + 46 if len(lines) == 1 else by + 39
        for j, s in enumerate(lines):
            d.text(x + w / 2, ly0 + j * 16, s, 12, INK, anchor="middle", mono=True)
    cy = by + box_h / 2
    d.arrow(att_x + att_w, cy, bus1_x - 2, cy, AMBER)
    d.arrow(bus1_x + bus_w, cy, moe_x - 2, cy, AMBER)
    d.arrow(moe_x + moe_w, cy, bus2_x - 2, cy, AMBER)
    d.arrow(bus2_x + bus_w, cy, nxt_x - 2, cy, INK)
    d.text(nxt_x + 8, cy - 4, "next layer,", 12, MUTE, italic=True)
    d.text(nxt_x + 8, cy + 12, "same device", 12, MUTE, italic=True)

# the two all-to-all steps: amber bars across all device rows
bars = (
    (bus1_x, "dispatch", "DeepEP all-to-all: each token goes to the devices that hold its top-k experts  (mlp.py:461-490)"),
    (bus2_x, "combine", "DeepEP all-to-all: expert outputs return to the token's own device  (mlp.py:493-511)"),
)
bar_top = top - 34
for bx, lead, _ in bars:
    d.rect(bx, bar_top, bus_w, rows_bottom - bar_top + 8, fill=AMBER[1], stroke=AMBER, rx=6, sw=1.4)
    d.text(bx + bus_w / 2, bar_top + 22, lead, 12.5, AMBER, "bold", "middle", mono=True)
for k, (bx, lead, body_) in enumerate(bars):
    ty = notes_y + k * 26
    d.text(46, ty, lead, 12.5, AMBER, "bold", mono=True)
    d.text(130, ty, body_, 12, INK)
for k, s in enumerate(bold_lines):
    d.text(46, notes_y + 2 * 26 + 10 + k * 18, s, 12, INK, "bold")

# ============================================================================
# Panel 3: E/P/D
# ============================================================================
y0 = y0 + P2_H + 20
SUB3 = ("Separate instances per stage, not per layer. P and D instances run the whole LLM; VE runs only the vision encoder. "
        "Not in this release.")
ex3 = (sub_lines(SUB3) - 1) * 18
README = ("README.md:41: \"VE/Prefill/Decode disaggregation (most required engine functionality is already implemented)\" "
          "is listed under \"not included in this release\".")
readme_lines = wrap(README, 11.5, R - 46)
by = y0 + 80 + ex3
bw, bh = 300, 82
gap = (R - 46 - 3 * bw) / 2
P3_H = by + bh + 26 + len(readme_lines) * 17 + 8 - y0
panel(y0, P3_H, 3, "What the docs DO split: vision encoder / prefill / decode (E/P/D)", SUB3)
xs = [46, 46 + bw + gap, 46 + 2 * (bw + gap)]
labels = [
    ("VE instances", ["vision encoder, about 1 GPU each", "qa.md:51"]),
    ("Prefill instances", ["EP2-8 / DP2-8, attention + MoE", "qa.md:47"]),
    ("Decode instances", ["EP64-128 / DP64-128, attention + MoE", "qa.md:49"]),
]
for x, (t, ls) in zip(xs, labels):
    d.rect(x, by, bw, bh, fill=NEUTRAL[2], stroke=GRAY_MID, rx=8, sw=1.4, dash="4 3")
    d.text(x + bw / 2, by + 23, t, 14, INK, "bold", "middle")
    for j, s in enumerate(ls):
        d.text(x + bw / 2, by + 46 + j * 18, s, 12, INK if j == 0 else MUTE, anchor="middle", mono=True)
d.arrow(xs[0] + bw, by + bh / 2, xs[1] - 2, by + bh / 2, GRAY_MID, dash="5 4")
d.arrow(xs[1] + bw, by + bh / 2, xs[2] - 2, by + bh / 2, GRAY_MID, dash="5 4")
d.aside(46, by + bh + 26, readme_lines)

y = y0 + P3_H + 24
d.legend(30, y, [
    (BLUE, "attention"),
    (VIOLET, "FFN / MoE experts"),
    (AMBER, "tokens moving between devices"),
    (NEUTRAL, "not in this release"),
])
y += 40
notes = []
for para in [
    "Simplified: panel 2 shows 4 devices and one layer. Real decode uses EP64-128. Not shown: DeepInfer calls DeepEP with async_with_compute_stream=True (mlp.py:479, 507).",
    "qa.md = doc/inference_deployment_qa.md. Attention uses data parallelism with #DP = #EP (qa.md:33).",
]:
    notes += wrap(para, 12, W - 70, indent="  ")
y = d.footnotes(30, y, notes)
d.save(height=y + 14)
