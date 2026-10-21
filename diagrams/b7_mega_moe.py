"""Diagram: when DeepInfer uses mega-MoE, and what the mega path replaces.

Used by: src/concepts/mega-moe.html
Sources (commit 9bd9cf2):
  deepinfer/model_executor/models/v4_modules/mlp.py:177-188   mma_type and the use_mega_moe condition
  deepinfer/model_executor/parallel_utils/parallel_state.py:130-134  is_within_nvl_domain (NPU: always True)
  deepinfer/hugging_face/config.py:251-264, 300-305           checkpoint must be fp8 + fp4 experts -> mma_type fp8xfp4
  deepinfer/model_executor/models/v4_modules/mlp.py:254-272   mega_moe_func, fuse_shared, weight conversion
  deepinfer/model_executor/models/v4_modules/mlp.py:274-325   fused norm cast into the SymmBuffer; buffer allocation
  deepinfer/model_executor/models/v4_modules/mlp.py:528-563   mega_moe_forward
  deepinfer/model_executor/models/v4_modules/mlp.py:565-616   forward: mega path or DeepEP path
  doc/inference_deployment_qa.md:229-231                      "Mega MoE is the general solution within a scale-up domain"
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, GRAY_MID, INK, MUTE, NEUTRAL, TEAL, VIOLET, WHITE, Diagram  # noqa: E402

d = Diagram(width=1100)
d.header(
    "Mega-MoE: the whole MoE layer in one call",
    "DeepseekMoE in v4_modules/mlp.py  ·  decided once per layer at start-up  ·  commit 9bd9cf2",
    params="mma_type = activation x weight type: \"fp8xfp4\" for the released checkpoint format",
)

# ============================================================================
# Panel 1: the decision
# ============================================================================
y0 = 112
BW, BH = 300, 96
XS = [46, 400, 754]
by = y0 + 76
P1_H = 76 + BH + 34 + 42 + 22
d.panel(y0, P1_H, 1, "When does a layer use mega-MoE?",
        "use_mega_moe needs both conditions (mlp.py:184-188). The value is fixed when the layer is built.")


def cond(x, num, title, lines, col):
    d.rect(x, by, BW, BH, fill=col[1], stroke=col, sw=1.5)
    d.badge(x + 20, by + 21, num, col, r=11, size=12)
    d.text(x + 38, by + 26, title, 14, INK, "bold")
    for i, s in enumerate(lines):
        d.text(x + 14, by + 52 + i * 18, s, 12.5, INK, mono=True)


cond(XS[0], "A", "Platform or data types", ["PLATFORM.is_gpu", "  or mma_type == \"fp8xfp4\"", "(fp8xfp4: also on Ascend)"], BLUE)
cond(XS[1], "B", "EP group in one NVLink domain", ["is_within_nvl_domain(ep_group)", "GPU: size 1, or size <= DeepEP", "  physical domain size; NPU: True"], BLUE)
d.text(XS[0] + BW + 27, by + BH / 2 + 7, "and", 15, INK, "bold", "middle")
jx = XS[1] + BW + 27
d.line(XS[1] + BW, by + BH / 2, jx, by + BH / 2, col=INK, sw=1.6)
d.circle(jx, by + BH / 2, 4, INK)
d.path_arrow(f"M {jx},{by + BH / 2} L {jx},{by + BH / 4 - 2} L {XS[2] - 2},{by + BH / 4 - 2}", TEAL)
d.path_arrow(f"M {jx},{by + BH / 2} L {jx},{by + 3 * BH / 4 + 2} L {XS[2] - 2},{by + 3 * BH / 4 + 2}", AMBER)
# result box split in two
d.rect(XS[2], by, BW, BH / 2 - 4, fill=TEAL[1], stroke=TEAL, sw=1.5)
d.text(XS[2] + 14, by + 28, "both true -> mega-MoE", 14, TEAL[0], "bold")
d.rect(XS[2], by + BH / 2 + 4, BW, BH / 2 - 4, fill=AMBER[1], stroke=AMBER, sw=1.5)
d.text(XS[2] + 14, by + BH / 2 + 32, "else -> DeepEP path", 14, AMBER[0], "bold")

ty = by + BH + 34
d.text(46, ty, "Released checkpoint format: fp8 activations x MXFP4 experts -> mma_type \"fp8xfp4\", so A is always true.", 12.5, INK, "bold")
d.text(46, ty + 22, "GPU: mega-MoE when the EP group fits in the NVLink domain.   Ascend: always mega-MoE.", 12.5, INK, mono=True)
d.text(46, ty + 42, "The docs: \"Mega MoE is the general solution within a scale-up domain\"  (inference_deployment_qa.md:231)", 12, MUTE, italic=True)

# ============================================================================
# Panel 2: the two paths side by side
# ============================================================================
y0 = y0 + P1_H + 20
LW = 486
LX = [46, 568]
ROW_H, ROW_GAP = 46, 10
left = [
    ("ffn norm", "fp8 x + scales, new tensors"),
    ("gate_forward", "topk_idx, topk_weights"),
    ("dispatch", "DeepEP EPBuffer"),
    ("grouped GEMM gate_up", "DeepGEMM"),
    ("SwiGLU + fp8 cast", "tile_kernels"),
    ("grouped GEMM down", "DeepGEMM"),
    ("shared expert", "two linears, fewer SMs"),
    ("combine", "DeepEP EPBuffer"),
]
right = [
    ("ffn norm -> SymmBuffer", "writes fp8 x, x_sf into sym_buffer"),
    ("gate_forward -> SymmBuffer", "writes topk_idx, topk_weights"),
    ("ONE call: fp8_fp4_mega_moe", "dispatch + 2 GEMMs + SwiGLU"),
    ("", "+ shared expert + combine"),
]
lane_top = y0 + 72
lane_h = 64 + 14 + len(left) * (ROW_H + ROW_GAP) + 4
P2_H = (lane_top - y0) + lane_h + 20
d.panel(y0, P2_H, 2, "What does the mega path replace?",
        "Eight steps become two writes into a symmetric buffer and one DeepGEMM call.")
d.lane(LX[0], lane_top, LW, lane_h, AMBER, "DeepEP path  (forward, mlp.py:574-616)", ["buffer: deep_ep.EPBuffer  (userbuffer.allocate_ep)"])
d.lane(LX[1], lane_top, LW, lane_h, TEAL, "Mega path  (mega_moe_forward, mlp.py:528-563)", ["buffer: deep_gemm.SymmBuffer  (userbuffer.allocate_sym_buffer)"])

ry = lane_top + 64 + 14
for i, (t, s) in enumerate(left):
    y = ry + i * (ROW_H + ROW_GAP)
    d.rect(LX[0] + 14, y, LW - 28, ROW_H, fill=WHITE, stroke=AMBER, sw=1.3)
    d.text(LX[0] + 28, y + 28, t, 13.5, INK, "bold")
    d.text(LX[0] + LW - 28, y + 28, s, 12.5, MUTE, anchor="end", mono=True)
    if i < len(left) - 1:
        d.arrow(LX[0] + 40, y + ROW_H, LX[0] + 40, y + ROW_H + ROW_GAP - 2, AMBER)

big_h = 2 * ROW_H + ROW_GAP
rows_r = [(0, ROW_H), (1, ROW_H), (2, big_h)]
for idx, (k, h) in enumerate(rows_r):
    y = ry + k * (ROW_H + ROW_GAP)
    d.rect(LX[1] + 14, y, LW - 28, h, fill=WHITE if k < 2 else TEAL[1], stroke=TEAL, sw=1.3 if k < 2 else 2)
    if k < 2:
        d.text(LX[1] + 28, y + 28, right[k][0], 13.5, INK, "bold")
    if idx < 2:
        d.arrow(LX[1] + 40, y + h, LX[1] + 40, y + h + ROW_GAP - 2, TEAL)
d.text(LX[1] + 236, ry + 28, "fused_norm_cast_kwargs", 12.5, MUTE, mono=True)
d.text(LX[1] + 236, ry + (ROW_H + ROW_GAP) + 28, "out = sym_buffer slices", 12.5, MUTE, mono=True)
y = ry + 2 * (ROW_H + ROW_GAP)
d.text(LX[1] + 28, y + 28, "ONE DeepGEMM call", 14, TEAL[0], "bold")
d.text(LX[1] + 28, y + 50, "fp8_fp4_mega_moe(out, l1, l2, sym_buffer,", 12.5, INK, mono=True)
d.text(LX[1] + 28, y + 68, "  shared_l1/l2, expert_recv_stats, ...)", 12.5, INK, mono=True)
d.text(LX[1] + 28, y + 86, "replaces dispatch ... combine on the left", 12.5, MUTE, mono=True)
y2 = y + big_h + ROW_GAP + 14
notes = [
    "Weights are converted once at load:",
    "  deep_gemm.transform_weights_for_mega_moe",
    "  (mlp.py:93-106, 259-272)",
    "Shared expert goes into the same call when",
    "  the layer has one (fuse_shared, mlp.py:256)",
    "The call still counts tokens for EPLB:",
    "  cumulative_local_expert_recv_stats (mlp.py:555)",
]
for i, s in enumerate(notes):
    d.text(LX[1] + 28, y2 + i * 19, s, 12.5, INK if not s.startswith("  ") else MUTE, mono=s.startswith("  "))

y = y0 + P2_H + 22
d.legend(30, y, [(BLUE, "condition"), (AMBER, "DeepEP path"), (TEAL, "mega-MoE path")])
y += 38
y = d.footnotes(30, y, [
    "The mega kernels are in DeepGEMM, which is not in this repo. This diagram shows only how DeepInfer calls them.",
    "bf16 activations use deep_gemm.bf16_mega_moe instead (mlp.py:255). The fused norm output is used only with fp8 activations (mlp.py:275).",
])
d.save(height=y + 10)
