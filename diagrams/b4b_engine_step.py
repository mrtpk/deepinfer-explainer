"""Diagram: one engine step (decode, ZOS on) in the order of the code, with the step whose data
each phase touches (N or N-1) and the device work that the phase queues.

Used by: src/tours/engine-step.html
Sources (commit 9bd9cf2):
  deepinfer/entrypoints/llm.py:176-182          loop: has_unfinished_requests, step(), clone outputs
  deepinfer/engine/llm_engine.py:881-887        schedule step N (C++)
  deepinfer/engine/llm_engine.py:961-975        _execute_model_async_step -> run_workers("execute_model_step")
  deepinfer/worker/worker.py:116-118, 191-245   _correct_seqlens_qk (remap, H2D, compute_seqlens_k_zos)
  deepinfer/worker/worker.py:121-124            execute_main_model: prepare inputs on the device, replay the graph
  deepinfer/worker/worker.py:143-144, 247-272   post-process N-1: sample_end_evt.synchronize(), engine post_process
  deepinfer/worker/worker.py:146-152            update_metadata_for_sampling_zos (and the d2h_evt wait with DSpark)
  deepinfer/worker/worker.py:154-159            execute_sample: sampler + DFlash, non-blocking copies to the CPU
  deepinfer/worker/worker.py:162-168            pre_sampler_sync, record sample_end_evt
  deepinfer/worker/worker.py:170-189            keep WorkerStepState of N; return the outputs of N-1
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, VIOLET, WHITE, Diagram, text_width  # noqa: E402

d = Diagram(width=1100)
W = d.W
d.header(
    "One engine step with ZOS: which step does each phase touch?",
    "Decode step N, the default ZOS path  ·  the CPU runs top to bottom; the device runs its queue in order  ·  commit 9bd9cf2",
    params="blue tag = data of step N   ·   violet tag = data of step N-1   ·   green = device work that the phase queues",
)

y0 = 112
rows = [
    ("1", "loop: has_unfinished_requests(), step()", "llm.py:176-178", "loop", None),
    ("2", "schedule step N (C++ Scheduler)", "llm_engine.py:885-887", "N", None),
    ("3", "run_workers('execute_model_step')", "llm_engine.py:965-973", "N", None),
    ("4", "correct lengths: remap + kernel", "worker.py:118, 191-245", "N from N-1", "H2D, compute_seqlens_k_zos"),
    ("5", "prepare inputs, launch forward N", "worker.py:121-124", "N", "metadata, gather ids, forward N"),
    ("6", "wait sample_end_evt, post-process", "worker.py:144, 262-271", "N-1", None),
    ("7", "update metadata for sampling", "worker.py:147-152", "N", None),
    ("8", "launch sample N (+ DFlash drafts)", "worker.py:154-159", "N", "sample N, drafts, D2H copies"),
    ("9", "pre_sampler_sync, record event", "worker.py:162-168", "old", "sample_end_evt (N)"),
    ("10", "keep N; return outputs of N-1", "worker.py:182-189", "N / N-1", None),
]
ROW_H, GAP = 44, 8
P_H = 82 + len(rows) * (ROW_H + GAP) + 16
d.panel(y0, P_H, 1, "One call of step(): CPU phases in order, and the device queue",
        "By default the CPU waits for the device only in phase 6 (sample N-1). Forward N is queued, so the device keeps working.")

cx, cw = 46, 640
dx, dw = 740, 314
top = y0 + 88
d.text(cx, top - 10, "CPU (driver thread)", 12.5, INK, "bold")
d.text(dx, top - 10, "device stream (queued work)", 12.5, EMERALD, "bold")

TAGCOL = {"N": BLUE, "N-1": VIOLET, "N from N-1": BLUE, "N / N-1": VIOLET, "old": AMBER, "loop": MUTE}
for i, (num, title, cite, tag, dev) in enumerate(rows):
    y = top + i * (ROW_H + GAP)
    col = TAGCOL[tag]
    d.rect(cx, y, cw, ROW_H, fill=WHITE, stroke="#d1d5db", rx=8, sw=1.2)
    d.badge(cx + 22, y + ROW_H / 2, num, INK, r=12, size=11.5)
    d.text(cx + 44, y + 19, title, 13.5, INK, "bold")
    d.text(cx + 44, y + 36, cite, 12, MUTE, mono=True)
    tw = text_width(tag, 11, mono=True) + 20
    d.pill(cx + cw - tw - 12, y + (ROW_H - 19) / 2, tw, tag, col if tag != "loop" else MUTE)
    if dev:
        d.rect(dx, y + 4, dw, ROW_H - 8, fill=EMERALD[1], stroke=EMERALD, rx=6, sw=1.4)
        d.text(dx + dw / 2, y + ROW_H / 2 + 4.5, dev, 12, EMERALD, "bold", "middle", mono=True)
        d.arrow(cx + cw, y + ROW_H / 2, dx - 2, y + ROW_H / 2, EMERALD, sw=1.4)

# the wait in phase 6: dashed arrow from the event row back up
y6 = top + 5 * (ROW_H + GAP)
d.rect(dx, y6 + 4, dw, ROW_H - 8, fill=WHITE, stroke=VIOLET, rx=6, sw=1.3, dash="4 3")
d.text(dx + dw / 2, y6 + ROW_H / 2 + 4.5, "CPU waits: sample N-1 done", 12, VIOLET, "bold", "middle")
d.arrow(dx - 2, y6 + ROW_H / 2, cx + cw + 2, y6 + ROW_H / 2, VIOLET, sw=1.4, dash="5 4")

y = y0 + P_H + 22
d.legend(30, y, [(BLUE, "step N"), (VIOLET, "step N-1"), (AMBER, "older buffers"), (EMERALD, "device work")])
y += 34
y = d.footnotes(30, y, [
    "ZOS off: phase 4 does nothing, phase 6 finds no kept step, and phase 10 post-processes step N at once (it waits for sample N).",
    "A prefill step is always post-processed at once. With DSpark, phase 7 first waits for d2h_evt (worker.py:148-149).",
])
d.save(height=y + 10)
