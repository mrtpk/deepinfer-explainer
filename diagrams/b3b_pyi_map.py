"""Diagram: map of deepinfer._C.engine: Python users, the 34 exported names in 5 groups, and the C++ files.

Used by: src/code/engine-pyi.html
Sources (commit 9bd9cf2):
  deepinfer/_C/engine.pyi:8                      __all__: 34 names
  csrc/pybind.cpp:12-13                          submodule "engine"
  csrc/engine/pybind.cpp:5-9                     three registration functions
  csrc/engine/pybind_scheduler.cpp:10-136        group 1
  csrc/engine/pybind_sequence.cpp:50-171         group 2
  csrc/engine/pybind_output.cpp:16-46            group 3
  csrc/engine/pybind_output.cpp:48-75            group 4
  csrc/engine/pybind_output.cpp:76-135           group 5
  Python importers: llm_engine.py:19-31, sequence.py:14-20, entrypoints/llm.py:15, model_metadata_utils.py:6-11,
  sampling_inputs.py:18-27, prepare_tensor_input_zos.py:7, engram.py:18, worker/base.py:22, model_runner.py:15,
  worker.py:16-19, zos_status.py:5
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, PINK, VIOLET, Diagram  # noqa: E402

d = Diagram(width=1100)
W = d.W
d.header(
    "deepinfer._C.engine: who uses what, and where it lives",
    "34 exported names in 5 groups  ·  left: Python importers  ·  right: the C++ binding file and the code",
    params="engine.pyi (735 lines) = output of pybind11-stubgen for the submodule deepinfer._C.engine",
)

groups = [
    (BLUE, "1  Scheduling and blocks (9)",
     ["Scheduler  SchedulerOutputs", "BlockManager  SequenceMetadataPool", "FlopsEstimator  + 4 functions"],
     ["engine/llm_engine.py", "worker/base.py", "worker/model_runner.py", "worker.py  zos_status.py"],
     ["pybind_scheduler.cpp", "scheduler.hpp  block_manager.hpp", "process_output.hpp", "flops_estimator.hpp"]),
    (VIOLET, "2  Sequences and ZOS input (8)",
     ["Sequence  SequenceData  SequenceStatus", "SequenceMetadata  PLACEHOLDER_REQUEST_ID", "encode_compressed  prepare_*zos_inputs"],
     ["sequence.py  worker/worker.py", "prepare_tensor_input_zos.py", "v4_modules/engram.py", "engine/llm_engine.py"],
     ["pybind_sequence.cpp", "sequence.hpp", "zos.hpp  zos.cpp"]),
    (EMERALD, "3  Outputs (3)",
     ["RequestOutput  RequestOutputPool", "build_request_outputs"],
     ["engine/llm_engine.py", "entrypoints/llm.py"],
     ["pybind_output.cpp:16-46", "outputs.hpp"]),
    (AMBER, "4  Input metadata (5)",
     ["PrepareArgs  YocoPrefillTruncationMode", "prepare_prompt_v4  prepare_decode_v4", "set_engram_lookup_table"],
     ["model_metadata_utils.py", "prepare_tensor_input_zos.py", "worker/base.py"],
     ["pybind_output.cpp:48-75", "input_metadata/prepare_tensor_input*", "prepare_tensor_input_v4.cpp"]),
    (PINK, "5  Sampler inputs (9)",
     ["8 classes: SamplerInputs, Driver-,", "Decode-, Prefill-, Speculative-, ...", "prepare_sampler_inputs"],
     ["model_executor/sampling_inputs.py", "worker/model_runner.py"],
     ["pybind_output.cpp:76-135", "prepare_sample.hpp", "prepare_sample.cpp"]),
]

y0 = 112
ROW = 100
P_H = 96 + len(groups) * ROW
d.panel(y0, P_H, 1, "Five groups, three binding files",
        "Each row: the Python files that import the group, the names, and the C++ files that bind and implement them.")
d.text(46, y0 + 78, "Python importers", 12.5, MUTE, "bold")
d.text(330, y0 + 78, "exported names (deepinfer._C.engine)", 12.5, MUTE, "bold")
d.text(770, y0 + 78, "C++: binding file, then code", 12.5, MUTE, "bold")
for i, (col, title, names, py, cpp) in enumerate(groups):
    y = y0 + 90 + i * ROW
    h = ROW - 14
    d.rect(46, y, 250, h, fill="#ffffff", stroke=col, rx=8, sw=1.2)
    for k, s in enumerate(py):
        d.text(58, y + 22 + k * 17, s, 11.5, INK, mono=True)
    d.arrow(298, y + h / 2, 326, y + h / 2, col)
    d.box(330, y, 400, h, title, names, col=col, align="start", mono_size=12)
    d.arrow(732, y + h / 2, 764, y + h / 2, col)
    d.rect(766, y, 288, h, fill="#ffffff", stroke=col, rx=8, sw=1.2)
    for k, s in enumerate(cpp):
        d.text(778, y + 22 + k * 17, s, 11.5, INK, mono=True)

y = y0 + P_H + 24
d.legend(30, y, [(BLUE, "scheduling"), (VIOLET, "sequences"), (EMERALD, "outputs"), (AMBER, "input metadata"),
                 (PINK, "sampler inputs")])
y += 40
y = d.footnotes(30, y, [
    "Arrows mean \"imports\" (left) and \"is bound in / implemented in\" (right). All C++ paths are under csrc/engine/.",
    "Not shown: the sibling submodules deepinfer._C.cuda_utils and deepinfer._C.graph_timer (csrc/pybind.cpp:9-16).",
])
d.save(height=y + 14)
