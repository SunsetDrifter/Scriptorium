"""Functional tests for every mechanical check, including regression tests
for each defect found in the 2026-07-05 review."""

import tempfile
import unittest
from pathlib import Path

from helpers import DAYS_AGO_41, DAYS_AGO_95, TODAY, findings, gather, make_wiki, page, use_variant


class WikiTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = self._tmp.name


class TestFrontmatter(WikiTest):
    def test_valid_page_passes(self):
        root = make_wiki(self.tmp, files={
            "concepts/alpha-note.md": page("concept", "A note.", body="See body.\n"),
        })
        report = gather(root)
        self.assertEqual(findings(report, "frontmatter"), [])

    def test_missing_frontmatter_and_bad_type(self):
        root = make_wiki(self.tmp, files={
            "concepts/no-fm.md": "just prose\n",
            "concepts/bad-type.md": page("nonsense", "Bad type."),
        })
        report = gather(root)
        self.assertEqual(len(findings(report, "frontmatter", "ERROR")), 2)

    def test_empty_required_list_is_missing(self):
        # Review regression: [] used to pass the required-field check.
        root = make_wiki(self.tmp, files={
            "concepts/empty-tags.md": page("concept", "Empty tags.", tags=""),
        })
        (root / "concepts/empty-tags.md").write_text(
            "---\ntype: concept\ncreated: 2026-07-01\nupdated: 2026-07-01\n"
            "description: Empty tags.\ntags:\nsources: []\n---\n\nBody.\n"
        )
        report = gather(root)
        messages = [m for _, c, _, m in findings(report, "frontmatter", "ERROR")]
        self.assertTrue(any("required field: tags" in m for m in messages))

    def test_invalid_confidence_and_date_order(self):
        root = make_wiki(self.tmp, files={
            "concepts/bad.md": page("concept", "Bad.", extra_fm="confidence: high\n",
                                    created="2026-07-02", updated="2026-07-01"),
        })
        report = gather(root)
        messages = [m for _, c, _, m in findings(report, "frontmatter", "ERROR")]
        self.assertTrue(any("confidence" in m for m in messages))
        self.assertTrue(any("older than created" in m for m in messages))


class TestBodyExtraction(WikiTest):
    def test_trailing_space_delimiter_keeps_body(self):
        # Review regression: "--- " closing line used to empty the body,
        # silently skipping body checks and false-erroring mermaid pages.
        use_variant("homelab")
        root = make_wiki(self.tmp, variant="homelab", files={
            "topology/lan.md": (
                "---\ntype: topology\ncreated: 2026-07-01\nupdated: 2026-07-01\n"
                "description: LAN map.\ntags: [alpha]\nsources: []\nscope: l2\n"
                "includes: [topology/lan.md]\n--- \n\n```mermaid\nflowchart LR\n  a[A] --> b[B]\n```\n"
            ),
        })
        report = gather(root)
        self.assertEqual(findings(report, "mermaid", "ERROR"), [])


class TestLinksAndOrphans(WikiTest):
    def test_broken_wikilink_and_orphan_hint(self):
        root = make_wiki(self.tmp, files={
            "concepts/alpha-note.md": page("concept", "A note.", body="See [[missing-page]].\n"),
            "queries/orphan-question.md": page("query", "Nobody links here."),
            "synthesis/mentioner.md": page(
                "synthesis", "Mentions the orphan.",
                body="The orphan question came up in prose.\nAlso [[alpha-note]].\n",
            ),
        })
        report = gather(root)
        self.assertEqual(len(findings(report, "wikilink", "ERROR")), 1)
        orphan_infos = [m for _, _, p, m in findings(report, "orphan", "INFO")
                        if p == "queries/orphan-question.md"]
        self.assertTrue(any("mentioned unlinked in synthesis/mentioner.md" in m
                            for m in orphan_infos))

    def test_self_reference_does_not_hide_orphan(self):
        # Review regression: a frontmatter self-reference used to count as inbound.
        root = make_wiki(self.tmp, files={
            "concepts/self-ref.md": page("concept", "Self referencing.",
                                         extra_fm="supersedes: [concepts/self-ref.md]\n"),
        })
        report = gather(root)
        orphans = [p for _, _, p, _ in findings(report, "orphan", "WARNING")]
        self.assertIn("concepts/self-ref.md", orphans)


class TestMembership(WikiTest):
    def test_active_component_outside_topology_flagged(self):
        # Review regression: the old "topology orphans" rule had been dropped.
        component = page("component", "A switch.", tags="[alpha]",
                         extra_fm="component_kind: device\nstatus: active\n"
                                  f"last_verified: {TODAY}\ndepends_on: []\n")
        root = make_wiki(self.tmp, variant="homelab", files={
            "components/switch-01.md": component,
            "components/router-01.md": component.replace("A switch.", "A router linking [[switch-01]]."),
        })
        report = gather(root)
        flagged = [p for _, _, p, _ in findings(report, "membership", "WARNING")]
        self.assertIn("components/switch-01.md", flagged)

    def test_included_component_passes(self):
        root = make_wiki(self.tmp, variant="homelab", files={
            "components/switch-01.md": page(
                "component", "A switch.",
                extra_fm="component_kind: device\nstatus: active\n"
                         f"last_verified: {TODAY}\ndepends_on: []\n"),
            "topology/lan.md": page(
                "topology", "LAN.", extra_fm="scope: l2\nincludes: [components/switch-01.md]\n",
                body="```mermaid\nflowchart LR\n  a[A] --> b[B]\n```\n"),
        })
        report = gather(root)
        self.assertEqual(findings(report, "membership"), [])


class TestTagsContestedInferred(WikiTest):
    def test_unknown_and_unused_tags(self):
        root = make_wiki(self.tmp, files={
            "concepts/tagged.md": page("concept", "Tagged.", tags="[gamma]"),
        })
        report = gather(root)
        self.assertEqual(len(findings(report, "tags", "WARNING")), 1)
        self.assertEqual(len(findings(report, "tags", "INFO")), 2)  # alpha, beta unused

    def test_long_contested_flagged(self):
        root = make_wiki(self.tmp, files={
            "concepts/old-fight.md": page("concept", "Long contested.",
                                          extra_fm="confidence: contested\n",
                                          created=DAYS_AGO_41, updated=DAYS_AGO_41),
        })
        report = gather(root)
        self.assertEqual(len(findings(report, "contested", "WARNING")), 1)

    def test_inferred_without_low_confidence(self):
        root = make_wiki(self.tmp, files={
            "concepts/guess.md": page("concept", "Guesswork.",
                                      body="Acme adopted it (inferred).\n"),
        })
        report = gather(root)
        self.assertEqual(len(findings(report, "provenance", "WARNING")), 1)


class TestSecretsAndLog(WikiTest):
    def test_secret_flagged_with_line(self):
        root = make_wiki(self.tmp, files={
            "concepts/leaky.md": page("concept", "Leaky.", body="password: hunter2\n"),
        })
        report = gather(root)
        hits = findings(report, "secrets", "ERROR")
        self.assertEqual(len(hits), 1)
        self.assertIn(":", hits[0][2])  # path:line

    def test_bad_log_header(self):
        root = make_wiki(self.tmp)
        (root / "log.md").write_text("# Log\n\n## bad header\n")
        report = gather(root)
        self.assertEqual(len(findings(report, "log", "WARNING")), 1)


class TestPinningAndDrift(WikiTest):
    def _index_head(self):
        return (
            "# Index\n\nExample block first:\n\n```yaml\ntype: concept\n```\n\n"
            "```yaml\nrepo: github.com/x/y\nlocal_path: ~/nonexistent\n"
            "default_branch: main\nlast_synced_commit: 'e4f5g6h'\n"
            "last_synced_at: 2026-07-01\nwiki_scope:\n  include:\n    - libs\n"
            "  exclude: [vendor/]\n```\n"
        )

    def test_pinning_quotes_block_lists_and_decoy_fence(self):
        # Review regression: quoted commits, block lists, and an earlier yaml
        # fence all silently corrupted the pinning data.
        use_variant("codebase")
        root = make_wiki(self.tmp, variant="codebase")
        (root / "index.md").write_text(self._index_head())
        from wikilint.model import parse_index_pinning
        pinning = parse_index_pinning(root)
        self.assertEqual(pinning["last_synced_commit"], "e4f5g6h")
        self.assertEqual(pinning["wiki_scope"]["include"], ["libs"])
        self.assertEqual(pinning["wiki_scope"]["exclude"], ["vendor/"])

    def test_sync_drift_uses_unquoted_commit(self):
        module = page("module", "Auth module.", tags="[alpha]",
                      extra_fm="source_path: libs/auth/\nlanguage: go\nstatus: active\n"
                               "depends_on: []\nlast_verified_commit: e4f5g6h\n"
                               f"last_verified: {TODAY}\n")
        root = make_wiki(self.tmp, variant="codebase",
                         files={"modules/auth.md": module})
        (root / "index.md").write_text(self._index_head())
        report = gather(root)
        # commit matches the (unquoted) pinning value -> no spurious drift
        self.assertEqual(findings(report, "sync-drift"), [])


class TestReverseDeps(WikiTest):
    def test_all_relationship_fields_reversed(self):
        # Review regression: only depends_on used to be derivable.
        use_variant("codebase")
        from wikilint.settings import CONFIG
        for field in ("defined_in", "modules", "exposes", "consumes",
                      "producers", "consumers", "depends_on"):
            self.assertIn(field, CONFIG["reverse_fields"])
        root = make_wiki(self.tmp, variant="codebase", files={
            "modules/auth.md": page(
                "module", "Auth.", extra_fm="source_path: libs/auth/\nlanguage: go\n"
                f"status: active\ndepends_on: []\nlast_verified_commit: abc\nlast_verified: {TODAY}\n"),
            "apis/auth-http.md": page(
                "api", "Auth API.", extra_fm="api_kind: http\ndefined_in: modules/auth.md\n"
                "stability: stable\nlast_verified_commit: abc\n"),
        })
        from wikilint.derived import derive_reverse_edges
        from wikilint.model import discover_pages, Report
        pages = discover_pages(root, Report())
        reverse = derive_reverse_edges(pages)
        self.assertEqual(reverse["defined_in"].get("modules/auth.md"), ["apis/auth-http.md"])


class TestIndexAndSize(WikiTest):
    def test_rebuild_clears_drift(self):
        root = make_wiki(self.tmp, files={
            "concepts/alpha-note.md": page("concept", "A note."),
        })
        report = gather(root)
        self.assertEqual(len(findings(report, "index", "WARNING")), 1)
        from wikilint.derived import rebuild_index
        rebuild_index(root)
        report = gather(root)
        self.assertEqual(findings(report, "index"), [])

    def test_hot_core_cap(self):
        root = make_wiki(self.tmp)
        (root / "CLAUDE.md").write_text("x\n" * 200)
        report = gather(root)
        self.assertEqual(len(findings(report, "hot-core", "WARNING")), 1)


class TestAdrsAndStaleness(WikiTest):
    def test_adr_gap_and_missing_forward_link(self):
        adr = page("adr", "Choose postgres.", tags="[alpha]",
                   extra_fm="adr_number: 0001\nstatus: superseded\ndate: 2026-07-01\n")
        adr3 = page("adr", "Choose sqlite.", tags="[alpha]",
                    extra_fm="adr_number: 0003\nstatus: accepted\ndate: 2026-07-02\n")
        root = make_wiki(self.tmp, variant="codebase", files={
            "adrs/0001-choose-postgres.md": adr,
            "adrs/0003-choose-sqlite.md": adr3,
        })
        report = gather(root)
        self.assertEqual(len(findings(report, "adr", "ERROR")), 1)    # no forward link
        self.assertEqual(len(findings(report, "adr", "WARNING")), 1)  # gap 0002

    def test_last_verified_staleness(self):
        root = make_wiki(self.tmp, variant="homelab", files={
            "components/old-box.md": page(
                "component", "Old box.",
                extra_fm="component_kind: host\nstatus: active\n"
                         f"last_verified: {DAYS_AGO_95}\ndepends_on: []\n"),
        })
        report = gather(root)
        self.assertEqual(len(findings(report, "staleness", "WARNING")), 1)


class TestCoverage(WikiTest):
    def test_coverage_anchored_and_grouped_by_subsystem(self):
        # Review regressions: 'src' used to cover 'src-utils'; no subsystem view.
        use_variant("codebase-large")
        repo = Path(self.tmp) / "fakerepo"
        (repo / "libs" / "auth").mkdir(parents=True)
        (repo / "libs" / "auth-extra").mkdir(parents=True)
        wiki = Path(self.tmp) / "wiki"
        wiki.mkdir()
        module = page(
            "module", "Auth.",
            extra_fm="subsystem: auth\nsource_path: libs/auth\nlanguage: go\n"
                     "status: active\ncriticality: load-bearing\ndepends_on: []\n"
                     f"last_verified_commit: abc\nlast_verified: {TODAY}\n"
                     "verification_method: full\n")
        root = make_wiki(str(wiki), variant="codebase-large",
                         files={"subsystems/auth/modules/auth.md": module})
        (root / "index.md").write_text(
            f"```yaml\nrepo: x\nlocal_path: {repo}\nlast_synced_commit: abc\n"
            "wiki_scope:\n  include: [libs/]\n  exclude: []\n```\n"
        )
        from wikilint.derived import run_coverage
        run_coverage(root)
        coverage = (root / "coverage.md").read_text()
        self.assertIn("## Module pages by subsystem", coverage)
        self.assertIn("auth: 1 module pages (1 load-bearing)", coverage)
        self.assertIn("uncovered: `libs/auth-extra`", coverage)
        self.assertIn("1/2 first-level directories covered (50%)", coverage)


if __name__ == "__main__":
    unittest.main()
