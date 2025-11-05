# Solara Codex Foundry

Unified workspace for Solara component experiments and reference applications.

## Project layout

The repository now follows a conventional `src/` structure with clear package
boundaries:

```
src/solara_codex_foundry/
├── apps/                 # Ready-to-run Solara entry points
├── assets/               # Static assets shared by applications
├── chat/                 # Reusable chat components, state, and backends
└── primary_credit/       # Primary Credit reference application
    ├── components/       # Page-level and layout components
    ├── core/             # Application state, gates, and shared helpers
    ├── pages/            # Solara pages that wire the experience together
    ├── services/         # External integrations (storage, telemetry, etc.)
    └── styles/           # CSS used by the application
```

Top-level automated tests now live under `tests/`, mirroring the public package
API (`solara_codex_foundry`). Supporting configuration files remain at the
repository root (for example `codex/`, `docs/`, and `storage/`).

## Running the tests

```
uv run pytest
```