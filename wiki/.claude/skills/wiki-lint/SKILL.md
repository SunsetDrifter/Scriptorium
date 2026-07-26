---
name: wiki-lint
description: Run the deterministic lint plus the judgment-only review pass. Use when the human says "lint the wiki".
---

Read `workflows/lint.md` from the wiki root and follow it exactly, step by step. Do not run the procedure from memory; the workflow file is the source of truth and may have changed since you last read it. `python3 lint.py check` verifies this wrapper stays paired with its workflow.
