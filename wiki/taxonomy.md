---
type: tooling
---

# Taxonomy

Every `tags:` value on every page must appear in the tag list below. Introducing a new tag means adding it here in the same commit, with a one-line meaning. Keep tags few and general; if two tags mean nearly the same thing, merge them. `lint.py check` warns on tags missing from this file and reports listed tags no page uses.

- example-tag — replace these entries with your domain's tags as pages accumulate

## Page types

Every page `type:` the schema allows is described here with a one-line meaning, so any OKF consumer can learn this bundle's vocabulary without reading the lint config. The authoritative schema lives in `lint.py`; `lint.py check` warns when the two drift.

- source — a summary page for one raw source, with its key claims
- entity — a person, company, product, place, or tool
- concept — an idea, framework, theory, or pattern
- synthesis — a cross-cutting analysis or comparison built from multiple sources
- query — a filed answer from a past exploration worth keeping
