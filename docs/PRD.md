# Solara Chat POC – PRD v0.1

## Problem & Goal
Engineers need a high-performance Solara chat window with zero flicker/lag, streaming-friendly UI, per-message toolbars, and a compact file-backed attestation gate.

## MVP Scope
- One chat page with multi-line input; optimistic send + “thinking” bubble.
- Message = ordered list of typed blocks: string, image(path), table(dataframe-like), integer, plus metadata (generated Python code).
- Per-message toolbar: “View code” (expand/collapse), “Give feedback” (modal: minutes-saved slider, score slider, comments, submit).
- Attestation: check local file store; if absent, show gate once; configurable persistence.
- Clean component API so the chat widget is reusable and scalable.

## Non-Goals (v0)
- No CI/CD; no auth; no remote DB.

## Non-Functional
- No visible reflow/flicker on send or expand/collapse.
- Streaming-ready: placeholder/typing bubble; safe to swap in streaming later.
- Components responsive; keyboard accessible; 60fps interactions target.

## Acceptance (High-level)
- Send/receive round-trip with mock backend returns composite message.
- Expanding code panel doesn’t shift sibling messages jarringly.
- Feedback modal is per-message and independent; submits to local endpoint.
- Attestation persists; not shown again once accepted.
