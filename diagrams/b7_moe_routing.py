"""Diagram: how the MoE gate of DeepInfer picks experts for one token, with a worked example.

Used by: src/concepts/moe-routing.html
Sources (commit 9bd9cf2):
  deepinfer/model_executor/models/v4_modules/moe.py:40-67     TopKGate: sqrtsoftplus, noaux_tc, two fp32 biases, bf16 Wgate
  deepinfer/model_executor/models/v4_modules/mlp.py:164-170   asserts noaux_tc, norm_topk_prob, sqrtsoftplus
  deepinfer/model_executor/models/v4_modules/mlp.py:222-231   gate = ReplicatedLinear(use_fp32_output=True), correction bias
  deepinfer/model_executor/models/v4_modules/mlp.py:359-401   gate_forward: kwargs, mega gate (GPU) or moe_topk_gate
  deepinfer/model_executor/eplb/__init__.py:31-39, 86-95      initial physical layout and logical_to_physical_map
The scoring formula sqrt(softplus(z)) and the "bias only for choosing" rule are the usual meaning of the
config names; the kernels (DeepGEMM, tile_kernels) are not in the repo. All numbers are a toy example.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, VIOLET, WHITE, Diagram, text_width  # noqa: E402

d = Diagram(width=1100)
d.header(
    "How the MoE gate picks experts for one token",
    "DeepSeek V4.1 MoE layer in DeepInfer  ·  gate_forward() in v4_modules/mlp.py  ·  commit 9bd9cf2",
    params="T = tokens in the step   n_logical = routed experts in config.json   k = num_experts_per_tok",
)

# ============================================================================
# Panel 1: the pipeline
# ============================================================================
y0 = 112
P1_H = 404
d.panel(y0, P1_H, 1, "What does the gate compute?",
        "A score per expert, a biased top-k choice, normalized weights, then a physical slot for each choice.")

BW, BH = 300, 104
XS = [46, 400, 754]
R1 = y0 + 72
R2 = R1 + BH + 56


def stage(x, y, num, title, lines, col):
    d.rect(x, y, BW, BH, fill=col[1], stroke=col, sw=1.5)
    d.badge(x + 20, y + 21, num, col, r=11, size=12)
    d.text(x + 38, y + 26, title, 14, INK, "bold")
    for i, s in enumerate(lines):
        d.text(x + 14, y + 52 + i * 18, s, 12.5, INK, mono=True)


stage(XS[0], R1, 1, "Gate GEMM (replicated)", ["x      bf16 [T, hidden]", "Wgate  bf16 [n_logical, hidden]", "logits fp32 [T, n_logical]"], BLUE)
stage(XS[1], R1, 2, "Score: sqrtsoftplus", ["s = sqrt(softplus(logit))", "softplus(z) = ln(1 + e^z)", "s > 0 for every expert"], BLUE)
stage(XS[2], R1, 3, "Choose: noaux_tc", ["c = s + bias[e]   fp32", "keep the k largest c", "bias is used ONLY here"], AMBER)
stage(XS[0], R2, 4, "Weights", ["w = s[chosen] / sum(s[chosen])", "w = w * routed_scaling_factor", "(norm_topk_prob = True)"], VIOLET)
stage(XS[1], R2, 5, "Logical -> physical slot", ["logical_to_physical_map", "  [n_logical, extra + 1], -1 = none", "pick 1 of logical_count copies"], EMERALD)
stage(XS[2], R2, 6, "Output to dispatch", ["topk_idx     [T, k]  physical ids", "topk_weights [T, k]", "-> DeepEP or mega-MoE"], EMERALD)

cy1 = R1 + BH / 2
d.arrow(XS[0] + BW, cy1, XS[1] - 2, cy1, BLUE)
d.arrow(XS[1] + BW, cy1, XS[2] - 2, cy1, BLUE)
# snake from box 3 down and left to box 4
gy = R1 + BH + 28
sx = XS[2] + BW / 2
tx = XS[0] + BW / 2
d.path_arrow(f"M {sx:.1f},{R1 + BH:.1f} L {sx:.1f},{gy:.1f} L {tx:.1f},{gy:.1f} L {tx:.1f},{R2 - 2:.1f}", AMBER)
d.text(560, gy - 7, "k chosen expert ids (logical)", 11.5, AMBER, "bold", "middle")
cy2 = R2 + BH / 2
d.arrow(XS[0] + BW, cy2, XS[1] - 2, cy2, VIOLET)
d.arrow(XS[1] + BW, cy2, XS[2] - 2, cy2, EMERALD)

ny = R2 + BH + 30
d.text(46, ny, "GPU: deep_gemm.bf16_mega_gate(x, Wgate, ...) does steps 1-6 in one call  (mlp.py:397-398)", 12.5, INK, mono=True)
d.text(46, ny + 20, "NPU: self.gate(x), then tile_kernels.moe.moe_topk_gate(logits, ...)  (mlp.py:399-400)", 12.5, INK, mono=True)

# ============================================================================
# Panel 2: worked example
# ============================================================================
y0 = y0 + P1_H + 20
LOGITS = [1.2, -0.5, 2.0, 0.3, 1.9, -1.0, 0.8, 0.1]
BIAS = [0.0, 0.0, -0.35, 0.0, 0.05, 0.0, 0.0, 0.0]
S = [math.sqrt(math.log1p(math.exp(z))) for z in LOGITS]
C = [s + b for s, b in zip(S, BIAS)]
top_c = sorted(range(8), key=lambda i: -C[i])[:2]
top_s = sorted(range(8), key=lambda i: -S[i])[:2]
tot = sum(S[i] for i in top_c)
FACTOR = 1.5

ROW = 21
P2_H = 112 + ROW * 9 + 26
d.panel(y0, P2_H, 2, "Worked example: 8 experts, top-2, one token",
        "The bias of expert 2 is negative (it was busy), so expert 0 takes its place. The weights use s, not s + bias.")
ty = y0 + 84
cols = [(46, "expert"), (118, "logit"), (196, "softplus"), (290, "s"), (362, "bias"), (446, "s + bias"), (548, "chosen?")]
for x, h in cols:
    d.text(x, ty, h, 12, MUTE, "bold", mono=True)
d.line(46, ty + 7, 640, ty + 7, col=MUTE, sw=1)
for i in range(8):
    ry = ty + 8 + (i + 1) * ROW
    chosen = i in top_c
    if chosen:
        d.rect(40, ry - 15, 604, ROW - 1, fill=AMBER[1], stroke=None, rx=0)
    col = AMBER[0] if chosen else INK
    vals = [f"{i}", f"{LOGITS[i]:+.1f}", f"{math.log1p(math.exp(LOGITS[i])):.3f}", f"{S[i]:.3f}",
            f"{BIAS[i]:+.2f}", f"{C[i]:.3f}",
            ("yes" if chosen else ("dropped" if i in top_s else "-"))]
    for (x, _), v in zip(cols, vals):
        d.text(x, ry, v, 12.5, col if v != "dropped" else MUTE, "bold" if chosen else "normal", mono=True)

rx0, rw = 668, 386
ry0 = y0 + 70
rh = P2_H - 86
d.rect(rx0, ry0, rw, rh, fill=WHITE, stroke=EMERALD, sw=1.4)
d.text(rx0 + 14, ry0 + 24, "Result of gate_forward for this token", 14, EMERALD[0], "bold")
lines = [
    f"top-2 by s alone      : experts {top_s[0]}, {top_s[1]}",
    f"top-2 by s + bias     : experts {top_c[0]}, {top_c[1]}",
    "",
    f"w({top_c[0]}) = {S[top_c[0]]:.3f} / {tot:.3f} = {S[top_c[0]] / tot:.3f}",
    f"w({top_c[1]}) = {S[top_c[1]]:.3f} / {tot:.3f} = {S[top_c[1]] / tot:.3f}",
    f"x {FACTOR} (example factor) -> {FACTOR * S[top_c[0]] / tot:.3f}, {FACTOR * S[top_c[1]] / tot:.3f}",
    "",
    "4 extra slots, EP = 4 -> 12 slots, 3 per rank",
    "logical 4 -> slot 4 (rank 1), 1 copy",
    "logical 0 -> slot 0 (rank 0) or slot 8 (rank 2)",
]
for i, s in enumerate(lines):
    d.text(rx0 + 14, ry0 + 50 + i * 19, s, 12.5, INK, mono=True)

y = y0 + P2_H + 22
d.legend(30, y, [(BLUE, "score"), (AMBER, "choice (uses the bias)"), (VIOLET, "weights"), (EMERALD, "physical slots / output")])
y += 38
fn = [
    "The gate kernels are in DeepGEMM and tile_kernels. They are not in this repo. Steps 2-4 show the usual meaning of the",
    "  config names sqrtsoftplus, noaux_tc and norm_topk_prob. How the kernel picks one copy of a logical expert is not shown in the repo.",
    "Toy numbers. The real expert count, k and routed_scaling_factor come from the checkpoint config.json (hugging_face/config.py:164-174).",
    "Initial slots: [0..7, then 0, 1, 2, 3] (eplb/__init__.py:31-39). Image tokens use a second bias, bias_vl (mlp.py:233-238).",
]
y = d.footnotes(30, y, fn)
d.save(height=y + 10)
