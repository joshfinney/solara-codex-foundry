Guidance for code-reading:
- Enumerate Solara’s state primitives and render triggers.
- Identify where list reconciliation depends on keys; document key strategy.
- Track how event handlers schedule updates; note any debounce/throttle hooks.
- Map where CSS/layout can cause reflow; propose CSS containment where helpful.
- Provide minimal repros in /scratch/ to verify hypotheses before wiring into the component.
Deliver short, well-structured notes with code references and file paths.
