# okf-wiki Sandbox Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the `okf-wiki` field-test sandbox per `docs/specs/2026-07-22-okf-wiki-sandbox-design.md`: generic-variant wiki about the OKF ecosystem, installed from the `proto/skills-dispatch` branch, with CI, cron maintenance, and a seeded first session.

**Architecture:** Two repos. Scriptorium's `proto/skills-dispatch` branch gains generic-variant skill wrappers (mirroring homelab's, one per workflow, enforced by the existing `check_skills`). A new standalone repo `okf-wiki` is installed from that branch per the README install steps, gets a lint CI gate and a weekly cron maintenance entry, then is seeded in an interactive session using the wiki's own workflows.

**Tech Stack:** stdlib Python (wikilint), git + gh CLI, GitHub Actions, cron, Claude Code (skills + `claude -p` for maintenance).

## Global Constraints

- Wiki prose style: no em dashes; plain direct English (per variant CLAUDE.md style rules). The em dash in taxonomy/skill list entries is a separator token, not prose.
- All internal wiki links are bundle-absolute: `[title](/dir/page.md)` (ADR 0001).
- Sandbox content rule: public sources only; never the maintainer's employer, private repos, or non-public work.
- Scriptorium work happens on branch `proto/skills-dispatch` (Tasks 1) — NOT main. okf-wiki work happens in `~/Development/okf-wiki`.
- `wikilint/` stays byte-identical across all four variants (no engine changes in this plan; Task 1 is config + files only).

---

### Task 1: Generic-variant skill wrappers (Scriptorium, `proto/skills-dispatch` branch)

**Files:**
- Create: `generic/.claude/skills/<name>/SKILL.md` for each of `triage`, `ingest`, `query`, `lint`, `reconcile`, `maintain`
- Modify: `generic/lint.py` (lines 14-17 area: `non_page_allowed`; add `skills_dir` key near `raw_dir`)
- Modify: `generic/CLAUDE.md` (one line after the workflows trigger table)

**Interfaces:**
- Consumes: `check_skills` and the `skills_dir` knob, already on this branch (`generic/wikilint/checks.py`, `settings.py`).
- Produces: a `generic/` template whose copy is a working skills-dispatch wiki; Task 2 copies this directory verbatim.

- [ ] **Step 1: Confirm branch and a red baseline**

Run: `git checkout proto/skills-dispatch && cd generic && python3 -c "
import lint" 2>/dev/null; cd ..`
Then temporarily prove the check would fire: add `"skills_dir": ".claude/skills",` to `generic/lint.py` right below the `"raw_dir": "raw",` line, with this comment line above it:

```python
    # Claude Code skill wrappers pair 1:1 with workflows/ (check_skills).
    "skills_dir": ".claude/skills",
```

Also extend `non_page_allowed` line 16 to end with `".claude",`:

```python
        "raw", "workflows", ".git", ".gitignore", ".githooks", ".claude",
```

Run: `cd generic && python3 lint.py check; cd ..`
Expected: 6 errors, one per workflow: `[skills] workflows/<name>.md: no skill wrapper; add .claude/skills/<name>/SKILL.md pointing at it`

- [ ] **Step 2: Create the six wrappers**

Create each `generic/.claude/skills/<name>/SKILL.md` with exactly this shape (shared body, per-skill frontmatter):

`generic/.claude/skills/triage/SKILL.md`:
```markdown
---
name: triage
description: Triage the raw inbox of this wiki. Use when the human says "triage the inbox" or "process the inbox", or drops files into raw/inbox/ and asks to sort them.
---

Read `workflows/triage.md` from the wiki root and follow it exactly, step by step. Do not run the procedure from memory; the workflow file is the source of truth and may have changed since you last read it. `python3 lint.py check` verifies this wrapper stays paired with its workflow.
```

The other five differ only in `name:`, `description:`, and the workflow path in the body:

- `ingest`: description `Ingest one raw source into the wiki: source page, affected pages, new pages where warranted. Use when the human says "ingest <source>".` Body references `workflows/ingest.md`.
- `query`: description `Answer a question from the wiki, scanning frontmatter and the index before opening page bodies. Use for any question answerable from the wiki.` Body references `workflows/query.md`.
- `lint`: description `Run the deterministic lint plus the judgment-only review pass. Use when the human says "lint the wiki".` Body references `workflows/lint.md`.
- `reconcile`: description `Resolve a contested page: weigh the disagreeing sources and rewrite latest-evidence-first. Use when the human says "reconcile <page>".` Body references `workflows/reconcile.md`.
- `maintain`: description `Run or review the unattended maintenance pass on the maintenance branch. Use when the human says "maintenance pass" or "review maintenance".` Body references `workflows/maintain.md`.

- [ ] **Step 3: Verify green**

Run: `cd generic && python3 lint.py check; cd ..`
Expected: `0 errors` (warnings about missing index/log are pre-existing template state).
Run: `python3 -m unittest discover tests`
Expected: `OK` (81 tests; the parity allowlist already covers `skills_dir`).

- [ ] **Step 4: Add the CLAUDE.md dispatch note**

In `generic/CLAUDE.md`, immediately after the workflows table's last row (`| "maintenance pass" / "review maintenance" | \`workflows/maintain.md\` |`), add a blank line then:

```markdown
In Claude Code each workflow is also a skill wrapper under `.claude/skills/`, so `/ingest`, `/triage`, etc. dispatch the same files deterministically; lint errors when a wrapper and its workflow drift apart.
```

Run: `cd generic && python3 lint.py check; cd ..`
Expected: `0 errors`, and no `hot-core` warning (the line budget holds).

- [ ] **Step 5: Commit and push**

```bash
git add generic/
git commit -m "proto: generic-variant skill wrappers for the okf-wiki sandbox"
git push
```

---

### Task 2: Create and install the okf-wiki repo

**Files:**
- Create: `~/Development/okf-wiki/` (full copy of `generic/` from the branch)
- Create: `~/Development/okf-wiki/log.md`, regenerated `index.md`

**Interfaces:**
- Consumes: the `generic/` template as left by Task 1.
- Produces: a GitHub repo `SunsetDrifter/okf-wiki` (public) whose clone lints clean; Tasks 3-5 operate inside it.

- [ ] **Step 1: Install per the README steps**

```bash
mkdir ~/Development/okf-wiki && cd ~/Development/okf-wiki && git init
cp -R ~/Development/Scriptorium/generic/ .
git config core.hooksPath .githooks
mkdir -p raw/inbox
```

- [ ] **Step 2: Give it a log and an index (silences the two template warnings)**

Create `log.md`:
```markdown
# Log

## 2026-07-22

- **Init**: installed the generic variant from Scriptorium proto/skills-dispatch as the OKF-ecosystem field-test wiki.
```

Run: `python3 lint.py rebuild-index`
Expected: `index.md rebuilt: 0 entries`

- [ ] **Step 3: Verify clean and hook active**

Run: `python3 lint.py check`
Expected: `checked 0 pages`, `0 errors, 0 warnings` (info lines about unused tags are fine).

- [ ] **Step 4: First commit and publish**

```bash
git add -A
git commit -m "init: generic Scriptorium variant, OKF-ecosystem sandbox"
gh repo create SunsetDrifter/okf-wiki --public --source . --push
```
Expected: repo URL printed; `git push` succeeds via the create command.

---

### Task 3: CI lint gate

**Files:**
- Create: `~/Development/okf-wiki/.github/workflows/lint.yml`

**Interfaces:**
- Consumes: the repo from Task 2.
- Produces: a green Actions run on every push; later tasks assume pushes are gated.

- [ ] **Step 1: Write the workflow**

`.github/workflows/lint.yml`:
```yaml
name: lint
on: [push, pull_request]
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: python3 lint.py check
```

- [ ] **Step 2: Commit, push, watch**

```bash
git add .github && git commit -m "ci: lint gate" && git push
gh run watch --exit-status
```
Expected: run completes with success.

---

### Task 4: Sandbox conventions (privacy line)

**Files:**
- Modify: `~/Development/okf-wiki/CLAUDE.md` (this copy is the wiki's own, co-owned file; editing it here does not touch the Scriptorium template)

**Interfaces:**
- Consumes: repo from Task 2.
- Produces: the standing content rule every future session operates under.

- [ ] **Step 1: Add the rule**

In `CLAUDE.md`, append a new numbered prime directive at the end of the "Prime directives" list:

```markdown
8. **Public sources only.** This wiki documents the public OKF ecosystem. Never file anything about the human's employer, private repositories, or non-public work; refuse and remind them where private notes belong.
```

- [ ] **Step 2: Lint, commit, push**

```bash
python3 lint.py check && git add CLAUDE.md && git commit -m "docs: public-sources-only prime directive" && git push
```
Expected: lint 0 errors (CLAUDE.md stays under the hot-core cap); push green in CI.

---

### Task 5: Weekly cron maintenance

**Files:**
- Modify: user crontab (no repo files)

**Interfaces:**
- Consumes: repo from Task 2; `workflows/maintain.md` from the template.
- Produces: unattended weekly maintenance commits on the `maintenance` branch.

- [ ] **Step 1: Dry-run the maintenance pass once, manually**

```bash
cd ~/Development/okf-wiki && claude -p "maintenance pass" --permission-mode acceptEdits
```
Expected: the run creates/uses the `maintenance` branch, performs allowed actions only (on an empty wiki, likely a no-op report), and leaves main untouched. Inspect with `git log --oneline maintenance` and `git branch`.

- [ ] **Step 2: Install the crontab entry**

```bash
(crontab -l 2>/dev/null; echo '0 3 * * 1 cd ~/Development/okf-wiki && claude -p "maintenance pass" --permission-mode acceptEdits') | crontab -
crontab -l | tail -1
```
Expected: the line prints back. (Mondays 03:00; the machine must be awake for cron to fire on macOS; a missed week is acceptable for a sandbox.)

---

### Task 6: Seeding session (interactive; do NOT delegate to a subagent)

This task is the first joint dogfood session and must run with the human present, inside `~/Development/okf-wiki` in Claude Code, using the wiki's own dispatch.

**Files:**
- Create: files under `~/Development/okf-wiki/raw/inbox/` then wiki pages via workflows

**Interfaces:**
- Consumes: everything above.
- Produces: the seeded wiki; observations for Scriptorium PR #7.

- [ ] **Step 1: Stage the raw inputs into `raw/inbox/`**

Copy from Scriptorium (public artifacts only):
```bash
cp ~/Development/Scriptorium/docs/research/2026-07-20-scientific-testing-variant-schema.md \
   ~/Development/Scriptorium/docs/research/2026-07-21-claude-md-vs-okf-reference-agent.md \
   ~/Development/Scriptorium/docs/research/2026-07-22-okf-type-vocabulary-position.md \
   ~/Development/okf-wiki/raw/inbox/
```
Also create `raw/inbox/okf-upstream-links.md` listing the key public sources, one URL per line with a one-line note each: the OKF SPEC.md raw URL, the knowledge-catalog PR queue URL, the PRs of record (#48, #66, #110, #125, #159, #165, #184, #186, #188, #189, #192, #195, #206), the Google Cloud OKF blog post, the OpenWiki 0.2 announcement, and the Karpathy LLM-wiki coverage links gathered on 2026-07-21.

- [ ] **Step 2: Run the real workflows, by slash dispatch**

In a Claude Code session in the wiki: `/triage`, approve the plan, then `/ingest` one source at a time. This is deliberately manual: it is the field test of triage, ingest, the page-worthiness test, and the wrappers.

- [ ] **Step 3: File the first observations**

After the session, post a comment on Scriptorium PR #7 answering, from actual use: were slash commands used or bypassed; did any skill trigger at the wrong time; did the pairing check interfere; did the page-worthiness test block or admit correctly.

---

## Self-review notes

Spec coverage: component 1 → Tasks 2-3; component 2 → Task 6; component 3 → ongoing (out of plan scope by design); component 4 → Task 5; component 5 → Task 6 Step 3; component 6 → Task 4; deferred items correctly absent. Type consistency: n/a (no new code interfaces; wrapper text matches homelab's shipped pattern). No placeholders remain.
