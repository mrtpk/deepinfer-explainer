"""Diagram: how the top-level folders of DeepInfer depend on each other.

Used by: src/code/index.html (section "How the folders depend on each other")
Sources (commit 9bd9cf2):
  examples/_config.py:108-110                  examples -> deepinfer (create_llm imports deepinfer.entrypoints.llm)
  examples/offline_inference.py:8              examples -> deep_cluster
  eval/run_eval.py, eval/*/bench.py            eval -> examples._config / examples._launch
  tests/models/test_sampler.py:23              tests -> examples._config
  tests/conftest.py                            tests -> deepinfer
  deepinfer/engine/llm_engine.py:17-31         deepinfer -> deep_cluster, deepinfer._C
  deepinfer/model_executor/models/v4_modules/mlp.py etc.  deepinfer -> deep_ep / deep_gemm / flash_mla / deep_select
  requirements.txt:16-17                       tilelang==0.1.15, tile-kernels==2.1.0 (pip, not submodules)
  .gitmodules                                  six vendor submodules
  build.sh:13-25                               requirements -> build_vendor.sh -> scripts/build.sh
  scripts/build_vendor.sh:7-53                 builds vendor wheels
  scripts/build.sh:11-29                       setup.py build -> deepinfer/_so/<accelerator>-<arch>/
  setup.py:10,22-34,87-89                      setup.py uses deep_cluster; csrc -> deepinfer._C
Counts measured with find/wc at 9bd9cf2 (see src/code/index.html).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, INK, MUTE, NEUTRAL, VIOLET, WHITE, Diagram  # noqa: E402

d = Diagram(width=1100)
W = d.W
CX = W / 2
d.header(
    "How the folders of DeepInfer depend on each other",
    "Arrows point from the code that imports to the code that it imports  ·  commit 9bd9cf2",
    params="342 files  ·  63,629 text lines  ·  vendor/ = 6 git submodules, not checked out",
)

TS = 15      # box title size
MS = 13      # mono line size


def fbox(x, y, w, h, title, lines, col, dash=None, tcol=None, mono_first=False):
    d.rect(x, y, w, h, fill=col[1] if isinstance(col, tuple) else WHITE, stroke=col, sw=1.5, dash=dash)
    d.text(x + w / 2, y + 26, title, TS, tcol or (col[0] if isinstance(col, tuple) else col), "bold", "middle", mono=True)
    for i, s in enumerate(lines):
        d.text(x + w / 2, y + 50 + i * 19, s, MS, INK, anchor="middle", mono=(mono_first and i == 0))


# ============================================================================
# Panel 1: imports
# ============================================================================
y0 = 120
P1_H = 504
d.panel(y0, P1_H, 1, "Which folder uses which?",
        "deepinfer/ is the centre. It never imports examples/, eval/ or tests/. Kernels come from outside the repo.")

# column geometry: 3 boxes side by side
cw = 300
gx = [46, 400, 754]
row1 = y0 + 78
bh = 86

fbox(gx[0], row1, cw, bh, "eval/", ["17 files  ·  2,003 lines", "benchmarks: AIME, GPQA, HLE"], BLUE, mono_first=True)
fbox(gx[1], row1, cw, bh, "examples/", ["18 files  ·  3,286 lines", "offline_inference.py, benchmark.py"], BLUE, mono_first=True)
fbox(gx[2], row1, cw, bh, "tests/", ["20 files  ·  3,207 lines", "pytest: engine, models, worker"], BLUE, mono_first=True)

# eval -> examples, tests -> examples (horizontal, between neighbours)
ay = row1 + 40
d.arrow(gx[0] + cw, ay, gx[1] - 2, ay, INK)
d.text((gx[0] + cw + gx[1]) / 2, ay - 8, "uses", 12, INK, "bold", "middle")
d.arrow(gx[2], ay, gx[1] + cw + 2, ay, INK)
d.text((gx[1] + cw + gx[2]) / 2, ay - 8, "uses", 12, INK, "bold", "middle")

# deepinfer centre box
row2 = row1 + bh + 58
mid_h = 104
d.rect(46, row2, W - 92, mid_h, fill=BLUE[1], stroke=BLUE, sw=2)
d.text(CX, row2 + 28, "deepinfer/   (the Python package)", 17, BLUE[0], "bold", "middle", mono=True)
d.text(CX, row2 + 52, "223 files  ·  47,174 lines", MS, INK, anchor="middle", mono=True)
d.text(CX, row2 + 74, "entrypoints/ → engine/ → worker/ → model_executor/   + hugging_face/, ve/, structure_output/, npu_ops/ ...", MS, INK, anchor="middle", mono=True)
d.text(CX, row2 + 94, "the only import of the C++ code is the extension module deepinfer._C", 12.5, MUTE, anchor="middle")

for x in gx:
    d.arrow(x + cw / 2, row1 + bh, x + cw / 2, row2 - 2, INK)
d.text(gx[0] + cw / 2 + 10, row1 + bh + 34, "imports", 12, INK, "bold")
d.text(gx[1] + cw / 2 + 10, row1 + bh + 34, "imports", 12, INK, "bold")
d.text(gx[2] + cw / 2 + 10, row1 + bh + 34, "imports", 12, INK, "bold")

# bottom row
row3 = row2 + mid_h + 58
bh3 = 106
fbox(gx[0], row3, cw, bh3, "csrc/  →  deepinfer._C", ["33 C++ files  ·  5,908 lines", "scheduler, block manager, ZOS,", "input metadata, outputs (pybind11)"], VIOLET, mono_first=True)
fbox(gx[1], row3, cw, bh3, "deep_cluster/", ["8 files  ·  656 lines", "finds GPUs or NPUs from device files,", "binds NUMA nodes; no torch import"], BLUE, mono_first=True)
fbox(gx[2], row3, cw, bh3, "kernel libraries", ["vendor/: DeepEP, DeepGEMM, FlashMLA,", "DeepSelect (+ 2 Ascend versions)", "pip: tilelang 0.1.15, tile-kernels 2.1.0"], NEUTRAL, dash="5 4", tcol=INK)
for x in gx:
    d.arrow(x + cw / 2, row2 + mid_h, x + cw / 2, row3 - 2, INK)
d.text(gx[0] + cw / 2 + 10, row2 + mid_h + 34, "imports the built module", 12, INK, "bold")
d.text(gx[1] + cw / 2 + 10, row2 + mid_h + 34, "imports", 12, INK, "bold")
d.text(gx[2] + cw / 2 + 10, row2 + mid_h + 34, "imports (86 files)", 12, INK, "bold")

# ============================================================================
# Panel 2: build
# ============================================================================
y1 = y0 + P1_H + 20
P2_H = 226
d.panel(y1, P2_H, 2, "How does the compiled code get there?",
        "./build.sh runs three steps. Only step 3 compiles code from this repo.")
r = y1 + 76
bh2 = 104
steps = [
    ("1  pip install", ["requirements-<accelerator>.txt", "torch, tilelang, tile-kernels,", "transformers, xgrammar ..."]),
    ("2  scripts/build_vendor.sh", ["git submodule update --init", "build 4 vendor wheels", "for CUDA or ASCEND, then install"]),
    ("3  scripts/build.sh build", ["python setup.py build (csrc/)", "link the .so files into", "deepinfer/_so/<accelerator>-<arch>/"]),
]
for i, (t, ls) in enumerate(steps):
    fbox(gx[i], r, cw, bh2, t, ls, AMBER, mono_first=True)
for i in range(2):
    d.arrow(gx[i] + cw, r + bh2 / 2, gx[i + 1] - 2, r + bh2 / 2, AMBER)
d.text(CX, r + bh2 + 30, "setup.py asks deep_cluster for the accelerator kind, then builds a CUDAExtension or an NpuExtension.",
       12.5, MUTE, anchor="middle")

y = y1 + P2_H + 26
d.legend(30, y, [(BLUE, "Python code in this repo"), (VIOLET, "C++ code in this repo"),
                 (NEUTRAL, "code not in this repo"), (AMBER, "build step")])
y += 40
y = d.footnotes(30, y, [
    "Not shown: doc/ (5 files: the deployment Q&A and 4 images) and scripts/format_csrc.sh, scripts/gen_stub.sh.",
    "Line counts are text lines (wc -l). Binary files (images) count as files with 0 lines.",
])
d.save(height=y + 10)
