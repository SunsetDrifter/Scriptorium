---
name: wiki-verify
description: Reality-check wiki pages against the actual infrastructure. Use when the human says "verify components" or "verify <component>".
---

Read `workflows/verify.md` from the wiki root and follow it exactly, step by step. Do not run the procedure from memory; the workflow file is the source of truth and may have changed since you last read it. `python3 lint.py check` verifies this wrapper stays paired with its workflow.
