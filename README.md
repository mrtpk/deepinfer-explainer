# DeepInfer Explained

A static website that teaches the [DeepInfer](https://github.com/deepseek-ai/DeepInfer) codebase step by step.
DeepInfer is DeepSeek's inference framework for DeepSeek-V4.1-Flash on NVIDIA SM100 GPUs and Huawei Ascend NPUs.

The site is for a reader who knows Python but knows little about machine learning.
Each page starts with a simple explanation. Then a "Deep dive" gives the full detail for study:
tensor shapes, memory layouts, algorithms, edge cases and environment variables.

> **Status:** work in progress. Pages that are not written yet show as "soon" in the menu.
> See [`progress.md`](progress.md) for the current state.

## Code version

The site explains one exact version of DeepInfer:

| | |
|---|---|
| Commit | [`9bd9cf243fc53ef9afbf8f04d391d989117d6ab9`](https://github.com/deepseek-ai/DeepInfer/tree/9bd9cf243fc53ef9afbf8f04d391d989117d6ab9) |
| Date | 2026-10-21 |

All code excerpts and `file:line` links point to this commit. Line numbers can be different in newer versions.
To get the same code:

```bash
git clone https://github.com/deepseek-ai/DeepInfer.git
cd DeepInfer
git checkout 9bd9cf243fc53ef9afbf8f04d391d989117d6ab9
git submodule update --init --recursive
```

## Read the site

Open `site/index.html` in a browser. The site works from disk (`file://`), with no server.
It needs an internet connection only for the Inter font. Without it, the site uses a system font.

The site has five parts:

| Part | Folder | What it contains |
|---|---|---|
| Learn the basics | `learn/` | LLMs, tokens, attention, the KV cache, sampling, batching, GPUs, parallelism, MoE, number formats |
| DeepInfer concepts | `concepts/` | Each idea in DeepInfer and the files that use it |
| Guided tours | `tours/` | Step-by-step tours through real code, for example "Life of a request" |
| Code map | `code/` | A folder tree and one page for each important module |
| Reference | `reference/` | Environment variables, config classes, the C++ engine API, the glossary, the FAQ |

Some pages have interactive visuals, for example a paged KV cache allocator.
Press `/` to search. Point to a dotted word to see its glossary definition.

## Build the site

Requirements:
- Python 3.11 or newer. The build uses only the standard library.
- A checkout of DeepInfer at the commit above, in a folder next to this one:

```
parent/
  DeepInfer/              # git checkout at 9bd9cf2 (read only)
  deepinfer-explainer/    # this repository
```

Commands:

```bash
cd deepinfer-explainer
python3 build.py                   # build site/ from src/
python3 build.py --strict          # also stop on warnings
python3 build.py --force-diagrams  # run all diagram scripts again
```

The build reads code excerpts directly from `../DeepInfer`, so each excerpt is exact.
It stops with an error if DeepInfer is at a different commit, or if a link, a code citation or a glossary term is wrong.

## Repository layout

| Path | Contents |
|---|---|
| `src/` | Page sources (HTML fragments with a small header), navigation (`src/nav/`) and glossary (`src/glossary/`) |
| `diagrams/` | One Python script for each SVG diagram, and the shared helper `svglib.py` |
| `assets/` | Site CSS and JavaScript, and the interactive visuals (`assets/viz/`) |
| `tools/` | Generators, for example `gen_env_vars.py` for the environment-variable tables |
| `notes/facts.md` | Facts that were checked in the code and that all pages share |
| `build.py` | The site generator |
| `site/` | The built site. Do not edit: the build writes it again each time |
| `STYLE.md` | The writer's guide: page templates, tags, writing rules, accuracy rules |
| `instructions-svg.md` | The style guide for diagrams |
| `plan.md`, `progress.md` | The project plan and the progress log |

## How the content is made

- The pages are written in ASD-STE100 (Simplified Technical English): short sentences and simple words.
- Each claim about the code has a citation to a file and line at the pinned commit.
- After a batch of pages is written, a separate review compares each claim with the code and corrects errors.
- The pages explain how DeepInfer calls its kernel libraries (FlashMLA, DeepGEMM, DeepEP, DeepSelect).
  They do not explain the inside of those libraries, because they are git submodules that are not part of this review.

The pages were written with Claude Code (Anthropic) and reviewed against the source code.
DeepInfer is a project of DeepSeek. This site is not an official DeepSeek project.
