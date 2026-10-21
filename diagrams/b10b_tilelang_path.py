"""Diagram: one TileLang kernel from the caller to the device, on both backends, and its test.

Used by: src/concepts/tilelang-kernels.html
Sources (commit 9bd9cf2):
  deepinfer/worker/worker.py:220-227                                  caller (ZOS decode, nextn > 0)
  deepinfer/model_executor/layers/tilelang_ops/compute_seqlens_k_zos.py:10-32   interface
  deepinfer/model_executor/layers/tilelang_ops/ops.py:13-32           dispatcher
  deepinfer/model_executor/layers/tilelang_ops/cuda/compute_seqlens_k_zos.py:7-38  CUDA factory
  deepinfer/model_executor/layers/tilelang_ops/asc/compute_seqlens_k_zos.py:8-59   Ascend factory
  deepinfer/worker/runtime_config.py:45-51                            TILELANG_CACHE_DIR
  deepinfer/model_executor/layers/tilelang_ops/compute_seqlens_k_zos.py:35-88   reference + test
  deepinfer/model_executor/layers/tilelang_ops/conftest.py:74-113     collection hook, skip rule
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, TEAL, VIOLET, WHITE, Diagram  # noqa: E402

d = Diagram(width=1100)
d.header(
    "One TileLang kernel, from the caller to the device",
    "Example: compute_seqlens_k_zos  ·  layers/tilelang_ops/  ·  commit 9bd9cf2",
    params="seqlens_k[i] += seqlens_q[i];  if remap[i] = j != -1:  seqlens_k[i] -= nextn - prev_accepted[j]",
)

# ---------------------------------------------------------------------------
# Panel 1: the call path
# ---------------------------------------------------------------------------
y0 = 112
steps = [
    ("caller: Worker, ZOS decode step", "compute_seqlens_k_zos(seqlens_k, seqlens_q, remap, accepted, nextn=self.nextn)",
     "worker.py:220-227", BLUE),
    ("interface file: tilelang_ops/compute_seqlens_k_zos.py", "kernel = ops.compute_seqlens_k_zos_tl(nextn);  kernel(4 tensors)",
     "compute_seqlens_k_zos.py:31-32", TEAL),
    ("dispatcher: tilelang_ops/ops.py (at import)", "import tilelang_ops.<cuda | asc>; copy every public *_tl name into ops",
     "ops.py:15-22", TEAL),
    ("factory: cuda/ or asc/compute_seqlens_k_zos.py", "@tilelang.jit: build and compile the kernel for this nextn",
     "cuda/...:7-38  ·  asc/...:8-59", VIOLET),
    ("device: the compiled kernel runs", "n_seq is dynamic (T.dynamic): one kernel for every batch size",
     "cuda/...:16-17", VIOLET),
]
CARD_H, CARD_GAP = 50, 12
P1_H = 72 + len(steps) * (CARD_H + CARD_GAP) - CARD_GAP + 22
d.panel(y0, P1_H, 1, "Which code runs, in which order?",
        "The interface is the same on both platforms. ops.py decides, once per process, which factory folder it uses.")
cy = y0 + 72
for i, (title, row, cite, col) in enumerate(steps):
    d.rect(46, cy, 1008, CARD_H, fill=col[1], stroke=col, sw=1.4)
    d.rect(46, cy, 6, CARD_H, fill=col[0], stroke=None, rx=3)
    d.badge(70, cy + 17, i + 1, col, r=10, size=11)
    d.text(88, cy + 22, title, 13.5, INK, "bold")
    d.text(88, cy + 40, row, 12, INK, mono=True)
    pw = len(cite) * 11 * 0.602 + 20
    d.pill(1054 - 10 - pw, cy + 8, pw, cite, col[0])
    if i < len(steps) - 1:
        d.arrow(70, cy + CARD_H, 70, cy + CARD_H + CARD_GAP - 2, col)
    cy += CARD_H + CARD_GAP

# ---------------------------------------------------------------------------
# Panel 2: how the two backends split the same work
# ---------------------------------------------------------------------------
y1 = y0 + P1_H + 20
BW, BH = 489, 236
P2_H = 72 + BH + 24
d.panel(y1, P2_H, 2, "How does each backend split the work? (n_seq = 300)",
        "CUDA starts one thread per sequence. Ascend starts one program per vector core, and each program loops over tiles.")
by = y1 + 72
cuda_lines = [
    "T.Kernel(ceildiv(n_seq, 128), threads=128)",
    "grid = ceildiv(300, 128) = 3 blocks",
    "threads = 3 x 128 = 384; 84 do nothing",
    "",
    "thread i:",
    "  T.pdl_sync()       wait for earlier kernel",
    "  sk = seqlens_k[i] + seqlens_q[i]",
    "  if remap[i] != -1:",
    "    sk = sk - nextn + accepted[remap[i]]",
    "  seqlens_k[i] = sk  (in place)",
]
asc_lines = [
    "T.Kernel(C)   C = get_num_vec_cores()",
    "T.Persistent: ceildiv(300, 8) = 38 tiles",
    "  shared by the C programs; 4 stages",
    "",
    "one tile of BR = 8 sequences:",
    "  T.copy 3 inputs x 8 int32 -> UB (32 B each)",
    "  T.SimtVF(threads=8): same formula",
    "  accepted[...] read from device memory",
    "  T.copy 8 results UB -> seqlens_k",
    "last tile: 300 - 37 x 8 = 4 sequences",
]
for i, (title, lines, col) in enumerate((("NVIDIA: cuda/compute_seqlens_k_zos.py", cuda_lines, EMERALD),
                                         ("Ascend: asc/compute_seqlens_k_zos.py", asc_lines, AMBER))):
    bx = 46 + i * (BW + 30)
    d.rect(bx, by, BW, BH, fill=col[1], stroke=col, sw=1.5)
    d.text(bx + 14, by + 24, title, 14, col[0], "bold", mono=True)
    for j, s in enumerate(lines):
        d.text(bx + 14, by + 50 + j * 18, s, 12, INK, mono=True)

# ---------------------------------------------------------------------------
# Panel 3: the test
# ---------------------------------------------------------------------------
y2 = y1 + P2_H + 20
TB_W, TB_H, TGAP = 316, 112, 30
P3_H = 72 + TB_H + 24
d.panel(y2, P3_H, 3, "How is the kernel tested?",
        "The test lives in the interface file. It compares the kernel with a plain PyTorch version on the same random input.")
ty = y2 + 72
tests = [
    ("1. collect", VIOLET, ["conftest.pytest_collect_file", "takes every top-level .py", "that has \"def test_\"", "conftest.py:74-97"]),
    ("2. compare", VIOLET, ["test_compute_seqlens_k_zos", "kernel vs ..._ref (PyTorch)", "torch.equal(...) must hold", "compute_seqlens_k_zos.py:55-88"]),
    ("3. missing kernel", AMBER, ["KernelUnavailableError", "-> pytest.skip off NVIDIA", "-> test error on NVIDIA", "conftest.py:100-113"]),
]
for i, (title, col, lines) in enumerate(tests):
    bx = 46 + i * (TB_W + TGAP)
    d.rect(bx, ty, TB_W, TB_H, fill=col[1], stroke=col, sw=1.5)
    d.text(bx + 14, ty + 22, title, 13.5, col[0], "bold")
    for j, s in enumerate(lines):
        last = j == len(lines) - 1
        d.text(bx + 14, ty + 44 + j * 17, s, 11.5 if last else 12, MUTE if last else INK, mono=True)
    if i < 1:
        ax = bx + TB_W
        d.arrow(ax, ty + TB_H / 2, ax + TGAP - 2, ty + TB_H / 2, INK)

y = y2 + P3_H + 22
d.legend(30, y, [(BLUE, "caller"), (TEAL, "shared Python"), (VIOLET, "factory, kernel, test"),
                 (EMERALD, "NVIDIA only"), (AMBER, "Ascend only")])
y += 38
y = d.footnotes(30, y, [
    "UB = Unified Buffer, the on-chip memory of an Ascend vector core. C, the number of vector cores, comes from tile_kernels at run time.",
    "Not shown: how TileLang compiles and caches kernels inside the library. DEEPINFER_JIT_CACHE_DIR only sets the cache folder",
    "  (TILELANG_CACHE_DIR, runtime_config.py:45-51).",
])
d.save(height=y + 10)
