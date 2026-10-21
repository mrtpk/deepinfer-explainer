"""Diagram: where v4_modules/mlp.py (DeepseekMoE) sits: who calls it, what it owns, what it calls.

Used by: src/code/v4-mlp.html
Sources (commit 9bd9cf2):
  deepinfer/model_executor/models/decoder_layer.py:38-45, 169-173, 200, 238   build and call DeepseekMoE
  deepinfer/model_executor/models/v4_modules/hc.py:52-54, 146                 fused_norm_cast_kwargs
  deepinfer/model_executor/models/deepseek.py:308-321, 323-364, 412-428       EPLB init, allocate_userbuffer
  deepinfer/model_executor/models/deepseek.py:494                             process_moe_weight (dummy FP4)
  deepinfer/model_executor/models/v4_modules/mlp.py:14-36                     imports
  deepinfer/model_executor/models/v4_modules/moe.py                           parameter containers
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, VIOLET, WHITE, Diagram  # noqa: E402

d = Diagram(width=1100)
d.header(
    "Where v4_modules/mlp.py sits",
    "DeepseekMoE: the runtime MoE layer of every decoder layer and every DFlash layer  ·  commit 9bd9cf2",
)

LY = 96
LW = [320, 330, 320]
LX = [30, 30 + LW[0] + 20, 30 + LW[0] + 20 + LW[1] + 20]
ROWS = 5
BOX_H, PITCH = 70, 86
lane_h = 64 + 18 + ROWS * PITCH
d.lane(LX[0], LY, LW[0], lane_h, BLUE, "Callers", ["model code, same process"])
d.lane(LX[1], LY, LW[1], lane_h, VIOLET, "mlp.py + moe.py", ["DeepseekMoE and helpers"])
d.lane(LX[2], LY, LW[2], lane_h, EMERALD, "Callees", ["DeepInfer modules and vendor libraries"])


def box(lane, row, title, lines, col, dash=None):
    x = LX[lane] + 12
    y = LY + 64 + 18 + row * PITCH
    w = LW[lane] - 24
    d.rect(x, y, w, BOX_H, fill=WHITE, stroke=col, sw=1.4, dash=dash)
    d.text(x + 12, y + 22, title, 13.5, col[0], "bold")
    for i, s in enumerate(lines):
        d.text(x + 12, y + 41 + i * 17, s, 12, INK, mono=True)
    return x, y, w


callers = [
    ("DeepseekDecoderLayer", ["builds it (decoder_layer.py:40)", "calls self.mlp(...)  :169-173"]),
    ("DFlashDecoderLayer", ["own MoE config  :198-200", "calls self.mlp(...)  :238"]),
    ("HCLayerMixin.ffn_norm_forward", ["fused_norm_cast_kwargs(T)", "(hc.py:146)"]),
    ("DeepseekForCausalLM.__init__", ["_init_eplb(moes, cfg)", "allocate_userbuffer() per layer"]),
    ("weight loading (dummy)", ["process_moe_weight(...,", "  use_fp4=True)  deepseek.py:494"]),
]
mine = [
    ("DeepseekMoE.__init__", ["counts, mma_type, use_mega_moe", "gate, shared expert, weights"]),
    ("forward / mega_moe_forward", ["gate_forward -> dispatch ->", "experts -> combine (or 1 call)"]),
    ("fused_norm_cast_kwargs", ["norm output straight into", "the SymmBuffer (mega, fp8)"]),
    ("allocate_userbuffer", ["SymmBuffer (mega) or", "EPBuffer (DeepEP)"]),
    ("process_moe_weight", ["HF 2-D expert weight ->", "[E, n, k] + scales"]),
]
callees = [
    ("moe.py containers", ["FusedExperts, TopKGate,", "ReplicatedSharedExpert"]),
    ("deep_ep + eplb", ["EPBuffer.dispatch / combine", "eplb.current().layer(i)"]),
    ("deep_gemm", ["get_block_m_for_mega_moe; also", "mega gate / mega MoE / GEMMs"]),
    ("parallel_utils/userbuffer.py", ["allocate_sym_buffer(...)", "allocate_ep(...)"]),
    ("tile_kernels", ["quant.per_token_cast (e2m1)", "also moe_topk_gate, swiglu"]),
]
for r in range(ROWS):
    bx, by, bw = box(0, r, *callers[r], BLUE)
    mx, my, mw = box(1, r, *mine[r], VIOLET)
    cx, cy, cw = box(2, r, *callees[r], EMERALD)
    d.arrow(bx + bw, by + BOX_H / 2, mx - 2, my + BOX_H / 2, BLUE)
    d.arrow(mx + mw, my + BOX_H / 2, cx - 2, cy + BOX_H / 2, VIOLET)

y = LY + lane_h + 22
d.legend(30, y, [(BLUE, "caller"), (VIOLET, "this file"), (EMERALD, "what it calls")])
y += 38
y = d.footnotes(30, y, [
    "Each arrow is a real call. A callee box can list more functions of the same module. The rows are not one call chain.",
    "Vendor libraries (DeepGEMM, DeepEP) are not checked out in the repo; tile_kernels comes from pip.",
])
d.save(height=y + 10)
