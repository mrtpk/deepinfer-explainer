"""Diagram: the life of one Sequence: statuses, transitions, finish reasons, and the fields it keeps.

Used by: src/concepts/request-lifecycle.html
Sources (commit 9bd9cf2):
  csrc/engine/sequence.hpp:30-64            SequenceStatus values and finish reason strings
  csrc/engine/pybind_sequence.cpp:35        schedulable = multi_modal_data is None
  deepinfer/engine/llm_engine.py:603-604     FINISHED_VE_FAILED at creation (image bytes None)
  deepinfer/engine/llm_engine.py:620-623     FINISHED_SO_FAILED before the queue; add_sequence
  deepinfer/ve/multimodal_processor.py:281-303  fetch() -> set_schedulable
  csrc/engine/scheduler.hpp:360-397          prefill: skip finished, wait if not schedulable, IGNORED if too long
  csrc/engine/scheduler.hpp:513-546          prefill: RUNNING only after the last chunk
  csrc/engine/scheduler.hpp:940-1020         after the step: running, or back to the front of waiting
  csrc/engine/scheduler.hpp:766-790          _preempt: FINISHED_PREEMPTED or WAITING (front)
  csrc/engine/scheduler.hpp:1035-1052        _check_stop: EOS, max_model_len, max_tokens
  csrc/engine/scheduler.hpp:144-163          abort_sequence: FINISHED_ABORTED
  csrc/engine/sequence.hpp:168-321           field groups of Sequence
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, PINK, VIOLET, Diagram  # noqa: E402

d = Diagram(width=1100)
W = d.W
d.header(
    "The life of one Sequence",
    "Statuses of the C++ Sequence and what moves it between them  ·  NORMAL engine  ·  commit 9bd9cf2",
    params="status: SequenceStatus (sequence.hpp:30-41)   queues: Scheduler.waiting (deque), Scheduler.running (vector)",
)

# ============================================================================
# Panel 1: statuses and transitions
# ============================================================================
y0 = 112
P1_H = 520
d.panel(y0, P1_H, 1, "Which status can a sequence have, and what changes it?",
        "WAITING and RUNNING are the live statuses. Every other status is a FINISHED_* value with a reason string.")

bh = 112
ry = y0 + 92
# born
d.box(46, ry, 270, bh, "add_request()", ["C++ Sequence(...)", "status = WAITING", "schedulable =", "  (multi_modal_data is None)", "llm_engine.py:593-631"], col=BLUE, align="start")
# waiting
d.box(400, ry, 290, bh, "WAITING", ["in Scheduler.waiting (deque)", "starts a prefill only if", "  schedulable is true and", "  the step is a prefill step", "scheduler.hpp:360-371"], col=AMBER, align="start")
# running
d.box(780, ry, 274, bh, "RUNNING", ["in Scheduler.running", "decode: 1 + drafts tokens", "tokens appended after", "  each step, then _check_stop", "scheduler.hpp:982-990"], col=EMERALD, align="start")

d.arrow(316, ry + 36, 398, ry + 36, BLUE)
d.arrow_label(357, ry + 36, "enqueue", BLUE)
d.arrow(690, ry + 30, 778, ry + 30, AMBER)
d.arrow_label(734, ry + 30, "last chunk", AMBER)
d.text(734, ry + 48, "of prefill", 11.5, AMBER, "bold", "middle")
# recompute back
d.arrow(780, ry + 86, 692, ry + 86, PINK, dash="5 4")
d.text(736, ry + 78, "recompute", 11.5, PINK, "bold", "middle")
d.text(736, ry + 104, "front of queue", 11.5, PINK, anchor="middle")
# chunk loop under WAITING
lx0, lx1 = 470, 620
d.path_arrow(f"M {lx1},{ry + bh} L {lx1},{ry + bh + 30} L {lx0},{ry + bh + 30} L {lx0},{ry + bh + 2}", AMBER)
d.text(545, ry + bh + 48, "chunk done, more prompt left:", 11.5, AMBER, "bold", "middle")
d.text(545, ry + bh + 64, "back to the FRONT of waiting", 11.5, AMBER, anchor="middle")
# schedulable from the image worker
d.text(46, ry + bh + 30, "multimodal worker: fetch()", 12, VIOLET, "bold")
d.text(46, ry + bh + 47, "-> set_schedulable(id) = true", 12, VIOLET, mono=True)
d.text(46, ry + bh + 64, "multimodal_processor.py:281-303", 11.5, MUTE, mono=True)

# finished states
fy = ry + bh + 104
fh = 172
d.rect(46, fy, W - 92, fh, fill=PINK[1], stroke=PINK, sw=1.4)
d.text(62, fy + 24, "FINISHED_*  (is_finished: status >= FINISHED_STOPPED, sequence.hpp:43)", 13.5, PINK, "bold")
rows = [
    ("FINISHED_STOPPED", '"stop"', "_check_stop: EOS id (unless ignore_eos)", "1038-1041"),
    ("FINISHED_LENGTH_CAPPED", '"length"', "output = max_tokens, or length > max_model_len", "1043-1051"),
    ("FINISHED_PREEMPTED", '"insufficient_system_resource"', "_preempt with stop_preempted_request, or SO", "771-780"),
    ("FINISHED_IGNORED", '"prompt_length_exceeded"', "prompt > prompt_limit, or can NEVER fit", "377-396"),
    ("FINISHED_ABORTED", '"abort"', "abort_request(), in waiting or running", "144-163"),
    ("FINISHED_SO_FAILED / VE_FAILED", '"xgrammar ..." / "ve_error"', "grammar or image error", "sequence.hpp:57-60"),
]
for i, (st, reason, why, src) in enumerate(rows):
    yy = fy + 50 + i * 20
    d.text(62, yy, st, 12, INK, "bold", mono=True)
    d.text(334, yy, reason, 12, PINK, mono=True)
    d.text(588, yy, why, 12, INK)
    d.text(W - 62, yy, src, 11.5, MUTE, anchor="end", mono=True)
# arrows to finished
d.arrow(917, ry + bh, 917, fy - 2, PINK)
d.text(925, ry + bh + 30, "stop, length,", 11.5, PINK, "bold")
d.text(925, ry + bh + 46, "preempt (stop)", 11.5, PINK, "bold")
d.arrow(668, ry + bh, 668, fy - 2, PINK, dash="5 4")
d.text(676, ry + bh + 92, "ignored, aborted", 11.5, PINK, "bold")

# ============================================================================
# Panel 2: what one Sequence keeps
# ============================================================================
y1 = y0 + P1_H + 20
P2_H = 300
d.panel(y1, P2_H, 2, "What does one Sequence keep?",
        "Seven groups of fields (sequence.hpp:313-320). The scheduler reads and writes them; Python sees them through bindings.")
gw, gh = 316, 112
groups = [
    ("request", BLUE, ["seq_id, request_id, user_id", "arrival_time (ms, set by", "  add_sequence)"]),
    ("input", BLUE, ["tokens: prompt + outputs", "compressed_tokens (Engram)", "multi_modal_data"]),
    ("generation", BLUE, ["params (SamplingParams)", "sampling: temperature, top_p ...", "stopping: max_tokens, ignore_eos"]),
    ("cache", EMERALD, ["num_tokens (KV written)", "block_table, state_id", "hit_tokens, swa_valid_start"]),
    ("mtp", EMERALD, ["draft_tokens, accepted_tokens", "info_slot, accept_rates", "schedule_cnt, process_cnt"]),
    ("schedule", AMBER, ["status, schedulable, branch_id", "chunked_rest_len, checkpoints", "total_inflight_tokens"]),
]
for i, (name, col, lines) in enumerate(groups):
    gx = 46 + (i % 3) * (gw + 22)
    gy = y1 + 70 + (i // 3) * gh
    d.box(gx, gy, gw, gh - 18, name, lines, col=col, align="start", mono_size=12)
d.text(46, y1 + P2_H - 18, "Also: structured_output {status, matcher}. Full field table: the module page of sequence.hpp.", 12, MUTE)

y = y1 + P2_H + 24
d.legend(30, y, [(BLUE, "admission, request data"), (AMBER, "waiting, scheduling"), (EMERALD, "running, KV cache"), (PINK, "finished"), (VIOLET, "image worker")])
y += 36
y = d.footnotes(30, y, [
    "SWAPPED exists in the enum but no code sets it: DeepInfer never swaps KV blocks to the CPU.",
    "A finished sequence stays in running until the next decode schedule. Its blocks go back in pre_sampler_sync of that step.",
])
d.save(height=y + 14)
