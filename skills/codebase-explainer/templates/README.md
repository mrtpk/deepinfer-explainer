# <Project> Explained

A static website that teaches the [<Project>](<repo URL>) codebase step by step.
<One sentence: what <Project> is.>

The site is for a reader who knows <language> but knows little about <domain>.
Each page starts with a simple explanation. Then a "Deep dive" gives the full detail for study.

> **Status:** <complete / in progress>. The site has <N> pages. Each page was fact-checked against the code.
> <Deferred pages, if any. They show as "soon" in the menu.> See [`progress.md`](progress.md).

## Code version

The site explains one exact version of <Project>:

| | |
|---|---|
| Commit | [`<full sha>`](<repo URL>/tree/<full sha>) |
| Date | <date> |

All code excerpts and `file:line` links point to this commit. Line numbers can be different in newer versions.

```bash
git clone <repo URL>.git
cd <Project>
git checkout <full sha>
git submodule update --init --recursive   # only if the repo has submodules
```

## Read the site

Open `site/index.html` in a browser. The site works from disk (`file://`), with no server.
It needs an internet connection only for the Inter font and for code colours (Prism from cdnjs).
Without it, the site uses a system font and plain code.

| Part | Folder | What it contains |
|---|---|---|
| Learn the basics | `learn/` | <topics> |
| Concepts | `concepts/` | Each idea in <Project> and the files that use it |
| Guided tours | `tours/` | Step-by-step tours through real code, for example "Life of a request" |
| Code map | `code/` | A folder tree and one page for each important module |
| Reference | `reference/` | <generated tables>, the glossary, the FAQ |

Press `/` to search. Point to a dotted word to see its glossary definition.

## Build the site

Requirements: Python 3.11 or newer (standard library only), and a checkout of <Project> at the commit
above, at the path `repo_path` in `explainer.json` (default: a folder next to this one).

```
parent/
  <Project>/              # git checkout at <short sha> (read only)
  <project>-explainer/    # this repository
```

```bash
python3 tools/gen_folder_tree.py   # update the code-map folder tree
python3 build.py                   # build site/ from src/
python3 build.py --strict          # also stop on warnings
python3 build.py --preview         # write site/ even when a page has errors
python3 build.py --force-diagrams  # run all diagram scripts again
```

The build reads code excerpts directly from the checkout, so each excerpt is exact.
It stops with an error if the checkout is at a different commit, or if a link, a code citation or a
glossary term is wrong.

## Repository layout

| Path | Contents |
|---|---|
| `explainer.json` | Project name, target repo path and URL, pinned commit, language style |
| `src/` | Page sources, navigation (`src/nav/`) and glossary (`src/glossary/`) |
| `diagrams/` | One Python script for each SVG diagram, and the shared helper `svglib.py` |
| `assets/` | Site CSS and JavaScript, and the interactive visuals (`assets/viz/`) |
| `tools/` | Generators for reference tables and the folder tree |
| `notes/facts.md` | Facts that were checked in the code and that all pages share |
| `build.py` | The site generator |
| `site/` | The built site. Do not edit it |
| `STYLE.md`, `instructions-svg.md` | The writer's guide and the diagram style guide |
| `plan.md`, `progress.md` | The project plan and the progress log |

## How the content is made

- The pages are written in <ASD-STE100 Simplified Technical English / plain English>.
- Each claim about the code has a citation to a file and line at the pinned commit.
- After a batch of pages is written, a separate review compares each claim with the code and corrects errors.
- <Out-of-scope parts, and why.>

The pages were written with Claude Code and reviewed against the source code.
This site is not an official project of the <Project> authors.
