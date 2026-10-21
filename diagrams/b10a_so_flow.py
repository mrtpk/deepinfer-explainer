"""Diagram: how a structured-output request gets its grammar matcher, and the so_status ledger.

Used by: src/concepts/structured-outputs.html ("The picture"), src/code/structure-output.html
Sources (commit 9bd9cf2):
  deepinfer/engine/llm_engine.py:606-630          add_request: so_pending, submit(seq, so_args, _enqueue)
  deepinfer/structure_output/so_matcher_builder.py:58-95   build(): key checks, trigger check, pool.submit(_build)
  deepinfer/structure_output/so_matcher_builder.py:31-49   pinned thread pool; compiler made on a pool thread
  deepinfer/structure_output/compiler.py:54-71     dispatch_and_compile: json / regex / ebnf
  deepinfer/structure_output/so_matcher_builder.py:109-121 pump(): try_result, seq.so_matcher, on_ready
  deepinfer/engine/llm_engine.py:841-842           pump() in pre_sampler_sync (every step)
  deepinfer/structure_output/matcher.py:319-338    try_result: timeout -> aborted matcher
  csrc/engine/scheduler.hpp:363-367                SO_FAILED request skips prefill
  csrc/engine/sequence.hpp:230-233                 status 0 / 1 / 2 / -1
  deepinfer/engine/llm_engine.py:913-928           last prompt chunk: 0 -> 1
  deepinfer/model_executor/layers/sampler.py:352-386       1 -> 2, errors -> -1
  csrc/engine/scheduler.hpp:928-929, 974-980       ledger update; -1 -> FINISHED_SO_FAILED
  csrc/engine/scheduler.hpp:770-780                preempted with status != 0 -> stops
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, PINK, VIOLET, Diagram  # noqa: E402

d = Diagram(width=1100)
W = d.W

d.header(
    "Structured outputs: from so_args to a running request",
    "The grammar compiles on a CPU thread pool  ·  the engine thread polls it once per step  ·  a status number follows the request",
    params="DEEPINFER_SO_BUILDER_CPUS = 4 threads  ·  DEEPINFER_XGRAMMAR_TIMEOUT = 20 s  ·  status 0 / 1 / 2 / −1",
)

# ---------------------------------------------------------------- panel 1
y0 = 112
P1 = 394
d.panel(y0, P1, 1, "Where does the grammar compile? On a pool thread, not in the step",
        "add_request returns at once. The request enters the scheduler only when pump() finds the matcher ready.")

bw, bh = 300, 104
xs = [46, 400, 754]
ra = y0 + 76
d.box(xs[0], ra, bw, bh, "1  LLMEngine.add_request", [
    "so_args is set  →  so_pending", "(no scheduler entry yet)", "llm_engine.py:606-613"], col=BLUE)
d.box(xs[1], ra, bw, bh, "2  SOMatcherBuilder.submit", [
    "build(): check keys + trigger", "pool.submit(_build) → future", "so_matcher_builder.py:58-108"], col=BLUE)
d.box(xs[2], ra, bw, bh, "3  pool thread (pinned CPUs)", [
    "xgrammar compile (json/regex/ebnf)", "XGrammarMatcher.from_compiled", "compiler.py:54-71"], col=VIOLET)
d.arrow(xs[0] + bw, ra + bh / 2, xs[1] - 2, ra + bh / 2, BLUE)
d.arrow(xs[1] + bw, ra + bh / 2, xs[2] - 2, ra + bh / 2, BLUE)

rb = ra + bh + 66
d.box(xs[2], rb, bw, bh, "4  pump() in pre_sampler_sync", [
    "every step: future.try_result()", "not done → keep waiting", "llm_engine.py:841-842"], col=BLUE)
d.box(xs[1], rb, bw, bh, "5  on_ready = _enqueue(seq)", [
    "pump has set seq.so_matcher", "aborted → FINISHED_SO_FAILED", "llm_engine.py:620-623"], col=BLUE)
d.box(xs[0], rb, bw, bh, "6  C++ scheduler", [
    "waiting queue → prefill", "SO_FAILED → ignored, no prefill", "scheduler.hpp:363-367"], col=EMERALD)
d.arrow(xs[2] + bw / 2, ra + bh, xs[2] + bw / 2, rb - 2, VIOLET, dash="5 4")
d.arrow_label(xs[2] + bw / 2 + 92, ra + bh + 40, "future done", VIOLET)
d.arrow(xs[2], rb + bh / 2, xs[1] + bw + 2, rb + bh / 2, BLUE)
d.arrow(xs[1], rb + bh / 2, xs[0] + bw + 2, rb + bh / 2, BLUE)
d.text(xs[0], rb + bh + 30, "Timeout: 20 s after submit, try_result() gives an aborted matcher, so step 5 ends the request (matcher.py:332-335).",
       12, MUTE, italic=True)

# ---------------------------------------------------------------- panel 2
y1 = y0 + P1 + 20
P2 = 316
d.panel(y1, P2, 2, "What does so_status mean? A ledger in the C++ Sequence",
        "The sampler reads the status, may change it, and process_outputs writes it back for the next step.")

cw, ch = 300, 96
cy = y1 + 78
d.box(xs[0], cy, cw, ch, "status 0: not started", [
    "prompt chunks still run", "no mask, no matcher work", "sequence.hpp:231"], col=INK)
d.box(xs[1], cy, cw, ch, "status 1: boundary", [
    "set on the last prompt chunk", "sampler: → 2, then fill mask 0", "llm_engine.py:913-915"], col=BLUE)
d.box(xs[2], cy, cw, ch, "status 2: running", [
    "accept last step's tokens", "fill one mask per draft row", "sampler.py:352-376"], col=EMERALD)
d.arrow(xs[0] + cw, cy + ch / 2, xs[1] - 2, cy + ch / 2, INK)
d.arrow(xs[1] + cw, cy + ch / 2, xs[2] - 2, cy + ch / 2, BLUE)

fy = cy + ch + 34
fw = 654
d.box(xs[1], fy, fw, 76, "status −1: aborted  →  FINISHED_SO_FAILED", [
    "matcher error, or the matcher is missing or aborted  ·  sampler.py:342-349, 377-386",
    "process_outputs ends the request  ·  scheduler.hpp:974-980"], col=PINK)
d.path_arrow(f"M {xs[2] + cw / 2},{cy + ch} L {xs[2] + cw / 2},{fy - 2}", PINK, dash="5 4")
d.path_arrow(f"M {xs[1] + cw / 2 - 60},{cy + ch} L {xs[1] + cw / 2 - 60},{fy - 2}", PINK, dash="5 4")
d.text(xs[0], fy + 22, "Preempted with status ≠ 0:", 12.5, INK, "bold")
d.text(xs[0], fy + 40, "the request stops (no recompute),", 12, INK)
d.text(xs[0], fy + 56, "scheduler.hpp:770-780", 12, INK, mono=True)

y = y1 + P2 + 22
d.legend(30, y, [(BLUE, "engine thread (Python)"), (VIOLET, "pool thread (xgrammar)"), (EMERALD, "C++ scheduler"),
                 (PINK, "failure path")])
y += 36
y = d.footnotes(30, y, [
    "Not shown: the synchronous path (enqueue=False) calls build().result() and waits (llm_engine.py:609-611).",
    "Status values come from the comment in sequence.hpp:231; a request without so_args keeps status 0.",
])
d.save(height=y + 10)
