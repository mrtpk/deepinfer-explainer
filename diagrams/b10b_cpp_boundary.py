"""Diagram: how csrc/ becomes deepinfer._C, what is inside it, and what one call does at the boundary.

Used by: src/concepts/python-cpp-boundary.html
Sources (commit 9bd9cf2):
  setup.py:22-34, 38-72                    COMMON_SOURCES, CUDAExtension / NpuExtension "deepinfer._C"
  scripts/build.sh:11-14, 18-30            platform tag, build folder, symlinks into deepinfer/_so/<tag>/
  deepinfer/__init__.py:9-32               _so_platform_tag(), __path__.append
  csrc/pybind.cpp:7-16                     three submodules
  deepinfer/_C/*.pyi                       names per submodule (3 / 34 / 3)
  csrc/engine/pybind_scheduler.cpp:97-99   schedule binding
  csrc/engine/scheduler.hpp:275-277        GIL release, block-manager locks
  csrc/engine/pybind_scheduler.cpp:31-62   borrowed NumPy views
  deepinfer/engine/llm_engine.py:885-887   the caller
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, INK, MUTE, TEAL, VIOLET, Diagram  # noqa: E402

d = Diagram(width=1100)
d.header(
    "Python and C++: build, contents, and one call",
    "csrc/ -> deepinfer._C (pybind11)  ·  one .so per platform  ·  commit 9bd9cf2",
    params="tag = <DEEPINFER_ACCELERATOR>-<uname -m>, for example nvidia-x86_64 or ascend-aarch64",
)

# ---------------------------------------------------------------------------
# Panel 1: build and import
# ---------------------------------------------------------------------------
y0 = 112
BW, BH, GAP = 316, 150, 30
P1_H = 72 + BH + 24
d.panel(y0, P1_H, 1, "How does csrc/ become an importable module?",
        "One build per platform. Each build goes to its own folder, so NVIDIA and Ascend builds can share one source tree.")
by = y0 + 72
boxes = [
    ("1. setup.py", VIOLET, [
        "11 COMMON_SOURCES",
        "+ cuda_utils.cpp, graph_timer_cuda.cpp",
        "  or asc_utils.cpp, graph_timer_asc.cpp",
        "CUDAExtension | NpuExtension",
        "  name=\"deepinfer._C\"",
        "setup.py:22-72",
    ]),
    ("2. scripts/build.sh", VIOLET, [
        "python setup.py build",
        "  --build-base build/<tag>",
        "ln -fs each *.so into",
        "  deepinfer/_so/<tag>/",
        "no .so linked -> exit 1",
        "build.sh:11-30",
    ]),
    ("3. import deepinfer", BLUE, [
        "_so_platform_tag() -> <tag>",
        "__path__.append(_so/<tag>)",
        "import deepinfer._C finds",
        "  _C.<soabi>.so in that folder",
        "never imports torch here",
        "__init__.py:9-32",
    ]),
]
for i, (title, col, lines) in enumerate(boxes):
    bx = 46 + i * (BW + GAP)
    d.rect(bx, by, BW, BH, fill=col[1], stroke=col, sw=1.5)
    d.text(bx + 14, by + 24, title, 14, col[0], "bold")
    for j, s in enumerate(lines):
        last = j == len(lines) - 1
        d.text(bx + 14, by + 48 + j * 17, s, 11.5 if last else 12, MUTE if last else INK, mono=True)
    if i < 2:
        ax = bx + BW
        d.arrow(ax, by + BH / 2, ax + GAP - 2, by + BH / 2, INK)

# ---------------------------------------------------------------------------
# Panel 2: the three submodules
# ---------------------------------------------------------------------------
y1 = y0 + P1_H + 20
BH2 = 150
P2_H = 72 + BH2 + 24
d.panel(y1, P2_H, 2, "What is inside deepinfer._C?",
        "csrc/pybind.cpp makes three submodules. Each has a type stub in deepinfer/_C/.")
by = y1 + 72
subs = [
    ("_C.cuda_utils (3 names)", TEAL, [
        "alloc_tensor(size)",
        "export_ipc_tensor(ptr, nbytes)",
        "import_ipc_tensor(data)",
        "users: cache_engine.py,",
        "  utils.CudaIPCWrapper",
        "cuda_utils.cpp | asc_utils.cpp",
    ]),
    ("_C.engine (34 names)", TEAL, [
        "Scheduler, BlockManager,",
        "Sequence, SequenceMetadata,",
        "RequestOutputPool, prepare_*",
        "users: llm_engine.py,",
        "  worker/, sequence.py ...",
        "csrc/engine/pybind_*.cpp",
    ]),
    ("_C.graph_timer (3 names)", TEAL, [
        "EventHandle",
        "EventRecordNodeHandle",
        "GraphHandle",
        "users: timer.py,",
        "  cuda_graph_runner.py",
        "graph_timer/pybind.cpp",
    ]),
]
for i, (title, col, lines) in enumerate(subs):
    bx = 46 + i * (BW + GAP)
    d.rect(bx, by, BW, BH2, fill=col[1], stroke=col, sw=1.5)
    d.text(bx + 14, by + 24, title, 14, col[0], "bold", mono=True)
    for j, s in enumerate(lines):
        last = j == len(lines) - 1
        d.text(bx + 14, by + 48 + j * 17, s, 11.5 if last else 12, MUTE if last else INK, mono=True)

# ---------------------------------------------------------------------------
# Panel 3: one call
# ---------------------------------------------------------------------------
y2 = y1 + P2_H + 20
steps = [
    ("Python: the engine calls the scheduler", "self.scheduler.schedule(self.sequence_metadata_pool)", "llm_engine.py:885-887", BLUE),
    ("pybind11: find the C++ method, convert the argument", ".def(\"schedule\", &Scheduler::schedule, ...)", "pybind_scheduler.cpp:97-99", VIOLET),
    ("C++: release the GIL, then lock the block managers", "py::gil_scoped_release; BlockManagerMutexAcquire", "scheduler.hpp:276-277", TEAL),
    ("C++ -> Python: return (list, SchedulerOutputs)", "metadata from the pool; clone_* and zero_states arrays borrow C++ memory", "pybind_scheduler.cpp:31-62", AMBER),
]
CARD_H, CARD_GAP = 50, 12
P3_H = 72 + len(steps) * (CARD_H + CARD_GAP) - CARD_GAP + 22
d.panel(y2, P3_H, 3, "What happens during one call?",
        "Other Python threads can run while C++ plans the step. Some results are views into C++ memory, not copies.")
cy = y2 + 72
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

y = y2 + P3_H + 22
d.legend(30, y, [(VIOLET, "build / binding"), (BLUE, "Python"), (TEAL, "C++ code in deepinfer._C"),
                 (AMBER, "results that borrow C++ memory")])
y += 38
y = d.footnotes(30, y, [
    "11 common sources = csrc/pybind.cpp, 9 files in csrc/engine/ and csrc/graph_timer/pybind.cpp (setup.py:22-34).",
    "Not shown: the 34 engine names one by one (see the engine.pyi page) and the CUDA/ACL calls inside cuda_utils.",
])
d.save(height=y + 10)
