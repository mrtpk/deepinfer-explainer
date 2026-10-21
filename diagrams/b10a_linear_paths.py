"""Diagram: the two linear.py files - HF containers, the runtime ReplicatedLinear, and its GEMM paths.

Used by: src/code/linear.html ("Where it sits")
Sources (commit 9bd9cf2):
  deepinfer/model_executor/models/v4_modules/linear.py:8-34        HF containers: ReplicatedLinear(nn.Linear), ParallelRoutedLinear
  deepinfer/model_executor/models/v4_modules/containers.py:62-135  prepare_meta_fp8, materialize_hf_parameter (packed FP4)
  deepinfer/hugging_face/weights.py:389-436                        load_covered_params
  deepinfer/model_executor/layers/linear.py:47-81                   runtime ReplicatedLinear.__init__ (sf layout)
  deepinfer/model_executor/layers/linear.py:168-185                 apply_weight dispatch
  deepinfer/model_executor/layers/linear.py:116-138, 140-166        BF16 and FP8 paths
  deepinfer/model_executor/models/v4_modules/mlp.py:207-213, 109-137  experts: grouped GEMM (not ReplicatedLinear)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, PINK, VIOLET, Diagram  # noqa: E402

d = Diagram(width=1100)
W = d.W

d.header(
    "linear.py: two files, one GEMM wrapper",
    "v4_modules/linear.py describes the checkpoint weights  ·  layers/linear.py runs the dense GEMMs",
    params="FP8: E4M3 weight, 32 × 32 scales  ·  input cast per token, 1 × 32  ·  output BF16, row stride padded to 32 bytes",
)

# ---------------------------------------------------------------- panel 1
y0 = 112
P1 = 246
d.panel(y0, P1, 1, "Where does a weight go? Meta container → loaded tensor → runtime layer",
        "The HF containers hold no data at first. The runtime classes take the loaded tensors, not the containers.")

bw, bh = 300, 132
by = y0 + 72
d.box(46, by, bw, bh, "v4_modules/linear.py", [
    "ReplicatedLinear(nn.Linear)", "  + use_fp8_gemm", "ParallelRoutedLinear(nn.Linear)", "  weight [n_local·h_in, h_out]", "  + n_local_experts", "linear.py:8-34"],
    col=VIOLET, align="start")
d.box(400, by, bw, bh, "load (meta → device)", [
    "prepare_meta_fp8: E4M3 + FP32 sf", "  sf [ceil(N/32), ceil(K/32)]", "experts: packed FP4 int8", "  [n_local, h_out, h_in/2]", "containers.py:62-135", "weights.py:389-436"],
    col=AMBER, align="start")
d.box(754, by, bw, bh, "runtime users", [
    "layers/linear.py", "  ReplicatedLinear(weight=…)", "  attention, compressor, gate,", "  shared expert, DFlash", "experts: DeepseekMoE grouped", "  GEMM (mlp.py:207-213)"],
    col=BLUE, align="start")
d.arrow(46 + bw, by + bh / 2, 398, by + bh / 2, VIOLET)
d.arrow(400 + bw, by + bh / 2, 752, by + bh / 2, AMBER)

# ---------------------------------------------------------------- panel 2
y1 = y0 + P1 + 20
P2 = 290
d.panel(y1, P2, 2, "Which GEMM runs? apply_weight looks at the weight dtype",
        "BF16 weights use a BF16 GEMM. One-byte weights use the FP8 path. Anything else raises TypeError.")

cw, ch = 300, 150
cy = y1 + 72
d.box(46, cy, cw, 62, "apply_weight(x, bias, out_acc)", ["linear.py:168-178"], col=INK)
d.box(400, cy - 6, cw, ch, "BF16 weight", [
    "out: BF16, or FP32 if", "  use_fp32_output (gate)", "deep_gemm.bf16_gemm_nt(", "  x, W, out, out_acc)", "+ bias (if any)", "linear.py:116-138"],
    col=EMERALD, align="start")
d.box(754, cy - 6, cw, ch, "FP8 weight (1 byte)", [
    "x BF16 → per_token_cast", "  (skipped if x is a tuple)", "assert sf dtype = platform", "deep_gemm.fp8_fp4_gemm_nt", "  recipe (1, 1, 32) → BF16", "linear.py:140-166"],
    col=PINK, align="start")
d.path_arrow(f"M {46 + cw},{cy + 31} L 398,{cy + 31}", EMERALD)
d.arrow_label(373, cy + 31, "bf16", EMERALD)
d.path_arrow(f"M {46 + cw - 40},{cy + 62} L {46 + cw - 40},{cy + ch + 40} L {904},{cy + ch + 40} L {904},{cy + ch - 4}", PINK)
d.text(600, cy + ch + 32, "element_size() == 1", 11.5, PINK, "bold", "middle")
d.text(46, cy + 98, "other dtype →", 12, MUTE)
d.text(46, cy + 116, "TypeError (line 178)", 12, INK, mono=True)

y = y1 + P2 + 22
d.legend(30, y, [(VIOLET, "HF container (meta)"), (AMBER, "loading"), (BLUE, "runtime"), (EMERALD, "BF16 path"),
                 (PINK, "FP8 path")])
y += 36
y = d.footnotes(30, y, [
    "Not shown: the 32-byte output padding (_allocate_output), and the einsum and mega-MoE paths, which call DeepGEMM directly.",
])
d.save(height=y + 10)
