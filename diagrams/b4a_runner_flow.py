"""Diagram: one step inside ModelRunner on the driver rank and on a context-parallel follower rank.

Used by: src/code/model-runner.html
Sources (commit 9bd9cf2):
  deepinfer/worker/model_runner.py:148-161     _prepare_input: driver or follower
  deepinfer/worker/model_runner.py:171-214     _prepare_input_driver: graph path (select, fill out_dict) or eager path (.cuda), CP broadcast
  deepinfer/worker/model_runner.py:216-230     _prepare_input_follower: receive, select the same graph or rebuild the object
  deepinfer/worker/model_runner.py:307-335     execute_main_model: replay or model(...) inside forbid_cuda_sync
  deepinfer/worker/model_runner.py:232-277     prepare_sampler_inputs: C++ on the driver, broadcast to followers
  deepinfer/worker/model_runner.py:337-367     execute_sample: model.sample(...) inside forbid_cuda_sync
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, PINK, VIOLET, Diagram  # noqa: E402

d = Diagram(width=1100)
W = d.W
d.header(
    "ModelRunner: one step on the driver and on a CP follower",
    "The driver builds the inputs; with context parallelism (CP > 1) the followers receive them  ·  no CPU-device sync",
    params="execute_main_model -> MainModelOutput(model_output, input_metadata, graph_size)   execute_sample -> SamplerOutput",
)

LX, LW = 40, 640
RX, RW = 700, 360

# ============================================================================
# Panel 1: forward
# ============================================================================
y0 = 112
P1_H = 380
d.panel(y0, P1_H, 1, "execute_main_model: where does the input come from?",
        "Decode steps with graphs fill the captured buffers. Prefill steps build a new object and copy it.")
ly = y0 + 66
LH = 258
d.lane(LX, ly, LW, LH, BLUE, "Driver rank (cp_rank 0)", ["has seq_metadata_list"], header_h=50)
d.lane(RX, ly, RW, LH, PINK, "CP follower rank", ["gets only is_prompt, is_placeholder"], header_h=50)

cy = ly + 62
d.step_card(LX + 12, cy, 300, 112, 1, "decode, graphs captured", BLUE, tag="graph",
            rows=[("a", "select(total_q) -> size"), ("b", "add padding sequences"), ("c", "C++ or ZOS kernel fills out_dict"),
                  ("d", "num_reqs = real count")], key_w=20)
d.step_card(LX + 326, cy, 302, 112, 2, "prefill, or no graphs", AMBER, tag="eager",
            rows=[("a", "build tensors (pinned; ZOS: device)"), ("b", "InputMetadataV4(...)"), ("c", ".cuda(non_blocking)"),
                  ("", "")], key_w=20)
by = cy + 126
d.step_card(LX + 12, by, 616, 58, 3, "CP > 1: broadcast_tensor_dict(src=0)", VIOLET, tag="model_runner.py:200",
            rows=[("", "is_prompt, type, run_cuda_graph, total_q, num_reqs  (+ all fields when eager)")], key_w=0)
d.arrow(LX + 162, cy + 114, LX + 162, by - 2, BLUE)
d.arrow(LX + 477, cy + 114, LX + 477, by - 2, AMBER)

d.step_card(RX + 12, cy, RW - 24, 112, 1, "receive", VIOLET, tag="src=0",
            rows=[("a", "pop type, run_cuda_graph"), ("b", "graph: select(total_q)"), ("c", "eager: from_flatten_dict"),
                  ("", "")], key_w=20)
d.path_arrow(f"M {LX + 630},{by + 29} L {RX + RW / 2},{by + 29} L {RX + RW / 2},{cy + 114}", VIOLET, dash="5 4")

ry = ly + LH + 14
d.callout(LX, ry, 1020, "Both ranks:", "replay(graph) or model(kv_caches, input_metadata), inside forbid_cuda_sync()",
          EMERALD, h=30)

# ============================================================================
# Panel 2: sample
# ============================================================================
y1 = y0 + P1_H + 20
P2_H = 156
d.panel(y1, P2_H, 2, "execute_sample: who prepares the sampler inputs?",
        "Only the driver calls C++. Followers get the row indices and run the same sample call without the driver part.")
d.step_card(46, y1 + 66, 470, 66, 1, "driver: prepare_sampler_inputs (C++)", BLUE, tag="prepare_sample.cpp",
            rows=[("", "then broadcast the row indices to the CP group")], key_w=0)
d.arrow(518, y1 + 99, 566, y1 + 99, VIOLET, dash="5 4")
d.step_card(568, y1 + 66, 486, 66, 2, "follower: SamplerInputs(driver=None)", PINK, tag="model_runner.py:271",
            rows=[("", "selected_token_indices, prompt indices, decode part")], key_w=0)

y = y1 + P2_H + 24
d.legend(30, y, [(BLUE, "driver"), (PINK, "CP follower"), (AMBER, "eager path"), (VIOLET, "CP broadcast"),
                 (EMERALD, "both ranks")])
y += 40
y = d.footnotes(30, y, [
    "With cp = 1 (no context parallelism) there is no follower and no broadcast.",
    "Simplified: on the graph path the followers receive the tensor values inside the graph (InputMetadata.broadcast).",
])
d.save(height=y + 14)
