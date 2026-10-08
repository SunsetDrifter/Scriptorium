"""index_head: the text a fresh index gets above the generated marker. A
tree that does not commit its index (because entry titles are private)
creates it from scratch in every clone, so without this knob the first
rebuild silently replaces the tree's own heading with the generic one."""

import tempfile
import unittest

from helpers import findings, gather, make_wiki, page, use_variant_with
from wikilint.derived import rebuild_index
from wikilint.model import GENERATED_MARKER
from wikilint.settings import ConfigError

HEAD = "# Findings index\n\nGenerated; never hand-edit below the marker.\n\n"


class IndexHeadTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = make_wiki(self.tmp.name, files={"concepts/a.md": page("concept", "A.")})

    def index_text(self):
        return (self.root / "index.md").read_text()


class TestIndexHead(IndexHeadTest):
    def test_fresh_index_gets_configured_head(self):
        use_variant_with("wiki", index_head=HEAD)
        rebuild_index(self.root)
        self.assertIn(HEAD + GENERATED_MARKER, self.index_text())
        self.assertNotIn("# Index\n", self.index_text())

    def test_default_keeps_generic_heading(self):
        rebuild_index(self.root)
        self.assertIn("# Index\n\n" + GENERATED_MARKER, self.index_text())

    def test_rebuild_is_stable_and_drift_free(self):
        use_variant_with("wiki", index_head=HEAD)
        rebuild_index(self.root)
        first = self.index_text()
        rebuild_index(self.root)
        self.assertEqual(self.index_text(), first)
        self.assertEqual(findings(gather(self.root), "index"), [])

    def test_existing_hand_edited_head_wins(self):
        """index_head seeds a missing index; it never overwrites a head an
        existing index already carries above its marker."""
        use_variant_with("wiki", index_head=HEAD)
        (self.root / "index.md").write_text(f"# Mine\n\n{GENERATED_MARKER}\n\nstale\n")
        rebuild_index(self.root)
        self.assertTrue(self.index_text().split("---\n\n")[-1].startswith("# Mine\n\n"))

    def test_pinning_fence_under_configured_head_is_preserved(self):
        """A marker-less index whose only content above a yaml pinning fence
        is the configured head keeps the fence, as with the generic head."""
        use_variant_with("wiki", index_head=HEAD)
        fence = "```yaml\nrepo: acme/app\nlast_synced_commit: abc123\n```"
        (self.root / "index.md").write_text(HEAD + fence + "\n")
        rebuild_index(self.root)
        self.assertIn(HEAD + fence + "\n\n" + GENERATED_MARKER, self.index_text())

    def test_non_string_rejected_at_configure(self):
        with self.assertRaisesRegex(ConfigError, "index_head"):
            use_variant_with("wiki", index_head=["# Index"])


if __name__ == "__main__":
    unittest.main()
