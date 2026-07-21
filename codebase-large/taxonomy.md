---
type: tooling
---

# Taxonomy

Every `tags:` value on every page must appear in the tag list below. Introducing a new tag means adding it here in the same commit, with a one-line meaning. Keep tags few and general; if two tags mean nearly the same thing, merge them. `lint.py check` warns on tags missing from this file and reports listed tags no page uses.

- auth — identity, sessions, access control
- database — storage, schemas, migrations
- api — external and internal API surfaces
- infra — deployment, CI, environments
- testing — test strategy, fixtures, coverage
- performance — latency, throughput, resource use
- tooling — build systems, codegen, developer tooling

## Page types

Every page `type:` the schema allows is described here with a one-line meaning, so any OKF consumer can learn this bundle's vocabulary without reading the lint config. The authoritative schema lives in `lint.py`; `lint.py check` warns when the two drift.

- subsystem — a subsystem entry point: mission, owners, key pages
- owners — the ownership record for one subsystem
- module — one module, package, or library in the repo
- service — one deployable service or process
- api — an API surface: HTTP routes, gRPC, CLI, or public functions
- data-model — a schema, type, database table, or message format
- architecture — a diagram page: dependency graph, data flow, or deployment
- adr — an append-only architecture decision record
- concept — a pattern, protocol, or domain concept
- runbook — how to build, test, deploy, debug, or recover
- postmortem — something that broke in production and why
- synthesis — a cross-cutting analysis or refactor proposal
- source — a summary page for one raw source
- query — a filed answer worth keeping
