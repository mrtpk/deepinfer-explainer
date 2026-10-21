"""Diagram: LLM.generate(): add every request, then run the step loop, then group, sort and decode.

Used by: src/code/entrypoints-llm.html
Sources (commit 9bd9cf2):
  deepinfer/entrypoints/llm.py:117-142   generate: checks, defaults, one _add_request per prompt
  deepinfer/entrypoints/llm.py:151-166   _add_request: deepcopy, id, tokenize, int32, empty image dict, add_request
  deepinfer/entrypoints/llm.py:176-186   loop: has_unfinished -> step, else flush; clone every handle
  deepinfer/entrypoints/llm.py:187-190   sort by int(request_id), optional decode to text
  deepinfer/engine/llm_engine.py:665-679 has_unfinished_requests: all-reduce MAX over data-parallel ranks
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, PINK, VIOLET, Diagram  # noqa: E402

d = Diagram(width=1100)
W = d.W
d.header(
    "LLM.generate(): add, loop, collect",
    "The offline API in deepinfer/entrypoints/llm.py  ·  one call handles a whole batch of prompts",
    params="request ids: \"0\", \"1\", ... (one counter per LLM object)   user_id: always \"0\"",
)

# ============================================================================
# Panel 1: add the requests
# ============================================================================
y0 = 112
P1_H = 214
d.panel(y0, P1_H, 1, "Add: one request per prompt",
        "generate() checks the inputs, then calls _add_request for each prompt, in order. Nothing runs on the device yet.")
d.step_card(46, y0 + 70, 320, 126, 1, "generate()", BLUE, tag="llm.py:117", rows=[
    ("chk", "prompts or token ids"),
    ("str", "one prompt -> list"),
    ("def", "SamplingParams()"),
    ("for", "i in range(num_requests)"),
], key_w=36)
d.arrow(368, y0 + 133, 390, y0 + 133, BLUE)
d.step_card(392, y0 + 70, 360, 126, 2, "_add_request()", VIOLET, tag="llm.py:144", rows=[
    ("copy", "deepcopy(sampling_params)"),
    ("id", "str(next(counter))"),
    ("tok", "tokenizer.encode(prompt) or ids"),
    ("ids", "np.asarray(..., dtype=np.int32)"),
], key_w=40)
d.arrow(754, y0 + 133, 776, y0 + 133, VIOLET)
d.box(778, y0 + 70, 276, 126, "LLMEngine.add_request", [
    "user_id=\"0\"",
    "-> Sequence in the",
    "   waiting queue",
    "-> None if a token is bad",
], col=AMBER, align="start", mono_size=12)

# ============================================================================
# Panel 2: the loop
# ============================================================================
y1 = y0 + P1_H + 20
P2_H = 266
d.panel(y1, P2_H, 2, "Loop: step until no rank has work, then flush",
        "Every handle is cloned at once, because the pool reuses it in the next step. Outputs are grouped by request id.")
d.box(46, y1 + 76, 250, 70, "has_unfinished_requests()", ["all-reduce MAX over DP ranks"], col=AMBER, mono_size=12)
d.arrow(298, y1 + 100, 336, y1 + 100, AMBER)
d.arrow_label(317, y1 + 100, "yes", AMBER)
d.box(338, y1 + 83, 200, 34, "step()", [], col=AMBER)
d.path_arrow(f"M 171,{y1 + 148} L 171,{y1 + 186} L 336,{y1 + 186}", AMBER)
d.text(182, y1 + 172, "no", 11.5, AMBER[0], "bold")
d.box(338, y1 + 169, 200, 34, "flush_inflight_reqs()", [], col=AMBER)
d.arrow(540, y1 + 101, 576, y1 + 125, INK)
d.arrow(540, y1 + 186, 576, y1 + 163, INK)
d.path_arrow(f"M 816,{y1 + 214} L 816,{y1 + 226} L 32,{y1 + 226} L 32,{y1 + 111} L 44,{y1 + 111}", INK, dash="5 4")
d.text(830, y1 + 230, "next round (after step only)", 11.5, MUTE, italic=True)
d.step_card(578, y1 + 76, 476, 136, 3, "for each uint64 handle", PINK, tag="llm.py:179", rows=[
    ("copy", "RequestOutput.clone(handle)"),
    ("group", "outputs[request_id].append(...)"),
    ("tqdm", "+1 when output.finished"),
    ("end", "break after the flush"),
], key_w=48)
d.text(46, y1 + 252, "After the loop: sort the ids as integers; with decode_sequence=True, each request becomes tokenizer.decode(ids).",
       12, EMERALD[0], "bold")

y = y1 + P2_H + 24
d.legend(30, y, [(BLUE, "user call"), (VIOLET, "per request"), (AMBER, "engine calls"), (PINK, "per output"),
                 (EMERALD, "result")])
y += 40
y = d.footnotes(30, y, [
    "Simplified: the loop body is the same for step() and for the flush; the flush runs once, then the loop ends.",
    "With ZOS, a decode step returns the tokens of the step before. The flush post-processes the last step in flight, often an empty one.",
])
d.save(height=y + 14)
