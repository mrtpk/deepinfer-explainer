"""Diagram: one MoE layer with expert parallelism on the DeepEP path (dispatch, grouped GEMMs, combine).

Used by: src/concepts/expert-parallelism.html, src/code/v4-mlp.html
Sources (commit 9bd9cf2):
  deepinfer/model_executor/models/v4_modules/mlp.py:565-616   DeepseekMoE.forward (non-mega path)
  deepinfer/model_executor/models/v4_modules/mlp.py:461-490   dispatch(): EPBuffer.dispatch arguments
  deepinfer/model_executor/models/v4_modules/mlp.py:406-459   routed_experts_forward(): two grouped GEMMs + SwiGLU
  deepinfer/model_executor/models/v4_modules/mlp.py:493-511   combine(): bias = shared expert output
  deepinfer/model_executor/models/v4_modules/mlp.py:513-526   shared_forward()
  deepinfer/model_executor/models/v4_modules/mlp.py:109-137   _grouped_gemm(): DeepGEMM m_grouped_*_contiguous, psum layout
  deepinfer/model_executor/models/v4_modules/mlp.py:196-205   physical slots split evenly over EP ranks
Toy example: 3 EP ranks, 6 physical slots (2 per rank), top-2, 5 tokens.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, VIOLET, WHITE, Diagram  # noqa: E402

d = Diagram(width=1100)
d.header(
    "Expert parallelism: dispatch, grouped GEMM, combine",
    "DeepEP path of DeepseekMoE.forward (mlp.py:565-616)  ·  used when mega-MoE is off  ·  commit 9bd9cf2",
    params="toy example: EP = 3 ranks   6 expert slots (2 per rank)   top-2   5 tokens",
)

# ============================================================================
# Panel 1: where the tokens go
# ============================================================================
y0 = 112
CW, GAP = 328, 12
XS = [46 + i * (CW + GAP) for i in range(3)]
A_Y = y0 + 72
A_H = 84
B1_Y = A_Y + A_H + 34
BAND_H = 30
B_Y = B1_Y + BAND_H + 34
B_H = 102
B2_Y = B_Y + B_H + 34
C_Y = B2_Y + BAND_H + 34
C_H = 84
P1_H = C_Y + C_H + 20 - y0
d.panel(y0, P1_H, 1, "Where do the tokens go?",
        "Each token visits the ranks that hold its k experts, then comes back to its own rank.")

own = [
    ("rank 0: own tokens", ["a -> E0, E3", "b -> E1, E4"]),
    ("rank 1: own tokens", ["c -> E0, E2"]),
    ("rank 2: own tokens", ["d -> E3, E5", "e -> E0, E5"]),
]
recv = [
    ("rank 0 holds E0, E1", ["E0: a, c, e", "E1: b", "R = 4 rows, psum = [3, 4]"]),
    ("rank 1 holds E2, E3", ["E2: c", "E3: a, d", "R = 3 rows, psum = [1, 3]"]),
    ("rank 2 holds E4, E5", ["E4: b", "E5: d, e", "R = 3 rows, psum = [1, 3]"]),
]
back = [
    ("rank 0: own tokens again", ["a = w*E0(a) + w*E3(a) + sh(a)", "b = w*E1(b) + w*E4(b) + sh(b)"]),
    ("rank 1: own tokens again", ["c = w*E0(c) + w*E2(c) + sh(c)"]),
    ("rank 2: own tokens again", ["d = w*E3(d) + w*E5(d) + sh(d)", "e = w*E0(e) + w*E5(e) + sh(e)"]),
]


def card(x, y, h, title, lines, col):
    d.rect(x, y, CW, h, fill=col[1], stroke=col, sw=1.5)
    d.text(x + 14, y + 22, title, 14, col[0], "bold")
    for i, s in enumerate(lines):
        d.text(x + 14, y + 44 + i * 18, s, 12.5, INK, mono=True)


for i in range(3):
    card(XS[i], A_Y, A_H, *own[i], BLUE)
    card(XS[i], B_Y, B_H, *recv[i], VIOLET)
    card(XS[i], C_Y, C_H, *back[i], BLUE)
    cx = XS[i] + CW / 2
    d.arrow(cx, A_Y + A_H, cx, B1_Y - 2, AMBER)
    d.arrow(cx, B1_Y + BAND_H, cx, B_Y - 2, AMBER)
    d.arrow(cx, B_Y + B_H, cx, B2_Y - 2, AMBER)
    d.arrow(cx, B2_Y + BAND_H, cx, C_Y - 2, AMBER)

for by, lead, body in (
    (B1_Y, "dispatch", "all-to-all: one copy of each token for each chosen expert  (EPBuffer.dispatch, mlp.py:469-489)"),
    (B2_Y, "combine", "all-to-all back: sum the k expert rows of each token, add the shared expert  (mlp.py:501-510)"),
):
    d.rect(46, by, 1008, BAND_H, fill=AMBER[1], stroke=AMBER, rx=6, sw=1.4)
    d.text(60, by + 20, lead, 12.5, AMBER[0], "bold", mono=True)
    d.text(140, by + 20, body, 12.5, INK)

# ============================================================================
# Panel 2: what runs on one rank
# ============================================================================
y0 = y0 + P1_H + 20
CARD_H = 54
CARD_GAP = 16
steps = [
    ("gate_forward", "topk_idx [T, k] (physical slots), topk_weights [T, k]", "mlp.py:574", BLUE),
    ("dispatch (DeepEP)", "recv x: fp8 [R, hidden] + scales;  handle.psum_num_recv_tokens_per_expert", "mlp.py:578-585", AMBER),
    ("grouped GEMM 1: gate_up", "fp8 [R, hidden] x fp4 [E_local, 2*inter, hidden] -> bf16 [R, 2*inter]", "mlp.py:417-430", VIOLET),
    ("SwiGLU, x routing weight, fp8 cast", "bf16 [R, 2*inter] -> fp8 [R, inter] + scales", "mlp.py:436-442", VIOLET),
    ("grouped GEMM 2: down", "fp8 [R, inter] x fp4 [E_local, hidden, inter] -> bf16 [R, hidden]", "mlp.py:444-457", VIOLET),
    ("shared expert (fewer SMs)", "own tokens x of this rank -> bf16 [T, hidden]", "mlp.py:601-603", EMERALD),
    ("combine (DeepEP), bias = shared", "-> bf16 [T, hidden]: the MoE output of this rank's own tokens", "mlp.py:604-610", AMBER),
]
P2_H = 72 + len(steps) * (CARD_H + CARD_GAP) - CARD_GAP + 22
d.panel(y0, P2_H, 2, "What runs on one rank?",
        "T = own tokens, R = received rows (about T x k on average), E_local = expert slots on this rank.")
cy = y0 + 72
for i, (title, row, cite, col) in enumerate(steps):
    d.rect(46, cy, 1008, CARD_H, fill=col[1], stroke=col, sw=1.4)
    d.rect(46, cy, 6, CARD_H, fill=col[0], stroke=None, rx=3)
    d.badge(70, cy + 18, i + 1, col, r=10, size=11)
    d.text(88, cy + 23, title, 14, INK, "bold")
    d.text(88, cy + 43, row, 12.5, INK, mono=True)
    d.pill_auto(1054 - 10 - (len(cite) * 11 * 0.602 + 20), cy + 9, cite, col[0])
    if i < len(steps) - 1:
        d.arrow(70, cy + CARD_H, 70, cy + CARD_H + CARD_GAP - 2, col)
    cy += CARD_H + CARD_GAP

y = y0 + P2_H + 22
d.legend(30, y, [(BLUE, "own tokens"), (AMBER, "DeepEP communication"), (VIOLET, "routed experts"), (EMERALD, "shared expert")])
y += 38
y = d.footnotes(30, y, [
    "Shapes for the default checkpoint format: fp8 activations, MXFP4 expert weights (hugging_face/config.py:252-264). w = routing weight.",
    "Not shown: padding of each expert group to expert_alignment (mlp.py:477), CUDA events and streams, the EPLB token counter (mlp.py:474).",
    "DeepEP internals are not shown. The site explains only the arguments that DeepInfer passes.",
])
d.save(height=y + 10)
