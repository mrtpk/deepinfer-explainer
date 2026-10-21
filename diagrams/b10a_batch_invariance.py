"""Diagram: why batch composition changes floating-point results, and what DeepInfer switches on.

Used by: src/concepts/determinism.html ("The picture")
Sources (commit 9bd9cf2):
  deepinfer/worker/runtime_config.py:61-69        assert off on NPU; deep_gemm + tile_kernels deterministic
  deepinfer/model_executor/models/v4_modules/attn.py:87-92, 660-667   fused path choice; batch_invariant flag
  deepinfer/model_executor/layers/attention_backend.py:107-121, 125-142  fused path has no flag; FlashMLA gets enable_batch_invariant
  deepinfer/model_executor/parallel_utils/userbuffer.py:79   allow_multiple_reduction off with BI + EPLB rearrangement
  README.md:27-28                                  recipes
  deepinfer/model_executor/layers/tilelang_ops/schedule_mtp_varlen.py:70-98   shared budget, global ranking (PyTorch reference of the kernel)
  deepinfer/model_executor/layers/tilelang_ops/random_sampling.py:17-20, 76-81   draw = hash(seq_seed, position, case)
Panel 1 numbers: BF16 sums, computed by hand (8 significant bits: 257 is not a BF16 value).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, PINK, VIOLET, Diagram  # noqa: E402

d = Diagram(width=1100)
W = d.W

d.header(
    "Determinism: same request, same bits, any batch",
    "Floating-point sums depend on their order  ·  kernels pick an order from the batch  ·  DeepInfer can fix the order",
    params="DEEPINFER_BATCH_INVARIANT=1 (NVIDIA only)  ·  + DEEPINFER_ENABLE_MTP_VARLEN=0 + fixed seq_seed = deterministic sampling",
)

# ---------------------------------------------------------------- panel 1
y0 = 112
P1 = 232
d.panel(y0, P1, 1, "Why can a batch change the bits? Rounding happens after each addition",
        "Example in BF16 (8 significant bits). The same three numbers give 256 or 258, by the order of the sums.")

bw, bh = 300, 104
by = y0 + 72
d.box(46, by, bw, bh, "Order A: left to right", [
    "(256 + 1) + 1", "256 + 1 = 257 → rounds to 256", "256 + 1 = 257 → rounds to 256", "result: 256"], col=BLUE)
d.box(400, by, bw, bh, "Order B: pairs first", [
    "256 + (1 + 1)", "1 + 1 = 2 (exact)", "256 + 2 = 258 (exact)", "result: 258"], col=PINK)
d.box(754, by, bw, bh, "Where the order comes from", [
    "a kernel splits a long sum", "into parts by the batch size", "alone: 4 parts · in a batch: 1", "→ other order, other bits"], col=AMBER)
d.text(46, by + bh + 30, "A difference in the last bit of one logit can change a sampled token. After that token, the two runs differ completely.",
       12, MUTE, italic=True)

# ---------------------------------------------------------------- panel 2
y1 = y0 + P1 + 20
P2 = 212
d.panel(y1, P2, 2, "What does DEEPINFER_BATCH_INVARIANT=1 change? Three switches",
        "Also read: the fused-path choice of a PROMPT engine (attn.py:89). On Ascend, an assert stops the worker if the variable is on.")

by2 = y1 + 72
bh2 = 106
d.box(46, by2, bw, bh2, "Deterministic GEMM kernels", [
    "deep_gemm.use_deterministic_", "  algorithms(True)", "tile_kernels: the same call", "runtime_config.py:67-69"], col=VIOLET)
d.box(400, by2, bw, bh2, "Batch-invariant decode attention", [
    "FlashMLA enable_batch_invariant", "non-fused path only (NORMAL", "engine: dense packed-KV layers)", "attention_backend.py:141"], col=VIOLET)
d.box(754, by2, bw, bh2, "DeepEP buffer (with EPLB moves)", [
    "DeepEP buffer:", "allow_multiple_reduction = False", "only if rearrangement is on", "userbuffer.py:79"], col=VIOLET)

# ---------------------------------------------------------------- panel 3
y2 = y1 + P2 + 20
P3 = 206
d.panel(y2, P3, 3, "Deterministic sampling needs two more settings (README.md:28)",
        "Batch invariance fixes the logits. The random draw and the number of verified drafts must not depend on the batch.")

by3 = y2 + 72
bh3 = 100
d.box(46, by3, bw, bh3, "fixed logits", [
    "DEEPINFER_BATCH_INVARIANT=1", "same request → same", "logits in any batch", "panel 2"], col=VIOLET)
d.box(400, by3, bw, bh3, "fixed random numbers", [
    "SamplingParams(seq_seed=…)", "u = hash(seed, 3·pos + case)", "no row index, no batch size", "random_sampling.py:76-81"], col=EMERALD)
d.box(754, by3, bw, bh3, "fixed number of drafts", [
    "DEEPINFER_ENABLE_MTP_VARLEN=0", "varlen ranks all drafts of", "the batch in one budget", "schedule_mtp_varlen.py:70-98"], col=EMERALD)
d.text(46 + bw + 27, by3 + bh3 / 2 + 6, "+", 20, INK, "bold", "middle")
d.text(400 + bw + 27, by3 + bh3 / 2 + 6, "+", 20, INK, "bold", "middle")

y = y2 + P3 + 22
d.legend(30, y, [(BLUE, "one order of sums"), (PINK, "another order"), (AMBER, "cause"), (VIOLET, "batch-invariance switch"),
                 (EMERALD, "sampling setting")])
y += 36
y = d.footnotes(30, y, [
    "Simplified: what each library does inside its kernels is not in this repository; the diagram shows only the switches DeepInfer sets.",
    "Panel 1 is a general example, not a DeepInfer kernel. Real kernels sum thousands of FP32 products.",
])
d.save(height=y + 10)
