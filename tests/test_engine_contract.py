"""Contract tests for the engine's configuration surface: DEFAULTS must
supply every key the engine reads, so a variant's lint.py can list only the
keys it genuinely overrides and no omission can KeyError mid-run.

These are structural tests — they read the engine source for its CONFIG[...]
accesses rather than restating a key list that would drift.
"""

import re
import tempfile
import unittest
from pathlib import Path

from helpers import REPO, findings, gather

ENGINE_DIR = REPO / "wiki" / "wikilint"

# Keys the engine injects itself in configure()/_validate() — never variant
# input, so DEFAULTS must not carry them.
INJECTED_KEYS = {
    "index_entry_extra", "secret_extra_compiled", "secret_allow_compiled",
}

# settings._validate reads the raw merged dict as cfg[...] before it becomes
# CONFIG, so both access spellings count as an engine read.
CONFIG_READ_RE = re.compile(r"""(?:CONFIG|cfg)\[['"]([a-z_]+)['"]\]""")


def engine_config_keys():
    """Every CONFIG key the engine reads, gathered from its own source."""
    keys = set()
    for path in sorted(ENGINE_DIR.glob("*.py")):
        keys |= set(CONFIG_READ_RE.findall(path.read_text(encoding="utf-8")))
    return keys - INJECTED_KEYS


class TestDefaultsCompleteness(unittest.TestCase):
    def test_defaults_supply_every_key_the_engine_reads(self):
        from wikilint.settings import DEFAULTS
        missing = sorted(engine_config_keys() - set(DEFAULTS))
        self.assertEqual(
            missing, [],
            "engine reads keys with no DEFAULTS entry — a variant omitting "
            f"them KeyErrors mid-run: {missing}",
        )

    def test_defaults_declares_no_key_the_engine_never_reads(self):
        from wikilint.settings import DEFAULTS
        stale = sorted(set(DEFAULTS) - engine_config_keys())
        self.assertEqual(stale, [], f"DEFAULTS carries dead knobs: {stale}")

    def test_the_two_tiers_partition_defaults(self):
        """CORE_DEFAULTS and EXTENSION_DEFAULTS are the whole of DEFAULTS and
        do not overlap, so every knob is documented in exactly one tier."""
        from wikilint.settings import CORE_DEFAULTS, DEFAULTS, EXTENSION_DEFAULTS
        self.assertEqual(set(CORE_DEFAULTS) & set(EXTENSION_DEFAULTS), set())
        self.assertEqual(set(CORE_DEFAULTS) | set(EXTENSION_DEFAULTS), set(DEFAULTS))

    def test_core_defaults_are_all_neutral(self):
        """A core knob's default may not switch a check on: every one is empty,
        None, False, or a shape-only value the check itself guards."""
        from wikilint.settings import CORE_DEFAULTS
        shape_only = {
            "claude_md_max_lines", "contested_max_days",
            "inbox_warn_count", "inbox_warn_age_days", "index_mode",
        }
        for key, value in CORE_DEFAULTS.items():
            if key in shape_only:
                continue
            self.assertIn(value, ([], {}, None, False), f"{key} defaults to {value!r}")

    def test_extension_defaults_keep_original_wiki_behavior(self):
        """The pre-existing extension points are NOT flipped off by this
        change: a variant omitting one must behave as the original wiki did."""
        from wikilint.settings import EXTENSION_DEFAULTS
        self.assertTrue(EXTENSION_DEFAULTS["orphans"])
        self.assertTrue(EXTENSION_DEFAULTS["okf_conformance"])
        self.assertTrue(EXTENSION_DEFAULTS["types_glossary"])
        self.assertEqual(EXTENSION_DEFAULTS["log_file"], "log.md")
        self.assertEqual(EXTENSION_DEFAULTS["index_file"], "index.md")

    def test_minimal_config_configures_cleanly(self):
        """A variant config listing one key must yield a complete CONFIG: the
        whole point of the DEFAULTS merge."""
        from wikilint.settings import CONFIG, configure
        saved = dict(CONFIG)
        self.addCleanup(lambda: (CONFIG.clear(), CONFIG.update(saved)))
        configure({"page_dirs": ["notes"]}, lambda fields: "")
        for key in engine_config_keys():
            self.assertIn(key, CONFIG)

    def test_minimal_config_runs_a_full_check_pass(self):
        """Every neutral default must survive a real check pass — the
        regression this guards is `inbox_warn_count`, read by check_inbox but
        declared by no DEFAULTS entry at all before this change."""
        from wikilint.settings import CONFIG, configure
        saved = dict(CONFIG)
        self.addCleanup(lambda: (CONFIG.clear(), CONFIG.update(saved)))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "notes").mkdir()
            (root / "CLAUDE.md").write_text("---\ntype: tooling\n---\n\n# stub\n")
            # Non-wiki markdown tree: the wiki-shaped extension points off.
            configure({"page_dirs": ["notes"], "okf_conformance": False,
                       "types_glossary": False, "orphans": False,
                       "index_file": None, "log_file": None},
                      lambda fields: "")
            report = gather(root)  # must not raise KeyError
            self.assertEqual(findings(report, severity="ERROR"), [])

    def test_inbox_thresholds_default_when_only_inbox_dir_is_set(self):
        """The latent KeyError: setting inbox_dir without its two thresholds
        used to blow up inside check_inbox."""
        from wikilint.settings import CONFIG, configure
        saved = dict(CONFIG)
        self.addCleanup(lambda: (CONFIG.clear(), CONFIG.update(saved)))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "raw" / "inbox").mkdir(parents=True)
            (root / "CLAUDE.md").write_text("---\ntype: tooling\n---\n\n# stub\n")
            configure({"inbox_dir": "raw/inbox", "okf_conformance": False,
                       "types_glossary": False, "index_file": None,
                       "log_file": None}, lambda fields: "")
            self.assertEqual(CONFIG["inbox_warn_count"], 10)
            self.assertEqual(CONFIG["inbox_warn_age_days"], 14)
            gather(root)  # must not raise KeyError


if __name__ == "__main__":
    unittest.main()
