"""Diagram: Tour 1 overview, part B (stops 7-13): one engine step on the device, and back to the user.

Used by: src/tours/life-of-a-request.html
Sources (commit 9bd9cf2):
  deepinfer/worker/worker.py:88-189              execute_model_step(): forward N, post-process N-1, sample N
  deepinfer/worker/model_runner.py:307-367       execute_main_model() (graph replay or eager), execute_sample()
  deepinfer/model_executor/models/deepseek.py:154-248   DeepseekModel.forward
  csrc/engine/input_metadata/prepare_tensor_input_v4.cpp:26-127  slot_mapping_store_ca / _swa
  deepinfer/model_executor/layers/sampler.py:114-299    Sampler.forward (prefill / decode)
  deepinfer/model_executor/models/mtp/dflash.py:279-387 DFlash drafts, MTP info pool
  deepinfer/engine/llm_engine.py:686-785, 984-1015      post_process, _process_model_outputs
  csrc/engine/scheduler.hpp:872-1052, 1196-1262          process_outputs, _check_stop, process_MTPInfo
  csrc/engine/outputs.hpp:94-308                 build_request_outputs, RequestOutputPool
  deepinfer/entrypoints/llm.py:168-195           _run_engine(): clone, sort, decode
Example values are illustrative (prompt 41 tokens, block 2, state slot 2, nextn 5).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import BLUE, EMERALD, INK, MUTE, VIOLET, Diagram, text_width  # noqa: E402


def wrap(lines, size=12, max_w=1030):
    """Re-break footnote lines at word boundaries so each fits max_w; continuation lines indent 2 spaces."""
    out = []
    for line in lines:
        cur = ""
        for word in line.split(" "):
            cand = word if not cur else cur + " " + word
            if cur and text_width(cand, size) > max_w:
                out.append(cur)
                cur = "  " + word
            else:
                cur = cand
        out.append(cur)
    return out


d = Diagram(width=1100)
d.header(
    "Life of a request, part 2: one engine step, and back to the user",
    "Stops 7-13 of the tour  ·  request \"1\"  ·  ZOS on (default for the NORMAL engine)  ·  commit 9bd9cf2",
    params="nextn 5 drafts   decode seqlen_q 1 + 5 = 6   CUDA graph sizes 1 2 4 8 16 24   vocab 129280 (inferred)",
)

LANES = [
    (30, 336, BLUE, "Python  ·  worker and engine", ["deepinfer/worker, engine, entrypoints", "driver process (CP rank 0)"]),
    (382, 336, VIOLET, "C++ engine  ·  deepinfer._C", ["csrc/engine/*", "scheduler state, output objects"]),
    (734, 336, EMERALD, "Device  ·  GPU or NPU", ["kernels launched by Python", "no CPU sync inside forward / sample"]),
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


def side_box(lane, row, title, lines):
    x, y, w = lane_x(lane), ROW_Y0 + row * ROW_PITCH, lane_w(lane)
    col = LANES[lane][2]
    d.rect(x, y, w, BOX_H, fill="#ffffff", stroke=col, sw=1.3, dash="4 3")
    d.text(x + 14, y + 24, title, 14, col, "bold")
    for i, s in enumerate(lines):
        d.text(x + 14, y + 47 + i * 18, s, 13, INK, mono=True)


def flow(src_lane, src_row, dst_lane, dst_row, col=INK):
    sx = lane_x(src_lane) + lane_w(src_lane) / 2
    dx = lane_x(dst_lane) + lane_w(dst_lane) / 2
    sy = ROW_Y0 + src_row * ROW_PITCH + BOX_H
    dy = ROW_Y0 + dst_row * ROW_PITCH - 2
    if abs(sx - dx) < 1:
        d.arrow(sx, sy, dx, dy, col, sw=1.8)
    else:
        my = (sy + dy) / 2
        d.path_arrow(f"M {sx:.1f},{sy:.1f} L {sx:.1f},{my:.1f} L {dx:.1f},{my:.1f} L {dx:.1f},{dy:.1f}", col, sw=1.8)


def link(src_lane, dst_lane, row, col=MUTE):
    y = ROW_Y0 + row * ROW_PITCH + BOX_H / 2
    if src_lane < dst_lane:
        x1, x2 = lane_x(src_lane) + lane_w(src_lane), lane_x(dst_lane) - 2
    else:
        x1, x2 = lane_x(src_lane), lane_x(dst_lane) + lane_w(dst_lane) + 2
    d.arrow(x1, y, x2, y, col, sw=1.6, dash="5 4")


N_ROWS = 7
lane_h = HEADER_H + 22 + N_ROWS * ROW_PITCH - (ROW_PITCH - BOX_H) + 22
for x, w, col, name, details in LANES:
    d.lane(x, LANE_Y, w, lane_h, col, name, details)

# Row 0 - stop 7
main_box(0, 0, 7, "Worker.execute_model_step()", ["forward N -> post-process N-1", "-> sample N -> keep N for later"])

# Row 1 - stop 8
main_box(2, 1, 8, "Forward pass", ["decode: CUDA graph replay (size 8)", "embed -> decoder layers -> norm"])
side_box(0, 1, "ModelRunner.execute_main_model()", ["prefill: eager self.model(...)", "decode: cuda_graph_runner.replay"])
link(0, 2, 1, EMERALD)
flow(0, 0, 2, 1, EMERALD)

# Row 2 - stop 9
main_box(2, 2, 9, "KV cache writes", ["C1/C2 entries -> paged block 2", "last window -> SWA ring, slot 2"])
side_box(1, 2, "Slot maps from stop 6", ["slot_mapping_store_ca[ratio]", "slot_mapping_store_swa"])
link(1, 2, 2, VIOLET)
flow(2, 1, 2, 2, EMERALD)

# Row 3 - stop 10
main_box(2, 3, 10, "Sampling", ["logits = hidden x lm_head (fp32)", "prefill: last row  decode: verify"])
side_box(0, 3, "Sampler.forward()", ["via DeepseekForCausalLM.sample", "results copied to CPU (async)"])
link(0, 2, 3, EMERALD)
flow(2, 2, 2, 3, EMERALD)

# Row 4 - stop 11
main_box(2, 4, 11, "Draft tokens (DFlash)", ["decode only: 5 drafts / request", "-> MTP info pool slot, CPU copy"])
flow(2, 3, 2, 4, EMERALD)

# Row 5 - stop 12
main_box(1, 5, 12, "Output assembly", ["process_MTPInfo -> process_outputs", "-> build_request_outputs (ptrs)"])
side_box(0, 5, "LLMEngine.post_process()", ["ZOS decode: during step N+1", "prefill: in the same step"])
link(0, 1, 5, VIOLET)
flow(2, 4, 1, 5, VIOLET)

# Row 6 - stop 13
main_box(0, 6, 13, "Back to the user", ["RequestOutput.clone() per token", "sort by request id -> decode()"])
flow(1, 5, 0, 6, BLUE)

y = LANE_Y + lane_h + 22
d.callout(30, y, d.W - 60, "The loop:", "LLM._run_engine() calls step() again (stop 5) until no request is unfinished; then flush_inflight_reqs().", BLUE)
y += 54
d.legend(30, y, [(BLUE, "Python code"), (VIOLET, "C++ engine (deepinfer._C)"), (EMERALD, "work on the device (kernels)")])
y += 38
y = d.footnotes(30, y, wrap([
    "Graph size 8: one request with seqlen_q 6 uses the smallest captured size >= 6. With 4 requests, total_q is 24.",
    "Simplified: CP worker processes run stops 7-11 too, with inputs broadcast from the driver. Only the driver gets the sampled tokens and builds the outputs.",
    "Values (block 2, slot 2, sizes) are illustrative. Sources: see the docstring of diagrams/tour1_map_b.py.",
]))
d.save(height=y + 10)
