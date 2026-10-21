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

d = Diagram()
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
P_H = 560
d.panel(y0, P_H, 1, "Who calls LLMEngine, and what does it call?",
        "Solid arrows are calls. The dashed arrow is a callback: the driver Worker calls back into the engine during a step.")

top = y0 + 76
# column 1: callers
c1x, c1w = 46, 380
card(c1x, top, c1w, 150, "LLM", ["generate()", "  → add_request()", "  → step() / flush_inflight_reqs()", "close()"], BLUE,
     sub="deepinfer/entrypoints/llm.py")
card(c1x, top + 176, c1w, 112, "scripts and tests", ["examples/benchmark.py", "calls llm.llm_engine.step()", "and reads .scheduler"], BLUE)
d.rect(c1x, top + 314, c1w, 150, fill=WHITE, stroke=MUTE, sw=1.2, dash="4 3")
d.text(c1x + 16, top + 340, "One process per DP rank", 14, INK, "bold")
d.text(c1x + 16, top + 364, "examples/_launch.py starts one", 12.5, MUTE)
d.text(c1x + 16, top + 383, "process per data-parallel rank.", 12.5, MUTE)
d.text(c1x + 16, top + 402, "Each process makes its own LLM", 12.5, MUTE)
d.text(c1x + 16, top + 421, "and its own LLMEngine.", 12.5, MUTE)

# column 2: engine
c2x, c2w = 466, 430
eh = 464
d.rect(c2x, top, c2w, eh, fill=BLUE[1], stroke=BLUE, sw=2.2)
d.text(c2x + 16, top + 28, "LLMEngine", 17, BLUE[0], "bold", mono=True)
d.text(c2x + 16, top + 50, "deepinfer/engine/llm_engine.py  ·  1,029 lines", 12.5, MUTE)
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
d.text(c2x + 16, top + 80, "attributes (C++ objects in violet)", 12.5, MUTE)
for i, (k, v, cpp) in enumerate(own):
    yy = top + 104 + i * 26
    d.text(c2x + 16, yy, k, MS, VIOLET[0] if cpp else INK, "bold" if cpp else "normal", mono=True)
    if v:
        d.text(c2x + c2w - 16, yy, v, 12, MUTE, anchor="end")

# column 3: callees
c3x, c3w = 1010, 444
card(c3x, top, c3w, 150, "deepinfer._C.engine  (C++)",
     ["Scheduler.schedule()", "Scheduler.process_outputs()", "process_MTPInfo()", "build_request_outputs()"], VIOLET,
     sub="csrc/engine/  ·  pybind11")
card(c3x, top + 176, c3w, 150, "driver Worker  (same process)",
     ["load_model, profile_num_available_blocks", "init_cache_engine, warm_up_model", "execute_model_step", "clone_and_zero_..., flush_inflight_reqs"], EMERALD,
     sub="deepinfer/worker/worker.py")
card(c3x, top + 352, c3w, 112, "CP follower Workers",
     ["cp_size − 1 spawned processes", "get (method, kwargs) by broadcast"], EMERALD,
     sub="only when context_parallel_size > 1")

# arrows: callers -> engine
d.arrow(c1x + c1w, top + 75, c2x - 2, top + 75, BLUE, sw=2)
d.arrow(c1x + c1w, top + 232, c2x - 2, top + 232, BLUE)
# engine -> C++
d.arrow(c2x + c2w, top + 75, c3x - 2, top + 75, VIOLET, sw=2)
# engine -> worker (run_workers) and callback back
d.arrow(c2x + c2w, top + 230, c3x - 2, top + 230, EMERALD, sw=2)
d.text((c2x + c2w + c3x) / 2, top + 220, "_run_workers", 12, EMERALD[0], "bold", "middle", mono=True)
d.arrow(c3x, top + 284, c2x + c2w + 2, top + 284, EMERALD, dash="5 4")
d.text((c2x + c2w + c3x) / 2, top + 274, "callbacks", 12, EMERALD[0], "bold", "middle", mono=True)
# worker -> followers
d.arrow(c3x + c3w / 2, top + 326, c3x + c3w / 2, top + 350, EMERALD)
d.text(c3x + c3w / 2 + 10, top + 343, "cp_broadcast_object", 11.5, EMERALD[0], "bold", mono=True)

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
