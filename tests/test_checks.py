"""Functional tests for every mechanical check, including regression tests
for each defect found in the 2026-07-05 review."""

import tempfile
import unittest
from pathlib import Path

from helpers import (
    DAYS_AGO_41, DAYS_AGO_95, TODAY, findings, gather, make_wiki, page,
    use_variant, use_variant_with,
)


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
    def test_broken_link_and_orphan_hint(self):
        root = make_wiki(self.tmp, files={
            "concepts/alpha-note.md": page(
                "concept", "A note.", body="See [missing](/concepts/missing-page.md).\n"),
            "queries/orphan-question.md": page("query", "Nobody links here."),
            "synthesis/mentioner.md": page(
                "synthesis", "Mentions the orphan.",
                body="The orphan question came up in prose.\n"
                     "Also [alpha](/concepts/alpha-note.md).\n",
            ),
        })
        report = gather(root)
        self.assertEqual(len(findings(report, "link", "ERROR")), 1)
        orphan_infos = [m for _, _, p, m in findings(report, "orphan", "INFO")
                        if p == "queries/orphan-question.md"]
        self.assertTrue(any("mentioned unlinked in synthesis/mentioner.md" in m
                            for m in orphan_infos))

    def test_wikilink_syntax_is_inert(self):
        # Wikilinks were removed for OKF conformance: [[x]] neither resolves
        # nor errors, so a page linked only that way is an orphan.
        root = make_wiki(self.tmp, files={
            "concepts/alpha-note.md": page("concept", "A note.", body="See [[beta-note]].\n"),
            "concepts/beta-note.md": page("concept", "B note."),
        })
        report = gather(root)
        self.assertEqual(findings(report, "link"), [])
        orphans = [p for _, _, p, _ in findings(report, "orphan", "WARNING")]
        self.assertIn("concepts/beta-note.md", orphans)

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

    def test_legacy_log_header_flagged(self):
        root = make_wiki(self.tmp)
        (root / "log.md").write_text("# Log\n\n## [2026-07-01] lint | run\n- ok\n")
        report = gather(root)
        msgs = [m for _, _, _, m in findings(report, "log", "WARNING")]
        self.assertTrue(any("YYYY-MM-DD" in m for m in msgs))

    def test_okf_log_format_passes(self):
        root = make_wiki(self.tmp)
        (root / "log.md").write_text(
            "# Log\n\n## 2026-07-02\n\n- **Update**: concepts/foo.md\n"
            "- **Creation**: sources/bar.md\n\n## 2026-07-01\n\n- **Lint**: clean\n")
        report = gather(root)
        self.assertEqual(findings(report, "log"), [])

    def test_log_entries_and_ordering_checked(self):
        root = make_wiki(self.tmp)
        (root / "log.md").write_text(
            "# Log\n\n## 2026-07-01\n\n- plain bullet without action word\n"
            "\n## 2026-07-02\n\n- **Update**: fine\n")
        report = gather(root)
        msgs = [m for _, _, _, m in findings(report, "log", "WARNING")]
        self.assertTrue(any("bold action word" in m for m in msgs))
        self.assertTrue(any("out of order" in m for m in msgs))

    def test_duplicate_date_heading_flagged(self):
        root = make_wiki(self.tmp)
        (root / "log.md").write_text(
            "# Log\n\n## 2026-07-02\n\n- **Update**: a\n"
            "\n## 2026-07-02\n\n- **Update**: b\n")
        msgs = [m for _, _, _, m in findings(gather(root), "log", "WARNING")]
        self.assertTrue(any("duplicate heading" in m for m in msgs))


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


class TestMarkdownLinks(WikiTest):
    def test_broken_link_flagged_with_file_accurate_line(self):
        root = make_wiki(self.tmp, files={
            "concepts/a-note.md": page("concept", "A.", body="See [gone](missing.md).\n"),
        })
        hits = findings(gather(root), "link", "ERROR")
        self.assertEqual(len(hits), 1)
        # frontmatter is 8 lines + 1 blank: the body's first line is file line 10
        self.assertTrue(hits[0][2].endswith(":10"), hits[0][2])

    def test_bundle_absolute_links_resolve_against_root(self):
        root = make_wiki(self.tmp, files={
            "concepts/a-note.md": page(
                "concept", "A.",
                body="See [b](/concepts/b-note.md) and [gone](/concepts/nope.md).\n"),
            "concepts/b-note.md": page("concept", "B."),
        })
        report = gather(root)
        hits = findings(report, "link", "ERROR")
        self.assertEqual(len(hits), 1)
        self.assertIn("/concepts/nope.md", hits[0][3])
        orphans = [p for _, _, p, _ in findings(report, "orphan", "WARNING")]
        self.assertNotIn("concepts/b-note.md", orphans)  # inbound credit given

    def test_link_escaping_wiki_root_flagged(self):
        # Review regression: /../x.md and ../../x.md used to resolve outside
        # the bundle and pass silently when the target file existed.
        outside = Path(self.tmp).parent / "escaped-target.md"
        outside.write_text("outside the bundle\n")
        self.addCleanup(outside.unlink)
        root = make_wiki(self.tmp, files={
            "concepts/a-note.md": page(
                "concept", "A.",
                body=f"[abs](/../{outside.name}) [rel](../../{outside.name})\n"),
        })
        hits = findings(gather(root), "link", "ERROR")
        self.assertEqual(len(hits), 2)
        self.assertTrue(all("escapes the wiki root" in h[3] for h in hits), hits)

    def test_resolving_targets_pass_and_count_inbound(self):
        root = make_wiki(self.tmp, files={
            "concepts/a-note.md": page(
                "concept", "A.",
                body="See [b](b-note.md), [lab](../lab-dir/), [f](../lab-dir/x.txt),\n"
                     "[ext](https://example.com), [mail](mailto:x@y.z), [top](#anchor),\n"
                     "and [frag](b-note.md#section).\n"),
            "concepts/b-note.md": page("concept", "B."),
            "lab-dir/x.txt": "not markdown\n",
        })
        use_variant_with("generic",
                         non_page_allowed=["lab-dir", "CLAUDE.md", "index.md", "log.md",
                                           "lint.py", "wikilint", "taxonomy.md", "raw", "workflows"])
        report = gather(root)
        self.assertEqual(findings(report, "link"), [])
        orphans = [p for _, _, p, _ in findings(report, "orphan", "WARNING")]
        self.assertNotIn("concepts/b-note.md", orphans)  # md link counted inbound
        self.assertIn("concepts/a-note.md", orphans)

    def test_inline_code_span_not_treated_as_link(self):
        root = make_wiki(self.tmp, files={
            "concepts/a-note.md": page("concept", "A.",
                                       body="Quoted `[x](not-a-real-file.md)` in code.\n"),
        })
        self.assertEqual(findings(gather(root), "link"), [])


class TestEngineExtensionPoints(WikiTest):
    def test_orphans_gate_off(self):
        root = make_wiki(self.tmp, files={
            "queries/orphan-question.md": page("query", "Nobody links here."),
        })
        use_variant_with("generic", orphans=False)
        self.assertEqual(findings(gather(root), "orphan"), [])

    def test_non_page_allowed_globs(self):
        root = make_wiki(self.tmp, files={
            "lab-2026-01-01-x/README.md": "a lab\n",
            "mystery/notes.md": "unexpected\n",
        })
        config = use_variant("generic")
        use_variant_with("generic",
                         non_page_allowed=list(config["non_page_allowed"]) + ["lab-*"])
        flagged = [p for _, _, p, _ in findings(gather(root), "layout", "WARNING")]
        self.assertNotIn("lab-2026-01-01-x", flagged)
        self.assertIn("mystery", flagged)

    def test_custom_index_file_and_body(self):
        def table_body(pages):
            rows = ["| Page |", "|---|"]
            for p in sorted(pages, key=lambda p: p.rel):
                rows.append(f"| [{p.stem}]({p.path.name}) |")
            return "\n".join(rows) + "\n"

        root = make_wiki(self.tmp, files={
            "concepts/a-note.md": page("concept", "A."),
        })
        use_variant_with("generic", index_file="concepts/INDEX.md",
                         index_body_fn=table_body)
        from wikilint.derived import rebuild_index
        rebuild_index(root)
        text = (root / "concepts/INDEX.md").read_text()
        self.assertIn("| [a-note](a-note.md) |", text)
        report = gather(root)
        # INDEX.md inside a page dir is skipped by discovery (no frontmatter
        # error) and the freshly rebuilt index shows no drift.
        self.assertEqual(findings(report, "frontmatter", "ERROR"), [])
        self.assertEqual(findings(report, "index"), [])
        (root / "concepts/INDEX.md").write_text(text + "| stale row |\n")
        drift = findings(gather(root), "index", "WARNING")
        self.assertEqual([p for _, _, p, _ in drift], ["concepts/INDEX.md"])

    def test_extra_secret_patterns_fire(self):
        root = make_wiki(self.tmp, files={
            "concepts/token.md": page("concept", "T.", body="pat nbp_abc12345XYZ here\n"),
        })
        use_variant_with(
            "generic",
            extra_secret_patterns=[(r"\bnbp_[A-Za-z0-9]{8,}", "netbird PAT")],
        )
        hits = findings(gather(root), "secrets", "ERROR")
        self.assertEqual(len(hits), 1)
        self.assertIn("netbird PAT", hits[0][3])
        self.assertTrue(hits[0][2].startswith("concepts/token.md:"))

    def test_secret_allowlist_suppresses_a_real_match(self):
        # Both lines match the built-in password pattern; the allow regex must
        # suppress the ${...} placeholder line and leave the plain secret. If
        # the allowlist did nothing, both would be reported (guards the vacuous
        # case where the fixture matches no pattern at all).
        root = make_wiki(self.tmp, files={
            "concepts/tpl.md": page(
                "concept", "Tpl.",
                body="password: ${REDACTED}\npassword: leakedhunter2\n"),
        })
        use_variant_with("generic")
        self.assertEqual(len(findings(gather(root), "secrets", "ERROR")), 2)
        use_variant_with("generic", secret_allow_res=[r"\$\{[^}]*\}"])
        hits = findings(gather(root), "secrets", "ERROR")
        self.assertEqual(len(hits), 1)
        self.assertTrue(hits[0][2].endswith(":11"), hits[0][2])  # the plain line

    def test_iso_date_fields_configurable(self):
        root = make_wiki(self.tmp, files={
            "concepts/dated.md": page("concept", "D.", extra_fm="date: not-a-date\n"),
        })
        use_variant_with("generic",
                         iso_date_fields=["created", "updated", "date"])
        messages = [m for _, _, _, m in findings(gather(root), "frontmatter", "ERROR")]
        self.assertTrue(any("date is not an ISO date" in m for m in messages))

    def test_none_gates_disable_log_tags_inbox(self):
        root = make_wiki(self.tmp, files={
            "concepts/tagged.md": page("concept", "Tagged.", tags="[gamma]"),
        })
        (root / "log.md").unlink()
        (root / "taxonomy.md").unlink()
        use_variant_with("generic", log_file=None, taxonomy_file=None,
                         inbox_dir=None)
        report = gather(root)  # must not crash on inbox_dir=None
        self.assertEqual(findings(report, "log"), [])
        self.assertEqual(findings(report, "tags"), [])

    def test_extra_checks_run(self):
        def custom(pages, report, root):
            report.info("custom", "x", f"saw {len(pages)} pages")

        root = make_wiki(self.tmp, files={
            "concepts/a-note.md": page("concept", "A."),
        })
        use_variant_with("generic", extra_checks=[custom])
        hits = findings(gather(root), "custom", "INFO")
        self.assertEqual(len(hits), 1)
        self.assertIn("saw 1 pages", hits[0][3])


class TestExtensionHardening(WikiTest):
    """Regression tests for the extension-point defects found in review."""

    def _rebuild(self, root):
        from wikilint.derived import rebuild_index
        rebuild_index(root)

    def test_check_log_reports_the_configured_path(self):
        root = make_wiki(self.tmp, files={})
        (root / "log.md").unlink()
        (root / "ops-journal.md").write_text("# Log\n\n## bad header\n")
        use_variant_with("generic", log_file="ops-journal.md")
        hits = findings(gather(root), "log", "WARNING")
        self.assertTrue(hits)
        self.assertTrue(all(h[2].startswith("ops-journal.md:") for h in hits), hits)

    def test_created_updated_ordering_independent_of_iso_date_fields(self):
        root = make_wiki(self.tmp, files={
            "concepts/a-note.md": page("concept", "A.",
                                       created="2026-05-01", updated="2026-04-01"),
        })
        use_variant_with("generic", iso_date_fields=["date"])  # excludes the pair
        msgs = [m for _, _, _, m in findings(gather(root), "frontmatter", "ERROR")]
        self.assertIn("updated is older than created", msgs)

    def test_index_file_none_disables_index_without_crashing(self):
        root = make_wiki(self.tmp, files={"concepts/a-note.md": page("concept", "A.")})
        use_variant_with("generic", index_file=None)
        self.assertEqual(findings(gather(root), "index"), [])

    def test_invalid_index_file_raises_config_error(self):
        from wikilint.settings import ConfigError
        make_wiki(self.tmp, files={"concepts/a-note.md": page("concept", "A.")})
        for bad in ("/abs/index.md", "../escape.md", ""):
            with self.assertRaises(ConfigError):
                use_variant_with("generic", index_file=bad)

    def test_rebuild_index_creates_missing_parent_dir(self):
        root = make_wiki(self.tmp, files={"concepts/a-note.md": page("concept", "A.")})
        use_variant_with("generic", index_file="derived/index.md",
                         index_body_fn=lambda pages: "- x\n")
        self._rebuild(root)  # must not raise
        self.assertTrue((root / "derived/index.md").is_file())

    def test_dot_prefixed_index_is_skipped_by_discovery(self):
        root = make_wiki(self.tmp, files={"concepts/a-note.md": page("concept", "A.")})
        use_variant_with("generic", index_file="./concepts/INDEX.md",
                         index_body_fn=lambda pages: "- x\n")
        self._rebuild(root)
        fm = [i for i in findings(gather(root), "frontmatter", "ERROR") if "INDEX" in i[2]]
        self.assertEqual(fm, [])

    def test_relocated_root_index_not_flagged_by_layout(self):
        root = make_wiki(self.tmp, files={"concepts/a-note.md": page("concept", "A.")})
        use_variant_with("generic", index_file="catalog.md",
                         index_body_fn=lambda pages: "- x\n")
        self._rebuild(root)
        layout = [p for _, _, p, _ in findings(gather(root), "layout", "WARNING")]
        self.assertNotIn("catalog.md", layout)

    def test_index_body_fn_leading_newline_no_perpetual_drift(self):
        root = make_wiki(self.tmp, files={"concepts/a-note.md": page("concept", "A.")})
        use_variant_with("generic", index_body_fn=lambda pages: "\n| P |\n| a |\n")
        self._rebuild(root)
        self.assertEqual(findings(gather(root), "index"), [])

    def test_bad_secret_regex_raises_config_error(self):
        from wikilint.settings import ConfigError
        make_wiki(self.tmp, files={"concepts/a-note.md": page("concept", "A.")})
        with self.assertRaises(ConfigError):
            use_variant_with("generic", extra_secret_patterns=[("nbp_[", "bad")])
        with self.assertRaises(ConfigError):
            use_variant_with("generic", secret_allow_res=["(unclosed"])

    def test_extra_check_exception_becomes_a_finding(self):
        def boom(pages, report, root):
            raise KeyError("missing")

        root = make_wiki(self.tmp, files={"concepts/a-note.md": page("concept", "A.")})
        use_variant_with("generic", extra_checks=[boom])
        report = gather(root)  # must not crash
        hits = findings(report, "extra-check", "ERROR")
        self.assertEqual(len(hits), 1)
        self.assertIn("KeyError", hits[0][3])

    def test_non_callable_extra_check_raises_config_error(self):
        from wikilint.settings import ConfigError
        make_wiki(self.tmp, files={"concepts/a-note.md": page("concept", "A.")})
        with self.assertRaises(ConfigError):
            use_variant_with("generic", extra_checks=["not callable"])

    def test_image_wrapped_link_credits_outer_target(self):
        root = make_wiki(self.tmp, files={
            "concepts/a-note.md": page("concept", "A.", body="[![thumb](t.png)](b-note.md)\n"),
            "concepts/b-note.md": page("concept", "B."),
        })
        report = gather(root)
        self.assertEqual(findings(report, "link"), [])  # outer target resolves
        orphans = [p for _, _, p, _ in findings(report, "orphan", "WARNING")]
        self.assertNotIn("concepts/b-note.md", orphans)     # got inbound credit

    def test_markdown_link_encoding_scheme_and_absolute_targets(self):
        root = make_wiki(self.tmp, files={
            "concepts/a-note.md": page(
                "concept", "A.",
                body="[enc](../raw/my%20file.md) [tel](tel:+1555) "
                     "[abs](/nope.md) [ok](b-note.md)\n"),
            "concepts/b-note.md": page("concept", "B."),
            "raw/my file.md": "x\n",
        })
        report = gather(root)
        # percent-encoded target resolves, tel: is out of scope; the
        # bundle-absolute target now resolves against the root and is broken.
        hits = findings(report, "link", "ERROR")
        self.assertEqual(len(hits), 1)
        self.assertIn("/nope.md", hits[0][3])
        self.assertNotIn("concepts/b-note.md",
                         [p for _, _, p, _ in findings(report, "orphan", "WARNING")])

    def test_link_in_multi_backtick_code_span_not_flagged(self):
        root = make_wiki(self.tmp, files={
            "concepts/a-note.md": page(
                "concept", "A.",
                body="Example `[x](no-such.md)` and ``[y](/also/none.md)`` are code.\n"),
        })
        self.assertEqual(findings(gather(root), "link"), [])


class TestTypesGlossary(WikiTest):
    def test_default_fixture_passes(self):
        root = make_wiki(self.tmp, files={
            "concepts/alpha-note.md": page("concept", "A note."),
        })
        report = gather(root)
        self.assertEqual(findings(report, "types"), [])

    def test_missing_section_warns_once(self):
        root = make_wiki(self.tmp)
        (root / "taxonomy.md").write_text(
            "---\ntype: tooling\n---\n\n# Taxonomy\n\n- alpha — test tag\n"
        )
        report = gather(root)
        hits = findings(report, "types", "WARNING")
        self.assertEqual(len(hits), 1)
        self.assertIn("no '## Page types' section", hits[0][3])

    def test_undescribed_and_unknown_and_empty_meaning(self):
        root = make_wiki(self.tmp)
        # generic schema types: source, entity, concept, synthesis, query.
        # Describe all but 'query', add a meaningless entry and an unknown one.
        (root / "taxonomy.md").write_text(
            "---\ntype: tooling\n---\n\n# Taxonomy\n\n- alpha — test tag\n"
            "\n## Page types\n\n"
            "- source — a summary of one raw source\n"
            "- entity — a person, company, product, or tool\n"
            "- concept —\n"
            "- synthesis — a cross-cutting analysis\n"
            "- widget — not a real type\n"
        )
        report = gather(root)
        messages = [f[3] for f in findings(report, "types", "WARNING")]
        self.assertEqual(len(messages), 3)
        self.assertTrue(any("'query' is not described" in m for m in messages))
        self.assertTrue(any("'concept' has no meaning" in m for m in messages))
        self.assertTrue(any("unknown type 'widget'" in m for m in messages))

    def test_type_lines_are_not_tags(self):
        # A described type must not satisfy the tag taxonomy: a page tagged
        # 'source' when only the TYPE 'source' is described should warn.
        root = make_wiki(self.tmp, files={
            "concepts/alpha-note.md": page("concept", "A note.", tags="[source]"),
        })
        report = gather(root)
        tag_warnings = [f[3] for f in findings(report, "tags", "WARNING")]
        self.assertTrue(any("'source'" in m for m in tag_warnings))

    def test_glossary_gate_off(self):
        make_wiki(self.tmp)
        use_variant_with("generic", types_glossary=False)
        root = Path(self.tmp)
        (root / "taxonomy.md").write_text(
            "---\ntype: tooling\n---\n\n# Taxonomy\n\n- alpha — test tag\n"
        )
        report = gather(root)
        self.assertEqual(findings(report, "types"), [])


class TestSkillsPairing(WikiTest):
    WORKFLOW = "---\ntype: workflow\n---\n\n# Document\n\nSteps.\n"
    WRAPPER = (
        "---\nname: wiki-document\ndescription: Document a thing.\n---\n\n"
        "Read `workflows/document.md` and follow it exactly.\n"
    )

    def wiki(self, files=None):
        root = make_wiki(self.tmp, files=files)
        use_variant_with("generic", skills_dir=".claude/skills")
        return root

    def test_unprefixed_wrapper_is_orphan(self):
        # Field finding 2026-07-22: bare skill names collide with global
        # skills, so pairing requires the configured prefix.
        root = self.wiki(files={
            "workflows/document.md": self.WORKFLOW,
            ".claude/skills/document/SKILL.md": self.WRAPPER,
        })
        report = gather(root)
        messages = [f[3] for f in findings(report, "skills", "ERROR")]
        self.assertEqual(len(messages), 2)
        self.assertTrue(any("no skill wrapper" in m for m in messages))
        self.assertTrue(any("orphan wrapper" in m for m in messages))

    def test_disabled_by_default(self):
        # "generic" now ships skills_dir (task 1: generic-variant wrappers), so
        # this exercises a variant that still leaves the knob unset.
        root = make_wiki(self.tmp, variant="codebase",
                          files={"workflows/document.md": self.WORKFLOW})
        report = gather(root)
        self.assertEqual(findings(report, "skills"), [])

    def test_paired_wrapper_passes(self):
        root = self.wiki(files={
            "workflows/document.md": self.WORKFLOW,
            ".claude/skills/wiki-document/SKILL.md": self.WRAPPER,
        })
        report = gather(root)
        self.assertEqual(findings(report, "skills"), [])

    def test_workflow_without_wrapper_errors(self):
        root = self.wiki(files={"workflows/document.md": self.WORKFLOW})
        report = gather(root)
        hits = findings(report, "skills", "ERROR")
        self.assertEqual(len(hits), 1)
        self.assertIn("no skill wrapper", hits[0][3])

    def test_orphan_wrapper_errors(self):
        root = self.wiki(files={
            ".claude/skills/wiki-ghost/SKILL.md": self.WRAPPER,
        })
        report = gather(root)
        hits = findings(report, "skills", "ERROR")
        self.assertEqual(len(hits), 1)
        self.assertIn("orphan wrapper", hits[0][3])

    def test_wrapper_must_reference_its_workflow(self):
        root = self.wiki(files={
            "workflows/document.md": self.WORKFLOW,
            ".claude/skills/wiki-document/SKILL.md":
                "---\nname: wiki-document\ndescription: d\n---\n\nJust do it from memory.\n",
        })
        report = gather(root)
        hits = findings(report, "skills", "ERROR")
        self.assertEqual(len(hits), 1)
        self.assertIn("does not reference", hits[0][3])


class TestOkfConformance(WikiTest):
    def test_stray_markdown_needs_frontmatter_and_type(self):
        root = make_wiki(self.tmp, files={
            "notes.md": "no frontmatter here\n",
            "glossary.md": "---\ncreated: 2026-07-01\n---\n\nTyped? No.\n",
            "concepts/a-note.md": page("concept", "A."),
        })
        report = gather(root)
        hits = {p: m for _, _, p, m in findings(report, "okf", "ERROR")}
        self.assertIn("OKF rule 1", hits["notes.md"])
        self.assertIn("OKF rule 2", hits["glossary.md"])

    def test_pages_are_not_double_reported(self):
        root = make_wiki(self.tmp, files={
            "concepts/no-fm.md": "just prose\n",
        })
        report = gather(root)
        # check_frontmatter owns page files; check_okf must stay silent on them.
        self.assertEqual(
            [p for _, _, p, _ in findings(report, "okf", "ERROR")], [])
        self.assertEqual(len(findings(report, "frontmatter", "ERROR")), 1)

    def test_raw_and_reserved_files_excluded(self):
        root = make_wiki(self.tmp, files={
            "raw/inbox/dropped.md": "raw sources never need frontmatter\n",
        })
        report = gather(root)
        self.assertEqual(
            [p for _, _, p, _ in findings(report, "okf", "ERROR")
             if p.startswith("raw/") or p == "log.md"], [])

    def test_tooling_frontmatter_passes(self):
        root = make_wiki(self.tmp, files={
            "workflows/ingest.md": "---\ntype: workflow\n---\n\n# Ingest\n",
        })
        report = gather(root)
        self.assertEqual(findings(report, "okf", "ERROR"), [])

    def test_index_requires_okf_version(self):
        root = make_wiki(self.tmp, files={
            "concepts/a-note.md": page("concept", "A."),
        })
        (root / "index.md").write_text("# Index\n")
        msgs = [m for _, _, _, m in findings(gather(root), "okf", "ERROR")]
        self.assertTrue(any("okf_version" in m for m in msgs))
        from wikilint.derived import rebuild_index
        rebuild_index(root)
        self.assertEqual(findings(gather(root), "okf", "ERROR"), [])
        text = (root / "index.md").read_text()
        self.assertTrue(text.startswith('---\nokf_version: "0.1"\n---\n'), text[:60])
        self.assertIn("* [A Note](/concepts/a-note.md) - A.", text)

    def test_rebuild_index_does_not_accumulate_frontmatter(self):
        root = make_wiki(self.tmp, files={
            "concepts/a-note.md": page("concept", "A."),
        })
        from wikilint.derived import rebuild_index
        rebuild_index(root)
        rebuild_index(root)
        self.assertEqual((root / "index.md").read_text().count("okf_version"), 1)

    def test_okf_conformance_gate_off(self):
        root = make_wiki(self.tmp, files={
            "notes.md": "no frontmatter here\n",
        })
        use_variant_with("generic", okf_conformance=False)
        self.assertEqual(findings(gather(root), "okf"), [])


if __name__ == "__main__":
    unittest.main()
