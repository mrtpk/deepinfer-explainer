"""Diagram: what one call of LLMEngine.step() does, in order.

Used by: src/code/llm-engine.html (section "Walk through the main methods", step())
Sources (commit 9bd9cf2):
  deepinfer/engine/llm_engine.py:872-879     timers, profiler hook
  deepinfer/engine/llm_engine.py:884-887     Scheduler.schedule(pool)
  deepinfer/engine/llm_engine.py:889-905     clone / zero states and blocks (only when asked)
  deepinfer/engine/llm_engine.py:907-945     post_schedule hook, SO check, multimodal fetch
  deepinfer/engine/llm_engine.py:961-975     _execute_model_async_step -> run_workers("execute_model_step")
  deepinfer/worker/worker.py:113-127         1. forward current step
  deepinfer/worker/worker.py:143-144         2. post-process previous step -> engine.post_process
  deepinfer/engine/llm_engine.py:984-1015    post_process -> _process_model_outputs
  deepinfer/engine/llm_engine.py:717-761     process_MTPInfo, scheduler.process_outputs, build_request_outputs
  deepinfer/worker/worker.py:154-164         3. sample current step, then pre_sampler_sync callback
  deepinfer/engine/llm_engine.py:830-846     pre_sampler_sync
  deepinfer/worker/worker.py:182-189         4. post-process now (prefill / ZOS off) or keep for next step
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import BLUE, EMERALD, INK, MUTE, VIOLET, WHITE, Diagram  # noqa: E402

d = Diagram()
d.header(
    "One call of LLMEngine.step(), in order",
    "A decode step with zero-overhead scheduling (ZOS) on, the default for a NORMAL engine  ·  N = this step, N−1 = the step before",
    params="returns: np.ndarray[np.uint64]  =  handles of RequestOutput objects in the RequestOutputPool",
)

y0 = 116
lanes = [
    (46, 452, BLUE, "LLMEngine", "deepinfer/engine/llm_engine.py"),
    (524, 452, VIOLET, "C++ engine", "deepinfer._C.engine (csrc/engine/)"),
    (1002, 452, EMERALD, "driver Worker → ModelRunner", "deepinfer/worker/worker.py"),
]

rows = [
    (0, "step() starts", "timers · profile_manager.step()", "872-879", False),
    (1, "schedule the batch", "schedule(pool) → seq_metadata_list, outputs", "884-887", False),
    (2, "clone / zero state + blocks", "only if the scheduler asks", "889-905", True),
    (0, "after-schedule checks", "post_schedule · SO status · multimodal fetch", "907-945", False),
    (2, "forward step N", "execute_main_model (no CPU-GPU sync)", "worker 113-127", False),
    (2, "post-process step N−1", "wait for its sample event, then call back", "worker 143-144", False),
    (0, "post_process callback", "_process_model_outputs(N−1)", "984-1015", False),
    (1, "commit N−1 tokens, MTP info", "process_outputs · build_request_outputs", "717-761", False),
    (2, "sample step N", "execute_sample → SamplerOutput", "worker 154-159", False),
    (0, "pre_sampler_sync callback", "release N−1 buffers · SO pump · free finished", "830-846", False),
    (2, "keep step N for later", "ZOS decode: post-process in the next step()", "worker 182-189", False),
    (0, "return handles", "RequestOutput handles of step N−1", "974-975, 959", False),
]

lane_top = y0 + 8
head_h = 52
row_h, row_gap = 58, 16
body_top = lane_top + head_h + 18
total_h = head_h + 18 + len(rows) * (row_h + row_gap) + 6
for (x, w, col, name, sub) in lanes:
    d.rect(x, lane_top, w, total_h, fill=col[2], stroke=col, rx=12, sw=1.2, dash="4 4", stroke_op=0.35)
    d.rect(x, lane_top, w, head_h, fill=col[0], stroke=None, rx=12)
    d.rect(x, lane_top + head_h - 16, w, 16, fill=col[0], stroke=None, rx=0)
    d.text(x + 16, lane_top + 23, name, 15.5, "#fff", "bold")
    d.text(x + 16, lane_top + 42, sub, 12, "#fff", mono=True)

prev = None
for i, (lane, title, detail, src, optional) in enumerate(rows):
    x, w, col, _, _ = lanes[lane]
    cx, cw = x + 14, w - 28
    y = body_top + i * (row_h + row_gap)
    d.rect(cx, y, cw, row_h, fill=WHITE if optional else col[1], stroke=col, sw=1.4,
           dash="5 4" if optional else None)
    d.rect(cx, y, 6, row_h, fill=col[0], stroke=None, rx=3)
    d.badge(cx + 24, y + 19, i + 1, col, r=11, size=12)
    d.text(cx + 42, y + 24, title, 14.5, INK, "bold")
    d.text(cx + cw - 10, y + 23, src, 12, MUTE, anchor="end", mono=True)
    d.text(cx + 42, y + 46, detail, 13, INK, mono=True)
    if prev is not None:
        px, py = prev
        nx = cx + cw / 2
        if abs(px - nx) < 1:
            d.arrow(px, py, nx, y - 2, INK)
        else:
            my = py + row_gap / 2
            d.path_arrow(f"M {px:.1f},{py:.1f} L {px:.1f},{my:.1f} L {nx:.1f},{my:.1f} L {nx:.1f},{y - 2:.1f}", INK)
    prev = (cx + cw / 2, y + row_h)

y = lane_top + total_h + 24
d.legend(30, y, [(BLUE, "Python in the engine"), (VIOLET, "C++ called from the engine"),
                 (EMERALD, "Worker: launches device work")])
y += 40
y = d.footnotes(30, y, [
    "Rows 5-11 all run inside one call: run_workers(\"execute_model_step\"). The Worker calls rows 7 and 10 back in the engine.",
    "Prefill step, or ZOS off: at row 11 the Worker post-processes step N at once, so step() also returns the outputs of step N.",
    "First step: there is no step N−1, so rows 6-8 return no outputs. LLM calls flush_inflight_reqs() at the end to get the last step.",
    "Line numbers are in llm_engine.py unless marked \"worker\" (deepinfer/worker/worker.py).",
])
d.save(height=y + 10)
