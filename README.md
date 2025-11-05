# Solara Codex Foundry

Modern Solara playground showcasing a production-ready Primary Credit workspace
and reusable chat surface. The project now follows a single, extensible module
hierarchy rooted at `src/app`, making it easy to swap backends, adjust UI
primitives, or add new experiences without chasing cross-package imports.

## Project layout

```
src/app/
├── apps.py              # Solara entry points (e.g. proof-of-concept chat page)
├── core/                # Global styles and optional dependency helpers
├── models/              # Typed dataclasses for app, chat, and dataset state
├── services/            # Integrations (credentials, logging, storage, tasks)
├── state/               # Reactive controllers orchestrating UI + services
├── ui/                  # Chat surface, shared components, pages, and CSS
└── assets/static/       # Static images served by Solara
```

Top-level utilities such as `docs/`, `storage/`, and `tests/` remain at the
repository root. Tests import from the public `app` package, matching the new
module boundary.

## Getting started

### Install dependencies

```bash
uv sync
```

The project targets Python 3.12+. Optional dependencies such as `pandas` and
`ipyaggrid` are loaded defensively; the UI will gracefully degrade if they are
absent.

### Launch the Primary Credit workspace

Run the Solara development server pointing at the main page module:

```bash
uv run solara run src/app/ui/pages/main.py
```

Then open the printed URL (defaults to http://127.0.0.1:8765) to explore the
workspace. Runtime credentials (for example `PRIMARY_CREDIT_S3_BUCKET`) can be
configured through environment variables.

### Launch the standalone chat surface

```bash
uv run solara run src/app/apps.py:Page
```

This entry point wires the reusable chat controller, attestation gate, and mock
backend together for quick experimentation.

### Run tests and linters

```bash
uv run pytest
```

Additional tooling such as `ruff` or `mypy` can be executed via `uv run ruff` or
`uv run mypy` respectively, leveraging the consolidated `src/app` package.

## Extending the project

* **Swap chat backends** – Implement `ChatBackend` in `src/app/services/chat_backend.py`
  and pass it into `ChatController` during composition.
* **Augment state** – Add dataclasses to `src/app/models/app.py` and expose new
  reactive helpers within `src/app/state/app.py`.
* **Design new surfaces** – Assemble Solara pages under `src/app/ui/pages/` with
  building blocks from `src/app/ui/components/` and shared chat widgets in
  `src/app/ui/chat.py`.

The unified layout keeps models, controllers, services, and UI primitives in one
place, making future modules plug-and-play.
