"""Diagram: Tour 1 overview, part A (stops 1-6): from llm.generate() to a scheduled batch.

Used by: src/tours/life-of-a-request.html
Sources (commit 9bd9cf2):
  examples/offline_inference.py:95-101          llm.generate(...)
  examples/_launch.py:15-50                    launch_dp / run_dp (spawn one process per DP rank)
  deepinfer/entrypoints/llm.py:90-166            generate(), _add_request(), tokenizer.encode
  deepinfer/hugging_face/tokenizer.py:25-28      BOS id 0
  deepinfer/engine/llm_engine.py:553-631         add_request(): checks, Sequence, _enqueue
  deepinfer/ve/multimodal_processor.py:248-303   multimodal worker -> set_schedulable
  deepinfer/structure_output/so_matcher_builder.py:97-121  SO builder submit/pump
  csrc/engine/scheduler.hpp:275-345              _schedule(): prefill/decode vote
  csrc/engine/scheduler.hpp:351-554              _schedule_prefill()
  csrc/engine/scheduler.hpp:667-736              schedule() -> SequenceMetadata list
  csrc/engine/input_metadata/prepare_tensor_input_base.cpp:65-140  positions, input_ids
  deepinfer/worker/model_runner.py:120-214       _prepare_input -> InputMetadataV4
Example values (prompt length 41, block 2) are illustrative.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, INK, MUTE, VIOLET, Diagram  # noqa: E402

d = Diagram()
d.header(
    "Life of a request, part 1: from llm.generate() to a batch",
    "Stops 1-6 of the tour  ·  one text request, id \"1\", from examples/offline_inference.py  ·  commit 9bd9cf2",
    params="block_size 128   max_num_seqs 4   max_num_batched_tokens 32768   prompt 41 tokens (illustrative)",
)

LANES = [
    (30, 470, BLUE, "Python  ·  driver process", ["deepinfer/entrypoints, engine, worker", "one process per DP rank"]),
    (520, 470, VIOLET, "C++ engine  ·  deepinfer._C", ["csrc/engine/*  (pybind11)", "same process, GIL released"]),
    (1010, 460, AMBER, "Helpers  ·  other processes, threads", ["only when the request needs them", "or when there are many ranks"]),
]
LANE_Y = 112
HEADER_H = 64
ROW_Y0 = LANE_Y + HEADER_H + 22
ROW_PITCH = 112
BOX_H = 80


def lane_x(i):
    return LANES[i][0] + 14


def lane_w(i):
    return LANES[i][1] - 28


def main_box(lane, row, num, title, lines):
    x, y, w = lane_x(lane), ROW_Y0 + row * ROW_PITCH, lane_w(lane)
    col = LANES[lane][2]
    d.rect(x, y, w, BOX_H, fill=col[1], stroke=col, sw=1.5)
    d.badge(x + 22, y + 22, num, col, r=12, size=13)
    d.text(x + 42, y + 27, title, 15, INK, "bold")
    for i, s in enumerate(lines):
        d.text(x + 16, y + 50 + i * 18, s, 13, INK, mono=True)
    return x, y, w


def side_box(lane, row, title, lines, h=BOX_H):
    x, y, w = lane_x(lane), ROW_Y0 + row * ROW_PITCH, lane_w(lane)
    col = LANES[lane][2]
    d.rect(x, y, w, h, fill="#ffffff", stroke=col, sw=1.3, dash="4 3")
    d.text(x + 14, y + 24, title, 14, col, "bold")
    for i, s in enumerate(lines):
        d.text(x + 14, y + 47 + i * 18, s, 13, INK, mono=True)
    return x, y, w


def flow(src_lane, src_row, dst_lane, dst_row, col=INK):
    """Orthogonal arrow from the bottom of one main box to the top of the next."""
    sx = lane_x(src_lane) + lane_w(src_lane) / 2
    dx = lane_x(dst_lane) + lane_w(dst_lane) / 2
    sy = ROW_Y0 + src_row * ROW_PITCH + BOX_H
    dy = ROW_Y0 + dst_row * ROW_PITCH - 2
    if abs(sx - dx) < 1:
        d.arrow(sx, sy, dx, dy, col, sw=1.8)
    else:
        my = (sy + dy) / 2
        d.path_arrow(f"M {sx:.1f},{sy:.1f} L {sx:.1f},{my:.1f} L {dx:.1f},{my:.1f} L {dx:.1f},{dy:.1f}", col, sw=1.8)


def link(src_lane, dst_lane, row, label=None, col=MUTE):
    """Dashed horizontal link between two boxes in the same row (src right edge -> dst left edge, or reverse)."""
    y = ROW_Y0 + row * ROW_PITCH + BOX_H / 2
    if src_lane < dst_lane:
        x1, x2 = lane_x(src_lane) + lane_w(src_lane), lane_x(dst_lane) - 2
    else:
        x1, x2 = lane_x(src_lane), lane_x(dst_lane) + lane_w(dst_lane) + 2
    d.arrow(x1, y, x2, y, col, sw=1.6, dash="5 4")
    if label:
        d.arrow_label((x1 + x2) / 2, y, label, col)


N_ROWS = 6
lane_h = HEADER_H + 22 + N_ROWS * ROW_PITCH - (ROW_PITCH - BOX_H) + 22
for x, w, col, name, details in LANES:
    d.lane(x, LANE_Y, w, lane_h, col, name, details)

# Row 0 - stop 1
main_box(0, 0, 1, "User script", ["offline_inference.py:95", "llm.generate(prompts, params)"])
side_box(2, 0, "Launcher process", ["launch_dp() -> run_dp()", "spawn 1 process per DP rank"])
link(2, 0, 0, None, AMBER)

# Row 1 - stop 2
main_box(0, 1, 2, "LLM.generate() -> _add_request()", ["deepcopy(SamplingParams)", 'request_id = "1"  (Counter)'])
flow(0, 0, 0, 1)

# Row 2 - stop 3
main_box(0, 2, 3, "Tokenize", ["tokenizer.encode(prompt)", "-> int32 [41]  [0, ...]  BOS = 0"])
flow(0, 1, 0, 2)

# Row 3 - stop 4
main_box(0, 3, 4, "LLMEngine.add_request()", ["check: size > 0, 0 <= id < vocab", "-> C++ Sequence, then _enqueue()"])
side_box(1, 3, "Scheduler.waiting  (deque)", ["Sequence  status WAITING", "schedulable: False if VL model"])
side_box(2, 3, "Helpers, when needed", ["VL model: multimodal worker", "so_args: SO builder threads"])
link(0, 1, 3, None, VIOLET)
link(2, 1, 3, None, AMBER)
flow(0, 2, 0, 3)

# Row 4 - stop 5
main_box(1, 4, 5, "Scheduler::_schedule()", ["vote: prefill step or decode step", "_schedule_prefill(): blocks [2]"])
side_box(2, 4, "DP group all-reduce", ["all DP ranks take the same", "step type (prefill or decode)"])
link(2, 1, 4, None, AMBER)
flow(0, 3, 1, 4, VIOLET)

# Row 5 - stop 6
main_box(1, 5, 6, "schedule() + prepare_prompt_v4()", ["SequenceMetadata q=41 k=41", "positions 0..40, input_ids, slots"])
side_box(0, 5, "ModelRunner._prepare_input()", ["dict of pinned tensors", "-> InputMetadataV4(VL), .cuda()"])
link(1, 0, 5, None, BLUE)
flow(1, 4, 1, 5, VIOLET)

y = LANE_Y + lane_h + 22
d.callout(30, y, 1440, "Next:", "stop 7 (part 2): Worker.execute_model_step() runs the batch on the device.", BLUE)
y += 54
d.legend(30, y, [(BLUE, "Python code in the driver process"), (VIOLET, "C++ engine (deepinfer._C)"),
                 (AMBER, "other processes and threads")])
y += 38
y = d.footnotes(30, y, [
    "Solid arrows: the path of request \"1\". Dashed boxes and arrows: a side object or helper of that stop.",
    "Simplified: the example sends 5 x (dp_rank + 1) prompts on each DP rank (5 on rank 0); a prefill step can batch up to max_num_seqs = 4 of them.",
    "Values 41, [2] and the token ids are illustrative. Sources: see the docstring of diagrams/tour1_map_a.py.",
])
d.save(height=y + 10)
