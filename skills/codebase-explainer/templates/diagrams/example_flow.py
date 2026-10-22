"""Example diagram: the path of one request through three parts (placeholder content).

Used by: src/concepts/example-concept.html, src/tours/example-tour.html
Sources (at the pinned commit in explainer.json):
  README.md:1        the project name (replace with the real sources of each box)
Replace the labels and the file:line values with real ones from the target repo.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, Diagram  # noqa: E402

d = Diagram(width=1100)
d.header("How one request goes through the system",
         "Example diagram  ·  three parts  ·  replace the labels with real ones",
         params="1 request  ·  3 parts  ·  canvas 1100")

y0 = 112
P1_H = 170
d.panel(y0, P1_H, 1, "Which parts does a request pass?", "The API, the engine and the store, in this order.")
bx_y, bw, bh = y0 + 70, 290, 76
d.box(46, bx_y, bw, bh, "Public API", ["pkg/api.py", "submit(request)"], col=BLUE)
d.arrow(46 + bw, bx_y + bh / 2, 400 - 2, bx_y + bh / 2, BLUE)
d.arrow_label(46 + bw + 32, bx_y + bh / 2, "request", BLUE)
d.box(400, bx_y, bw, bh, "Engine", ["pkg/engine.py", "step()"], col=AMBER)
d.arrow(400 + bw, bx_y + bh / 2, 754 - 2, bx_y + bh / 2, AMBER)
d.arrow_label(400 + bw + 32, bx_y + bh / 2, "result", AMBER)
d.box(754, bx_y, bw, bh, "Store", ["pkg/store.py", "put(key, value)"], col=EMERALD)

y = y0 + P1_H + 24
d.legend(30, y, [(BLUE, "API (user side)"), (AMBER, "engine (main loop)"), (EMERALD, "storage")])
y += 40
y = d.footnotes(30, y, ["Simplified: this example leaves out errors, retries and threads.",
                        "Template: replace every label and path with real values from the target repo."])
d.save(height=y + 14)
