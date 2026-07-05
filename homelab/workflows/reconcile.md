# Reconcile

Triggered by "reconcile <page>" or by lint flagging a long-unreconciled contested page. Contested is a state to exit, not a resting place: this workflow resolves the disagreement and records what lost.

1. **Gather the conflict.** Read the page and every source it cites. List each competing claim with its source and the source's date.
2. **Propose a resolution.** Rank claims by source recency first, then source authority (primary sources over secondary, the human's direct word over both). State which claim should win and why, show the proposed rewrite, and wait for approval.
3. **Rewrite in place.** The winning claim goes in the main body, stated plainly. Each losing claim moves to a "Superseded claims" section at the bottom: one dated line per claim with its source and a one-line rationale for why it lost. Never silently delete the loser.
4. **Update frontmatter.** Remove `confidence: contested` (downgrade to `low` instead if the winner is itself uncited). Bump `updated` and refresh `description` if the page's conclusion changed.
5. **Check the neighbors.** Follow the page's wikilinks one hop out. Any page repeating the losing claim gets the same treatment in this session.
6. **Lint, log, commit.** Run `python3 lint.py check`, append to `log.md`, commit: `reconcile: <page>`.

Log entry format:

```
## [2026-07-05] reconcile | zero-trust-networking
- winner: sources/formal-verification-paper.md (2026-05)
- superseded: claim from sources/early-blog-post.md, moved to Superseded claims
- neighbors updated: concepts/microsegmentation.md
```
