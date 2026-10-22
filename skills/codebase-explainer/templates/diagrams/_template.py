"""Diagram template. Copy to diagrams/<name>.py (no leading underscore) and edit.

Used by: src/<section>/<page>.html  (embed with <x-diagram name="<name>" alt="..." />)
Sources (at the pinned commit in explainer.json):
  path/to/file.py:10-20   what this panel shows
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import BLUE, EMERALD, INK, MUTE, VIOLET, Diagram  # noqa: E402

d = Diagram(width=1100)
d.header("What the diagram explains", "Scope  ·  assumptions  ·  one-line summary",
         params="constants  ·  shapes  ·  sizes")

y0 = 112
P1_H = 200
d.panel(y0, P1_H, 1, "First question?", "One-sentence answer.")
d.box(46, y0 + 76, 300, 70, "Component", ["detail [n, m]", "file.py:12"], col=BLUE)
d.arrow(346, y0 + 111, 444, y0 + 111, BLUE)          # end 2 px short of the target
d.arrow_label(395, y0 + 111, "what flows", BLUE)
d.box(446, y0 + 76, 300, 70, "Next component", ["detail"], col=EMERALD)

y = y0 + P1_H + 24
d.legend(30, y, [(BLUE, "role of blue"), (EMERALD, "role of emerald")])
y += 40
y = d.footnotes(30, y, ["Simplified: what this diagram leaves out."])
d.save(height=y + 14)
