# Look and diagram rules

Read this before you change the CSS, write a diagram, or review screenshots.

Part of the `codebase-explainer` skill. The single-file version of this playbook is `project-instructions.md` in the DeepInfer explainer repo. Placeholders: `{PROJECT}`, `{SHA}`, `{SHORT_SHA}`, `{REPO_URL}`, `{SITE_NAME}`.

## 4. Look and diagram rules

### 4.1 Page look (user feedback; binding)

The first look was dark and busy: the site followed the OS dark mode, and it had many boxes,
borders and badges. The user said: *"I hate the color scheme... need light background, readable.
This is learning material."* A full restyle followed. Start with the final look:

- **Light background always.** Dark mode only through the toggle button. Never follow
  `prefers-color-scheme`. The toggle stores the choice in `localStorage`; a small inline script in
  `<head>` applies it before paint.
- Model: a long-form magazine article (Sebastian Raschka's Substack).
- Body: Inter (Google Fonts), **18 px / line height 1.7** (17 px / 1.68 on phones). Text colour dark
  gray `#292929`, headings `#141414`, on white.
- **Prose column ~720 px** (`--measure`). **Figures up to ~1100 px** (`--wide`). The article is a
  3-track CSS grid: prose in the middle track, `.diagram`, `.viz`, `.figure-img` span the full width.
- Figures nested in a deep dive, a tour stop or a callout break out to full width with a container query:
  `.article { container-type: inline-size; }` and
  `.article :is(.diagram,.viz,.figure-img):not(.article > *) { width: min(var(--wide), 100cqw); position: relative; left: 50%; transform: translateX(-50%); }`.
- Few boxes, borders and badges. Hairline rules. Pale tints only where they help.
  Role colours only as small dots, thin rules and short labels.
- One link colour (blue). Site colour roles: blue = link / note; amber = warning; teal = deep dive;
  emerald / violet / pink = level Beginner / Intermediate / Advanced.
- Code: GitHub-light token colours, Prism from cdnjs (pinned version), line-number gutter,
  highlighted lines, "GitHub ↗" and "Copy" buttons, path header linked to the pinned commit.
- Wide tables: cells wrap at spaces, code in cells breaks anywhere, tighter cells on phones.
  A table with many columns may scroll inside its own box; the page must never scroll sideways.
- Diagrams and images sit on a white card, also in dark mode.
- Mobile: sidebar becomes a drawer below 960 px; 16 px side padding; brand name hidden below 560 px.

### 4.2 Diagram rules

The full guide is `instructions-svg.md`. Read it. The project rules below **override** it where they differ
(the starter kit already uses the site rules: `svglib.py` defaults to width 1100).

- **One Python script per diagram** in `diagrams/<name>.py`, built on the shared `diagrams/svglib.py`.
  No Mermaid, no hand-drawn SVG, no images when a script can draw it. One look for all diagrams.
- **Canvas width 1100**: `d = Diagram(width=1100)`. The build warns if the width is not 1100.
  (A 1500 canvas showed text at 7-8 px on a 1280 screen. 1100 shows near 1:1.)
- **No text smaller than 11** on the canvas. Mono data lines 12-13. Box titles 14. No rotated text.
- **At most 3 boxes side by side. At most 3 panels per diagram.** If you need more, split the
  diagram into two (for example `tour1_map_a`, `tour1_map_b`).
- White background rect; height computed from content; inline attributes only (no CSS, no `<style>`,
  no gradients, shadows, filters or images).
- Sans (Inter stack) for prose; mono for every number, size, identifier and path.
- One colour = one meaning; 3-5 role accents per diagram, all in the legend; neutral gray for the rest.
  Arrow colour = the role of what flows. Dashed arrows for secondary paths. Arrows do not cross boxes.
- Numbered panels top to bottom; flow left to right in a panel. Each panel answers one question;
  its subtitle is the answer.
- Title says what the diagram explains; subtitle says the scope. Footnotes say what is simplified.
- Real values from the code. Sources (`file:line`) in the script docstring or on the drawing.
- **Captions start with "Figure: "** and say what the reader must see. `alt` text is required and
  describes the content panel by panel.
- "Open full size" is a help. The diagram must be readable in the page at 100 %.

---
