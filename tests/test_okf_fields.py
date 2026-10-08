"""OKF v0.2 page-level frontmatter the template adopts: `title`,
`generated { by, at }` (SPEC §5.2, offset datetimes per §5), and
`status` (§5.4), plus the parser shapes those keys need."""

import tempfile
import unittest
from datetime import date, timedelta

from helpers import (
    DAYS_AGO_41, TODAY, findings, gather, make_wiki, page, use_variant_with,
)
from wikilint.model import parse_frontmatter, parse_okf_datetime


def messages(report, check=None, severity=None):
    return [i[3] for i in findings(report, check, severity)]


class OkfFieldTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)


class TestParserMappings(unittest.TestCase):
    def test_flow_mapping_parses_to_dict(self):
        fields, err = parse_frontmatter(
            "---\ntype: concept\n"
            "generated: { by: claude-code/opus, at: 2026-10-08T14:00:00Z }\n---\n")
        self.assertIsNone(err)
        self.assertEqual(fields["generated"],
                         {"by": "claude-code/opus", "at": "2026-10-08T14:00:00Z"})

    def test_block_mapping_parses_to_dict(self):
        fields, err = parse_frontmatter(
            "---\ntype: concept\ngenerated:\n  by: human:jack\n"
            "  at: 2026-10-08T14:00:00+05:30\ntags: [a]\n---\n")
        self.assertIsNone(err)
        self.assertEqual(fields["generated"],
                         {"by": "human:jack", "at": "2026-10-08T14:00:00+05:30"})
        self.assertEqual(fields["tags"], ["a"])

    def test_empty_key_still_parses_as_list(self):
        fields, _ = parse_frontmatter(
            "---\nsources:\n  - resource: /sources/a.md\nsupersedes:\n---\n")
        self.assertEqual(fields["sources"], [{"resource": "/sources/a.md"}])
        self.assertEqual(fields["supersedes"], [])

    def test_braced_scalar_stays_a_string(self):
        """Review regression: `{todo}`-style placeholders parsed as plain
        strings before mappings existed and must keep doing so."""
        fields, err = parse_frontmatter(
            "---\ntype: concept\ntitle: {draft}\ndescription: {a, b}\n---\n")
        self.assertIsNone(err)
        self.assertEqual(fields["title"], "{draft}")
        self.assertEqual(fields["description"], "{a, b}")


class TestOkfDatetime(unittest.TestCase):
    def test_offset_forms_accepted(self):
        self.assertIsNotNone(parse_okf_datetime("2026-10-08T14:00:00Z"))
        self.assertIsNotNone(parse_okf_datetime("2026-10-08T14:00:00+05:30"))

    def test_forms_python_39_fromisoformat_rejects(self):
        """Review regression: 3.9's fromisoformat refuses these RFC 3339
        forms that 3.11+ accepts; results must not depend on the Python."""
        for value in ("2026-10-08T14:00:00.5Z", "2026-10-08T14:00:00.123456789Z",
                      "2026-10-08T14:00:00+0000", "2026-10-08T14:00:00.25-0530"):
            self.assertIsNotNone(parse_okf_datetime(value), value)

    def test_date_only_and_naive_rejected(self):
        self.assertIsNone(parse_okf_datetime("2026-10-08"))
        self.assertIsNone(parse_okf_datetime("2026-10-08T14:00:00"))
        self.assertIsNone(parse_okf_datetime("soon"))
        self.assertIsNone(parse_okf_datetime(None))


class TestTemplateRequiresOkfKeys(OkfFieldTest):
    def test_helper_page_passes(self):
        root = make_wiki(self.tmp.name, files={
            "concepts/a.md": page("concept", "A page.")})
        self.assertEqual(findings(gather(root), "frontmatter"), [])
        self.assertEqual(findings(gather(root), "okf"), [])

    def test_title_and_generated_at_required(self):
        bare = ("---\ntype: concept\ncreated: 2026-07-01\n"
                "description: d\ntags: [alpha]\nsources: []\n---\n\nBody.\n")
        root = make_wiki(self.tmp.name, files={"concepts/a.md": bare})
        msgs = messages(gather(root), "frontmatter")
        self.assertIn("missing or empty required field: title", msgs)
        self.assertIn("missing or empty required field: generated.at", msgs)


class TestGeneratedShape(OkfFieldTest):
    def lint_generated(self, line):
        root = make_wiki(self.tmp.name, files={
            "concepts/a.md": page("concept", "A page.").replace(
                page("concept", "A page.").split("\n")[4], line)})
        return messages(gather(root), "okf")

    def test_date_only_at_rejected(self):
        msgs = self.lint_generated("generated: { by: claude-code/opus, at: 2026-07-01 }")
        self.assertTrue(any("explicit offset" in m for m in msgs), msgs)

    def test_missing_by_rejected(self):
        msgs = self.lint_generated("generated: { at: 2026-07-01T00:00:00Z }")
        self.assertTrue(any("generated.by" in m for m in msgs), msgs)

    def test_scalar_generated_rejected(self):
        msgs = self.lint_generated("generated: 2026-07-01T00:00:00Z")
        self.assertTrue(any("mapping" in m for m in msgs), msgs)

    def test_generated_before_created_rejected(self):
        root = make_wiki(self.tmp.name, files={"concepts/a.md": page(
            "concept", "A page.", created="2026-07-02", updated="2026-07-01")})
        self.assertIn("generated.at is older than created",
                      messages(gather(root), "frontmatter"))


class TestStatus(OkfFieldTest):
    def test_non_okf_status_value_rejected(self):
        root = make_wiki(self.tmp.name, files={
            "concepts/a.md": page("concept", "A page.", extra_fm="status: active\n")})
        msgs = messages(gather(root), "okf")
        self.assertTrue(any("status" in m and "§5.4" in m for m in msgs), msgs)

    def test_okf_status_values_pass(self):
        files = {f"concepts/{s}.md": page("concept", "A page.", extra_fm=f"status: {s}\n")
                 for s in ("draft", "stable", "deprecated")}
        root = make_wiki(self.tmp.name, files=files)
        self.assertEqual(findings(gather(root), "okf"), [])

    def test_status_check_follows_okf_gate(self):
        root = make_wiki(self.tmp.name, files={
            "concepts/a.md": page("concept", "A page.", extra_fm="status: active\n")})
        use_variant_with("wiki", okf_conformance=False)
        self.assertEqual(findings(gather(root), "okf"), [])

    def test_superseded_page_must_be_deprecated(self):
        files = {
            "concepts/old.md": page("concept", "Old."),
            "concepts/new.md": page("concept", "New.",
                                    extra_fm="supersedes: [/concepts/old.md]\n"),
        }
        root = make_wiki(self.tmp.name, files=files)
        msgs = messages(gather(root), "supersedes", "ERROR")
        self.assertEqual(len(msgs), 1, msgs)
        self.assertIn("status: deprecated", msgs[0])

    def test_deprecated_superseded_page_passes(self):
        files = {
            "concepts/old.md": page("concept", "Old.", extra_fm="status: deprecated\n"),
            "concepts/new.md": page("concept", "New.",
                                    extra_fm="supersedes: [/concepts/old.md]\n"),
        }
        root = make_wiki(self.tmp.name, files=files)
        self.assertEqual(findings(gather(root), "supersedes"), [])


class TestLastModified(OkfFieldTest):
    def test_contested_age_reads_generated_at(self):
        root = make_wiki(self.tmp.name, files={"concepts/a.md": page(
            "concept", "A page.", extra_fm="confidence: contested\n",
            created=DAYS_AGO_41, updated=DAYS_AGO_41)})
        self.assertEqual(len(findings(gather(root), "contested")), 1)

    def test_contested_age_falls_back_to_legacy_updated(self):
        """Non-OKF trees configured with a legacy `updated` key keep their
        contested-age check (OKF §13.1 likewise falls back to `timestamp`)."""
        legacy = (f"---\ntype: concept\ncreated: {DAYS_AGO_41}\nupdated: {DAYS_AGO_41}\n"
                  "description: d\ntags: [alpha]\nsources: []\n"
                  "confidence: contested\n---\n\nBody.\n")
        root = make_wiki(self.tmp.name, files={"concepts/a.md": legacy})
        use_variant_with("wiki", required_fields=["type", "created", "updated"])
        self.assertEqual(len(findings(gather(root), "contested")), 1)

    def test_recent_generated_at_not_flagged(self):
        root = make_wiki(self.tmp.name, files={"concepts/a.md": page(
            "concept", "A page.", extra_fm="confidence: contested\n")})
        self.assertEqual(findings(gather(root), "contested"), [])


class TestIndexUsesOkfKeys(OkfFieldTest):
    def test_index_entry_shows_title_and_generated_date(self):
        from wikilint.derived import rebuild_index
        root = make_wiki(self.tmp.name, files={"concepts/zt.md": page(
            "concept", "A page.", updated="2026-09-30")})
        rebuild_index(root)
        index = (root / "index.md").read_text()
        self.assertIn("[Test Page](/concepts/zt.md)", index)
        self.assertIn("(updated 2026-09-30)", index)

    def test_untitled_page_falls_back_to_prettified_stem(self):
        from wikilint.derived import rebuild_index
        untitled = page("concept", "A page.").replace("title: Test Page\n", "")
        root = make_wiki(self.tmp.name, files={"concepts/a-note.md": untitled})
        use_variant_with("wiki", required_fields=["type", "created"])
        rebuild_index(root)
        self.assertIn("[A Note](/concepts/a-note.md)", (root / "index.md").read_text())


if __name__ == "__main__":
    unittest.main()
