"""Diagram: where LLMEngine sits (who calls it, what it owns and calls).

Used by: src/code/llm-engine.html (section "Where it sits")
Sources (commit 9bd9cf2):
  deepinfer/entrypoints/llm.py:84,160,177-178,198        LLM makes the engine and calls it
  examples/benchmark.py:230-231                          a script that calls step() directly
  examples/_launch.py:26-50                              one process per DP rank
  deepinfer/engine/llm_engine.py:200-205                 tokenizer
  deepinfer/engine/llm_engine.py:209-221                 MultimodalProcessor (not for COMPLETION engines)
  deepinfer/engine/llm_engine.py:230,265-271             RequestOutputPool, BlockManager x2, Scheduler, SequenceMetadataPool
  deepinfer/engine/llm_engine.py:329-342                 SOMatcherBuilder (lazy)
  deepinfer/engine/llm_engine.py:377-413                 CP follower processes + driver Worker in this process
  deepinfer/engine/llm_engine.py:398-400                 EngineCallbacks(post_process, pre_sampler_sync)
  deepinfer/engine/llm_engine.py:1017-1025               _run_workers -> driver_worker.run_workers
  deepinfer/worker/base.py:290-302, 129-133              cp_broadcast_object to followers; follower loop
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import BLUE, EMERALD, INK, MUTE, VIOLET, WHITE, Diagram  # noqa: E402

d = Diagram(width=1100)
d.header(
    "Where LLMEngine sits",
    "deepinfer/engine/llm_engine.py  ·  one engine per data-parallel rank  ·  each rank is its own process",
    params="LLM → LLMEngine → { C++ scheduler, driver Worker }    Worker → LLMEngine only through 2 callbacks",
)

TS, MS = 15, 13


def card(x, y, w, h, title, lines, col, sub=None):
    d.rect(x, y, w, h, fill=col[1], stroke=col, sw=1.5)
    d.text(x + 16, y + 26, title, TS, col[0], "bold", mono=True)
    yy = y + 26
    if sub:
        d.text(x + 16, y + 46, sub, 12.5, MUTE)
        yy = y + 46
    for i, s in enumerate(lines):
        d.text(x + 16, yy + 22 + i * 19, s, MS, INK, mono=True)


y0 = 120
top = y0 + 76
# three columns, shared by the callers row (top) and the callees row (bottom)
COLS = [(46, 290), (370, 360), (764, 290)]
(sx_, sw_), (lx_, lw_), (nx_, nw_) = COLS
ROWS = 6                                   # engine attributes: 2 columns of 6
ey = top + 150 + 48                        # engine box top
eh = 104 + (ROWS - 1) * 24 + 22            # engine box height
by = ey + eh + 62                          # callees row top
P_H = by + 150 + 26 + 34 - y0              # panel ends below the routed broadcast arrow
d.panel(y0, P_H, 1, "Who calls LLMEngine, and what does it call?",
        "Solid arrows are calls. The dashed arrow is a callback: the driver Worker calls back into the engine during a step.")

# ---- row 1: callers -------------------------------------------------------
card(lx_, top, lw_, 150, "LLM", ["generate()", "  → add_request()", "  → step() / flush_inflight_reqs()", "close()"], BLUE,
     sub="deepinfer/entrypoints/llm.py")
card(sx_, top, sw_, 112, "scripts and tests", ["examples/benchmark.py", "calls llm.llm_engine.step()", "and reads .scheduler"], BLUE)
d.rect(nx_, top, nw_, 150, fill=WHITE, stroke=MUTE, sw=1.2, dash="4 3")
d.text(nx_ + 16, top + 26, "One process per DP rank", 14, INK, "bold")
d.text(nx_ + 16, top + 50, "examples/_launch.py starts one", 12.5, MUTE)
d.text(nx_ + 16, top + 69, "process per data-parallel rank.", 12.5, MUTE)
d.text(nx_ + 16, top + 88, "Each process makes its own LLM", 12.5, MUTE)
d.text(nx_ + 16, top + 107, "and its own LLMEngine.", 12.5, MUTE)

# ---- row 2: the engine ------------------------------------------------------
c2x, c2w = 46, d.W - 92
own = [
    ("tokenizer", "Hugging Face tokenizer", False),
    ("multi_modal_processor", "or None", False),
    ("request_output_pool", "RequestOutputPool", True),
    ("block_manager", "KV cache blocks", True),
    ("state_manager", "state slots, or None", True),
    ("scheduler", "Scheduler", True),
    ("sequence_metadata_pool", "", True),
    ("deferred_release", "DeferredRelease", False),
    ("stats_logger", "StatsLogger", False),
    ("profile_manager", "or None", False),
    ("_so_matcher_builder", "made on first use", False),
    ("driver_worker", "Worker", False),
]
d.rect(c2x, ey, c2w, eh, fill=BLUE[1], stroke=BLUE, sw=2.2)
d.text(c2x + 16, ey + 28, "LLMEngine", 17, BLUE[0], "bold", mono=True)
d.text(c2x + 16, ey + 50, "deepinfer/engine/llm_engine.py  ·  1,029 lines", 12.5, MUTE)
d.text(c2x + 16, ey + 80, "attributes (C++ objects in violet)", 12.5, MUTE)
half = c2w / 2
for i, (k, v, cpp) in enumerate(own):
    col_x = c2x + (i // ROWS) * half
    yy = ey + 104 + (i % ROWS) * 24
    d.text(col_x + 16, yy, k, MS, VIOLET[0] if cpp else INK, "bold" if cpp else "normal", mono=True)
    if v:
        d.text(col_x + half - 40, yy, v, 12, MUTE, anchor="end")

# callers -> engine
d.arrow(lx_ + lw_ / 2, top + 150, lx_ + lw_ / 2, ey - 2, BLUE, sw=2)
d.arrow(sx_ + sw_ / 2, top + 112, sx_ + sw_ / 2, ey - 2, BLUE)

# ---- row 3: what the engine calls -------------------------------------------
(cx_, cw_), (wx_, ww_), (fx_, fw_) = COLS
card(cx_, by, cw_, 150, "deepinfer._C.engine  (C++)",
     ["Scheduler.schedule()", "Scheduler.process_outputs()", "process_MTPInfo()", "build_request_outputs()"], VIOLET,
     sub="csrc/engine/  ·  pybind11")
card(wx_, by, ww_, 150, "driver Worker  (same process)",
     ["load_model, profile_num_available_blocks", "init_cache_engine, warm_up_model", "execute_model_step", "clone_and_zero_..., flush_inflight_reqs"], EMERALD,
     sub="deepinfer/worker/worker.py")
card(fx_, by, fw_, 112, "CP follower Workers",
     ["cp_size − 1 spawned processes", "get (method, kwargs) by broadcast"], EMERALD,
     sub="only when context_parallel_size > 1")

eb = ey + eh
# engine -> C++
d.arrow(cx_ + cw_ / 2, eb, cx_ + cw_ / 2, by - 2, VIOLET, sw=2)
# engine -> worker (run_workers) and callback back
ax1, ax2 = wx_ + 110, wx_ + 250
d.arrow(ax1, eb, ax1, by - 2, EMERALD, sw=2)
d.text(ax1 + 8, eb + 36, "_run_workers", 12, EMERALD[0], "bold", mono=True)
d.arrow(ax2, by, ax2, eb + 2, EMERALD, dash="5 4")
d.text(ax2 + 8, eb + 36, "callbacks", 12, EMERALD[0], "bold", mono=True)
# worker -> followers: routed under the boxes
wb = by + 150
ry_ = wb + 26
fcx = fx_ + fw_ / 2
d.path_arrow(f"M {wx_ + ww_ - 60:.1f},{wb:.1f} L {wx_ + ww_ - 60:.1f},{ry_:.1f} L {fcx:.1f},{ry_:.1f} L {fcx:.1f},{by + 112 + 2:.1f}",
             EMERALD)
d.text((wx_ + ww_ - 60 + fcx) / 2, ry_ + 18, "cp_broadcast_object", 11.5, EMERALD[0], "bold", "middle", mono=True)

y = y0 + P_H + 24
d.legend(30, y, [(BLUE, "Python, engine process"), (VIOLET, "C++ extension, called from the engine process"),
                 (EMERALD, "Worker: launches device work")])
y += 40
y = d.footnotes(30, y, [
    "Callbacks: post_process(step_state) and pre_sampler_sync(scheduler_outputs), passed in EngineCallbacks (llm_engine.py:398-400).",
    "Not shown: multimodal pre-processing child processes, the SOMatcherBuilder thread pool, the stats log thread and the",
    "  profiling HTTP thread (only with DEEPINFER_PROFILE_HTTP_ENABLE=1). The deep dive on the page lists them.",
])
d.save(height=y + 10)
