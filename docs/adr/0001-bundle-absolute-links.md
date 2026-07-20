# Internal wiki links are bundle-absolute, not file-relative

All internal links in every wiki variant use bundle-absolute targets (`[proxmox-01](/components/proxmox-01.md)`, resolved against the wiki root), one of the two link styles OKF v0.1 permits. We keep this despite discovering (2026-07-20) that Google's own OKF reference tooling and GitHub's renderer only follow file-relative links, because one canonical spelling per target is worth more to an agent-operated wiki than out-of-the-box rendering.

## Considered Options

- **Bundle-absolute (chosen).** Every reference to a page is spelled identically regardless of which file contains it, so `grep '/components/proxmox-01.md'` finds all inbound references with zero ambiguity, links survive moving the *linking* file, and the lint engine resolves them with no per-file context. These properties directly serve the wikis' primary consumers: agents and `wikilint/`.
- **File-relative (rejected).** Renders on GitHub and works unpatched with Google's reference visualizer (`knowledge-catalog` `okf/src/reference_agent/viewer/generator.py` silently drops leading-`/` targets — its own spec allows them; Google's sample bundles switched to file-relative on 2026-06-13 for GitHub rendering). But links become context-dependent (`../components/...`), moving a page breaks its outbound links, and there is no single greppable spelling per target.

## Consequences

- Wiki links 404 when browsed on github.com and produce edge-less graphs in Google's unpatched visualizer. Treat external rendering as a conversion/tooling concern (the visualizer needs a ~3-line patch to resolve leading-`/` targets against the bundle root), not an authoring concern.
- Still conformant OKF: the spec supports both styles. If a future OKF version drops bundle-absolute links, revisit this ADR.
- The convention is load-bearing in `wikilint/derived.py` (index generation emits `[Title](/path.md)`), link resolution in `wikilint/checks.py`, each variant's `CLAUDE.md` linking rule, and tests — a reversal is a coordinated migration across all four variants plus existing wiki content.
