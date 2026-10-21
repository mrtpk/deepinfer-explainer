"""Diagram: how build_request_outputs turns one decode step into RequestOutput objects, and how long they live.

Used by: src/code/outputs-hpp.html
Sources (commit 9bd9cf2):
  csrc/engine/outputs.hpp:199-216      count accepted drafts until -1; draft_tok / accept_tok
  csrc/engine/outputs.hpp:219-255      one RequestOutput per accepted draft
  csrc/engine/outputs.hpp:257-285      one more for the sampled token, if pushed_tokens allows it
  csrc/engine/outputs.hpp:287-294      draft_tok / accept_tok / confidence on the last output of the step
  csrc/engine/outputs.hpp:64-80        pool allocate (returns uint64) and release (destroy_at)
  csrc/engine/pybind_output.cpp:17-18  RequestOutput.clone(ptr): a Python-owned copy
  deepinfer/engine/llm_engine.py:974   DeferredRelease.collect_request_outputs
  deepinfer/engine/llm_engine.py:100-107, 830-831  release at the next pre_sampler_sync
  deepinfer/entrypoints/llm.py:179-182 LLM clones every handle
Numbers: nextn 5, so seqlen_q 6 and 5 draft rows. Token ids are made up.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, NEUTRAL, PINK, VIOLET, WHITE, Diagram  # noqa: E402

d = Diagram(width=1100)
W = d.W
d.header(
    "RequestOutput: from one step to the user",
    "build_request_outputs makes one object per new token  ·  the pool owns them  ·  the caller must clone",
    params="nextn 5   seqlen_q 6   pool size 10000   handle = uint64 address",
)

# ============================================================================
# Panel 1: one request, one decode step
# ============================================================================
y0 = 112
P1_H = 286
d.panel(y0, P1_H, 1, "One request, one decode step: how many outputs?",
        "One output per accepted draft, then one for the sampled token. The counters go on the last one.")
d.text(46, y0 + 86, "accepted_token_ids", 12, INK, "bold", mono=True)
d.text(46, y0 + 103, "(5 draft rows)", 11.5, MUTE)
vals = ["412", "77", "-1", "-1", "-1"]
for j, v in enumerate(vals):
    x = 210 + j * 62
    ok = v != "-1"
    col = EMERALD if ok else NEUTRAL
    d.rect(x, y0 + 74, 56, 34, fill=col[1], stroke=col[0], rx=4, sw=1.4)
    d.text(x + 28, y0 + 96, v, 12.5, INK, "bold" if ok else "normal", "middle", mono=True)
d.text(210, y0 + 128, "stop at the first -1: num_accepted = 2", 12, MUTE)
d.text(560, y0 + 86, "token_ids[i]", 12, INK, "bold", mono=True)
d.rect(680, y0 + 74, 70, 34, fill=BLUE[1], stroke=BLUE[0], rx=4, sw=1.4)
d.text(715, y0 + 96, "9051", 12.5, INK, "bold", "middle", mono=True)
d.text(560, y0 + 128, "the sampled token", 12, MUTE)
d.text(790, y0 + 86, "pushed_tokens = 3", 12, INK, mono=True)
d.text(790, y0 + 104, "from process_outputs", 11.5, MUTE)

cards = [
    ("output 1", ["token_id      412", "finished      false", "draft_tok     0"], EMERALD),
    ("output 2", ["token_id      77", "finished      false", "draft_tok     0"], EMERALD),
    ("output 3", ["token_id      9051", "draft_tok     6", "accept_tok    3"], BLUE),
]
for i, (t, lines, col) in enumerate(cards):
    x = 46 + i * 342
    d.box(x, y0 + 150, 320, 90, t, lines, col=col, align="start", mono_size=12)
    if i < 2:
        d.arrow(x + 322, y0 + 195, x + 340, y0 + 195, INK)
d.text(46, y0 + 268, "draft_tok = 5 drafts + 1 = 6    accept_tok = 2 accepted + 1 = 3    "
       "offline_inference.py turns them into an accept rate.", 12, INK)

# ============================================================================
# Panel 2: lifetime
# ============================================================================
y1 = y0 + P1_H + 20
P2_H = 230
d.panel(y1, P2_H, 2, "How long does an output live?",
        "The pool takes the objects back at the next pre_sampler_sync. The user keeps only clones.")
lanes = [
    (VIOLET, "C++ pool", 46),
    (AMBER, "LLMEngine", 396),
    (PINK, "LLM (user API)", 746),
]
for col, name, x in lanes:
    d.text(x, y1 + 80, name, 13.5, col[0], "bold")
d.step_card(46, y1 + 92, 330, 98, 1, "step N: allocate", VIOLET, tag="outputs.hpp:64",
            rows=[("in", "placement new in a free slot"), ("out", "uint64 handle per output"),
                  ("lim", "10000 slots, else error")], key_w=34)
d.step_card(396, y1 + 92, 330, 98, 2, "step N: collect, return", AMBER, tag="llm_engine:974",
            rows=[("keep", "handles in DeferredRelease"), ("ret", "the same uint64 array"),
                  ("N+1", "pre_sampler_sync: release")], key_w=40)
d.step_card(746, y1 + 92, 308, 98, 3, "before step N+1: clone", PINK, tag="llm.py:181",
            rows=[("copy", "RequestOutput.clone(h)"), ("own", "Python owns the copy"),
                  ("note", "the handle dies later")], key_w=40)
d.arrow(378, y1 + 141, 394, y1 + 141, VIOLET)
d.arrow(728, y1 + 141, 744, y1 + 141, AMBER)
d.text(46, y1 + 214, "Next step: pool.release(handles) calls destroy_at on each object and puts its slot back (outputs.hpp:72-80).",
       12, MUTE)

y = y1 + P2_H + 24
d.legend(30, y, [(EMERALD, "accepted draft"), (BLUE, "sampled token"), (NEUTRAL, "-1: not accepted"),
                 (VIOLET, "C++ pool"), (AMBER, "engine"), (PINK, "user API")])
y += 40
y = d.footnotes(30, y, [
    "Simplified: a prefill step has no draft rows. It gives one output per request whose prompt is complete (none for an earlier chunk).",
    "Sequences in ignored_seqs (too long, aborted while waiting, stopped by preemption) get one output with their last token (297-304).",
])
d.save(height=y + 14)
