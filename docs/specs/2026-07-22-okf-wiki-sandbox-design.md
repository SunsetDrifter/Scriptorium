# Design: okf-wiki — the live sandbox for Scriptorium field testing

Approved design, 2026-07-22. Status: agreed in discussion, pending build.

## Problem

Scriptorium's mechanical layer is tested (unit tests, per-variant lint), but its judgment layer — CLAUDE.md directives, workflows, the page-worthiness test, skill-wrapper dispatch (PR #7), the unattended maintenance loop — has never run against a live wiki. Prototypes therefore stall at "built but unproven" (PR #7's explicit state), and the project has no way to gather the usage evidence its own merge bar demands.

## Decision summary

| Question | Decision |
|---|---|
| Content | The OKF ecosystem itself: spec, upstream PRs, tools, our predictions. Churns weekly; we already work on it every session; public-safe. |
| Location | Separate repo, `SunsetDrifter/okf-wiki`, installed per the README steps. Real hooks, real CI, own history. |
| Template | `generic` variant from the `proto/skills-dispatch` branch, after extending that branch with generic-variant skill wrappers (same thin pattern as homelab's). |
| Test protocol | Ambient dogfood: real workflows during normal sessions, no staged scenarios. Plus one structured element: the weekly cron maintenance pass. |

## Components

1. **The repo.** `git init`, copy `generic/` from the extended prototype branch, install the pre-commit hook, `lint.py check` green on empty. A GitHub Actions workflow runs `lint.py check` on push (mirror of Scriptorium's CI shape).
2. **Seeding session (first dogfood).** Drop existing artifacts into `raw/inbox/`: the three `docs/research/` documents, the OKF usage-map notes, links to key upstream sources (SPEC.md, the PR queue, ecosystem posts). Then run the real `/triage` and ingest workflows to build sources/entities/concepts/synthesis pages. Seeding is itself the first test of triage, ingest, the page-worthiness test, and slash dispatch.
3. **Ongoing use.** Whenever OKF work happens in a session (spec checks, new upstream PRs, scoring the type-vocabulary predictions), it is filed into the wiki via workflows instead of into session memory or new Scriptorium research docs. Scriptorium's `docs/research/` remains the home only for decisions *about Scriptorium*.
4. **Cron maintenance.** Weekly unattended `maintenance pass` per the README crontab pattern, committing to the `maintenance` branch; review-and-merge happens in a normal session. First live exercise of the allowed-actions boundary.
5. **Feedback loop.** Observations about a prototype under test are posted as comments on the Scriptorium PR that carries it (evidence attaches to the decision). Graduation or closure of PR #7 is decided on that evidence.
6. **Privacy rule.** One convention line in the sandbox CLAUDE.md: public sources only; nothing about the maintainer's employer, private repos, or non-public work, ever.

## Deferred (recorded, not built now)

- **Community-implementations sweep**: research a broad set of third-party OKF implementations and wikis, file the findings as `raw/` sources for ingestion. Good second seeding wave once the wiki's routine works; also feeds the ecosystem-entity pages naturally.
- Scripted scenario injection (planted contradictions, back-dated pages): rejected for now — staged use doesn't test judgment, and lint tests already cover mechanics.

## Success criteria

- PR #7's dogfood questions get evidence-based answers (slash dispatch used or not; descriptions trigger sensibly; pairing check never misfires) within a few weeks of normal use.
- The maintenance loop runs unattended at least three times with its branch discipline intact.
- The wiki replaces the session-memory OKF watch list as the canonical place OKF knowledge accumulates.

## Non-goals

The sandbox is not a Scriptorium showcase, not upstream-citable collateral (though it may become that), and not a reason to add features to Scriptorium. Template changes still follow the normal scope rule; the sandbox only generates evidence.
