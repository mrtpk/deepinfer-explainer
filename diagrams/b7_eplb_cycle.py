"""Diagram: the EPLB cycle in DeepInfer: count tokens each step, rearrange every N steps, move the weights.

Used by: src/concepts/eplb.html, src/code/eplb.html
Sources (commit 9bd9cf2):
  deepinfer/model_executor/models/v4_modules/mlp.py:474, 555        dispatch / mega call add to expert_count
  deepinfer/model_executor/models/deepseek.py:402-409                sample() calls eplb.step(is_prompt)
  deepinfer/model_executor/eplb/__init__.py:113-123                  expert_count, window ring, first rearrangement after N // 4
  deepinfer/model_executor/eplb/__init__.py:131-193                  step(): window, rearrangement, LB stats, zero
  deepinfer/model_executor/eplb/__init__.py:195-278                  _initialize_shuffle, _rearrange_experts
  deepinfer/model_executor/eplb/shuffle.py                          P2P and intranode (symm_mem mirror) weight moves
  deepinfer/environ.py:111-121                                       env defaults
  examples/_config.py:77-83                                          example values: window 3, interval 30, after-prefill on
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, GRAY_MID, INK, MUTE, TEAL, VIOLET, WHITE, Diagram  # noqa: E402

d = Diagram(width=1100)
d.header(
    "EPLB in DeepInfer: count, rearrange, move the weights",
    "ExpertLoadBalancer in model_executor/eplb/  ·  one object per group of MoE layers with the same layout  ·  commit 9bd9cf2",
    params="N = DEEPINFER_EXPERT_REARRANGEMENT_STEP_INTERVAL (default 0 = off)   W = DEEPINFER_EXPERT_COUNT_WINDOW_SIZE (default 100)",
)

# ============================================================================
# Panel 1: counting
# ============================================================================
y0 = 112
BW, BH = 300, 122
XS = [46, 400, 754]
by = y0 + 72
P1_H = 72 + BH + 22
d.panel(y0, P1_H, 1, "What does EPLB count in each step?",
        "The MoE kernels add the tokens that each local expert slot receives. One call per step reads and clears the counts.")


def stage(x, num, title, lines, col, h=BH):
    d.rect(x, by, BW, h, fill=col[1], stroke=col, sw=1.5)
    d.badge(x + 20, by + 21, num, col, r=11, size=12)
    d.text(x + 38, by + 26, title, 14, INK, "bold")
    for i, s in enumerate(lines):
        d.text(x + 14, by + 52 + i * 18, s, 12.5, INK, mono=True)


stage(XS[0], 1, "Each MoE layer, each step", ["DeepEP dispatch or mega call:", "cumulative_local_expert_", "  recv_stats = expert_count[l]", "int32 [layers, local slots]"], BLUE)
stage(XS[1], 2, "After sampling", ["DeepseekForCausalLM.sample", "  -> eplb.current().step(", "       is_prompt)", "(deepseek.py:402-404)"], BLUE)
stage(XS[2], 3, "ExpertLoadBalancer.step", ["a. copy counts into window W", "b. step counter; rearrange?", "c. LB stats (default: every 128)", "d. expert_count.zero_()"], VIOLET)
cy = by + BH / 2
d.arrow(XS[0] + BW, cy, XS[1] - 2, cy, BLUE)
d.arrow(XS[1] + BW, cy, XS[2] - 2, cy, BLUE)

# ============================================================================
# Panel 2: timing
# ============================================================================
y0 = y0 + P1_H + 20
P2_H = 250
d.panel(y0, P2_H, 2, "When does it rearrange?",
        "First after N // 4 counted steps (at least 1), then every N counted steps. Example: N = 30.")
tx0, tx1 = 70, 1030
ty = y0 + 108
MAXS = 75
d.line(tx0, ty, tx1, ty, col=GRAY_MID, sw=1.4)


def xs(step):
    return tx0 + (tx1 - tx0) * step / MAXS


for s in range(0, MAXS + 1, 5):
    d.line(xs(s), ty - 5, xs(s), ty + 5, col=GRAY_MID, sw=1)
    d.text(xs(s), ty + 22, f"{s}", 11.5, MUTE, anchor="middle", mono=True)
for s in (7, 37, 67):
    d.rect(xs(s) - 5, ty - 30, 10, 30, fill=AMBER[1], stroke=AMBER, rx=3, sw=1.4)
    d.text(xs(s), ty - 38, f"step {s}", 12.5, AMBER[0], "bold", "middle", mono=True)
d.text(46, ty + 48, "counted step", 12, MUTE, italic=True)
d.text(46, ty + 76, "Start value: N - max(1, N // 4) = 23 (eplb/__init__.py:122-123). Each counted step adds 1; at N it rearranges and starts at 0.", 12.5, INK)
d.text(46, ty + 100, "NORMAL engine, after-prefill flag off: prefill steps do not count.  Flag on (example scripts): the next decode step", 12.5, INK)
d.text(46, ty + 118, "after a prefill step rearranges at once (eplb/__init__.py:83-84, 149-159).  EP size 1: step() returns at once.", 12.5, INK)

# ============================================================================
# Panel 3: weight move
# ============================================================================
y0 = y0 + P2_H + 20
CH = 34
P3_H = 330
d.panel(y0, P3_H, 3, "How do the expert weights move?",
        "Only slots whose expert changes get new weights. Example from the policy diagram: 3 experts move.")
r0x, r1x = 170, 620
ry_old = y0 + 100
ry_new = ry_old + 96
OLD = [0, 1, 2, 3, 4, 5, 0, 1]
NEW = [0, 4, 2, 5, 0, 4, 1, 3]
d.text(46, ry_old + 22, "old", 13.5, INK, "bold")
d.text(46, ry_new + 22, "new", 13.5, INK, "bold")
d.text(r0x, ry_old - 10, "rank 0", 12.5, MUTE, "bold", mono=True)
d.text(r1x, ry_old - 10, "rank 1", 12.5, MUTE, "bold", mono=True)
for row_y, lay in ((ry_old, OLD), (ry_new, NEW)):
    for r, x0 in ((0, r0x), (1, r1x)):
        for k in range(4):
            p = r * 4 + k
            e = lay[p]
            changed = OLD[p] != NEW[p] and row_y == ry_new
            x = x0 + k * 96
            col = EMERALD if changed else (BLUE if row_y == ry_old else GRAY_MID)
            d.rect(x, row_y, 84, CH, fill=EMERALD[1] if changed else WHITE, stroke=col if row_y == ry_old or changed else GRAY_MID, rx=6, sw=1.4)
            d.text(x + 42, row_y + 22, f"e{e}", 13, EMERALD[0] if changed else INK, "bold", "middle", mono=True)
# transfers: e4 (r1 slot 4) -> r0 slot 1; e5 (r1 slot 5) -> r0 slot 3; e3 (r0 slot 3) -> r1 slot 7
mid = ry_old + CH + 31


def xslot(p):
    r, k = divmod(p, 4)
    return (r0x if r == 0 else r1x) + k * 96 + 42


for src, dst, so, do, lv in ((4, 1, -12, 0, -12), (5, 3, 0, -14, 0), (3, 7, 14, 0, 12)):
    sx, dx = xslot(src) + so, xslot(dst) + do
    d.path_arrow(f"M {sx:.1f},{ry_old + CH:.1f} L {sx:.1f},{mid + lv:.1f} L {dx:.1f},{mid + lv:.1f} L {dx:.1f},{ry_new - 2:.1f}", AMBER)
d.text(1050, mid - 18, "3 remote copies", 12, AMBER[0], "bold", "end")
my = ry_new + CH + 30
d.text(46, my, "Rank 1 fills e0, e4 and e1 from its own old slots: local copies, no traffic (shuffle.py:16-25).", 12.5, MUTE, italic=True)
my += 26
d.text(46, my, "GPU, EP group in one NVLink domain:", 12.5, TEAL[0], "bold")
d.text(330, my, "symm_mem mirror of one layer; each rank reads the peer mirror directly (shuffle.py:178-218)", 12.5, INK)
d.text(46, my + 22, "Else (NPU, or larger EP group):", 12.5, VIOLET[0], "bold")
d.text(330, my + 22, "batch_isend_irecv (NCCL or HCCL) in DEEPINFER_REARRANGE_P2P_GROUPS buckets (shuffle.py:94-147)", 12.5, INK)

y = y0 + P3_H + 22
d.legend(30, y, [(BLUE, "counting / old layout"), (VIOLET, "EPLB state"), (AMBER, "rearrangement, moved weights"), (EMERALD, "new weights")])
y += 38
y = d.footnotes(30, y, [
    "Weights per layer: gate_up and down, plus their scales for fp8/fp4 weights; dim 0 is the local slot (deepseek.py:324-329).",
    "The doc values for production: prefill W = 100, N = 1000; decode W = 1000, N = 10000 (inference_deployment_qa.md:99, 103).",
])
d.save(height=y + 10)
