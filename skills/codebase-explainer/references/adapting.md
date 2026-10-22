# Adapting to other kinds of projects

Read this when the target repo is not an ML project, not Python, or not on GitHub.

Part of the `codebase-explainer` skill. The single-file version of this playbook is `project-instructions.md` in the DeepInfer explainer repo. Placeholders: `{PROJECT}`, `{SHA}`, `{SHORT_SHA}`, `{REPO_URL}`, `{SITE_NAME}`.

## 11. Adapting to other kinds of projects

The process, tooling, look and rules stay the same. These parts change:

| Part | ML inference engine (DeepInfer) | Web framework / backend service | Compiler / language tool | Database / storage engine | CLI tool / library |
|---|---|---|---|---|---|
| Basics pages | LLM, tokens, attention, KV cache, sampling, GPUs, parallelism, number formats | HTTP, routing, middleware, ORM, async I/O, sessions, caching | lexing, parsing, AST, IR, passes, codegen, linking | pages, B-trees/LSM, WAL, transactions, MVCC, replication | the problem domain, the main data model, the main algorithm |
| Tour 1 | Life of a request (`generate()` → tokens) | Life of a request (socket → handler → response) | Life of a source file (text → binary) | Life of a query / a write | Life of one command (argv → output) |
| Other tours | start-up, one engine step, one layer, one spec-decode round, multi-GPU step | start-up, one middleware chain, one DB transaction | one optimisation pass, error reporting | recovery after a crash, compaction, one checkpoint | config loading, plugin loading |
| Visuals | allocator, scheduler, attention toy, router | request pipeline stepper, cache hit/miss sim | parser stepper, pass pipeline | B-tree insert/split, WAL replay, lock table | state machine stepper |
| Reference generators | env vars (`environ.py`), config classes, C++ API from `.pyi` | settings, routes, CLI flags, HTTP API (OpenAPI) | flags, IR ops table, diagnostics list | config keys, SQL functions, error codes | flags, public API from type stubs or docs |
| Code map pages | Python + C++ modules | packages / apps | compiler phases | storage, query, txn layers | modules |

For a **non-Python target repo**:
- Add its file extensions to `LANG_BY_EXT` and the Prism components to `PRISM_COMPONENTS`
  (for example `prism-rust`, `prism-go`, `prism-java`, `prism-typescript`). `lang="none"` works for any file.
- Write generators in Python (standard library) with regexes or the language's own tools run once into a
  JSON file in `notes/`. Keep `build.py` standard-library only.
- The "Line N" reading and the `<x-code>` rules stay the same.
- The tooling itself stays Python: it only reads text files from the checkout.

For a **non-GitHub host**: change `github_url()` (GitLab: `{base}/-/blob/{sha}/{path}#L{a}-{b}`;
Gitea: `{base}/src/commit/{sha}/{path}#L{a}-L{b}`) and the "GitHub ↗" label.

For a **repo with no comments in another language**: the `<x-tr>` tag stays unused. For comments in a
language other than Chinese, change the label in `build.py`.

For a **domain the reader already knows**: make the basics part short (3-5 pages) or merge it into the
first concept pages. Keep at least one page that explains the main data model.

For a **very large repo**: pin a subset in `plan.md` (for example one subsystem), say on the home page
what is out of scope, and keep the code map tree complete (it is cheap) while module pages cover only the
important modules.

---
