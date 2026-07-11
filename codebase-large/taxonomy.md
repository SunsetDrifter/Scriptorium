---
type: tooling
---

# Tag taxonomy

Every `tags:` value on every page must appear here. Introducing a new tag means adding it to this list in the same commit, with a one-line meaning. Keep tags few and general; if two tags mean nearly the same thing, merge them. `lint.py check` warns on tags missing from this file and reports listed tags no page uses.

- auth — identity, sessions, access control
- database — storage, schemas, migrations
- api — external and internal API surfaces
- infra — deployment, CI, environments
- testing — test strategy, fixtures, coverage
- performance — latency, throughput, resource use
- tooling — build systems, codegen, developer tooling
