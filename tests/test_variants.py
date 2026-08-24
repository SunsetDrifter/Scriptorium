"""Template invariants: compilable heads, sane configs, line budgets, and
hook correctness properties, for the shipped template and the feature-named
extension configs in extension_configs.py."""

import py_compile
import unittest

from helpers import REPO, VARIANTS, load_variant_config

# Shipped template plus extension-knob config bundles.
ALL_CONFIGS = VARIANTS + ["infra", "pinned-repo", "sharded-repo"]


class TestEngineIdentity(unittest.TestCase):
    def test_everything_compiles(self):
        for variant in VARIANTS:
            py_compile.compile(str(REPO / variant / "lint.py"), doraise=True)
            for p in (REPO / variant / "wikilint").glob("*.py"):
                py_compile.compile(str(p), doraise=True)


class TestConfigSanity(unittest.TestCase):
    def test_configs_load(self):
        for variant in ALL_CONFIGS:
            config, extra = load_variant_config(variant)
            self.assertTrue(callable(extra), variant)
            self.assertTrue(config, variant)

    def test_reverse_fields_are_known_fields(self):
        for variant in ALL_CONFIGS:
            config, _ = load_variant_config(variant)
            known = set(config["path_fields"]) | set(config["edge_fields"])
            for field in config["reverse_fields"]:
                self.assertIn(field, known, f"{variant}: reverse field {field} unresolvable")

    def test_membership_references_real_types(self):
        for variant in ALL_CONFIGS:
            config, _ = load_variant_config(variant)
            rule = config["membership"]
            if not rule:
                continue
            self.assertIn(rule["member_type"], config["type_required"], variant)
            self.assertIn(rule["container_type"], config["type_required"], variant)
            self.assertIn(rule["container_field"],
                          config["path_fields"] + config["edge_fields"], variant)

    def test_every_config_key_is_covered_by_defaults(self):
        """A config may only set keys the engine knows about, so a typo'd key
        name cannot sit in a lint.py silently doing nothing."""
        from wikilint.settings import DEFAULTS
        for variant in ALL_CONFIGS:
            config, _ = load_variant_config(variant)
            unknown = sorted(set(config) - set(DEFAULTS))
            self.assertEqual(unknown, [],
                             f"{variant} sets keys the engine never reads: {unknown}")

    def test_extension_defaults_present(self):
        """The template's effective config carries every extension key."""
        from wikilint.settings import DEFAULTS, configure, CONFIG
        for variant in VARIANTS:
            config, extra = load_variant_config(variant)
            configure(config, extra)
            for key in DEFAULTS:
                self.assertIn(key, CONFIG, f"{variant} missing extension key {key}")


class TestBudgets(unittest.TestCase):
    def test_claude_md_within_declared_cap(self):
        for variant in VARIANTS:
            config, _ = load_variant_config(variant)
            lines = len((REPO / variant / "CLAUDE.md").read_text().splitlines())
            self.assertLessEqual(
                lines, config["claude_md_max_lines"],
                f"{variant}/CLAUDE.md is {lines} lines, cap {config['claude_md_max_lines']}",
            )

    def test_python_files_under_800_lines(self):
        for variant in VARIANTS:
            for p in [REPO / variant / "lint.py", *(REPO / variant / "wikilint").glob("*.py")]:
                lines = len(p.read_text().splitlines())
                self.assertLess(lines, 800, f"{p} is {lines} lines")


class TestHookAndWorkflows(unittest.TestCase):
    def test_hook_lints_staged_snapshot(self):
        for variant in VARIANTS:
            hook = REPO / variant / ".githooks" / "pre-commit"
            self.assertIn(b"checkout-index", hook.read_bytes(), variant)
            self.assertTrue(hook.stat().st_mode & 0o111, f"{variant} hook not executable")

    def test_dispatch_table_matches_workflow_files(self):
        for variant in VARIANTS:
            claude = (REPO / variant / "CLAUDE.md").read_text()
            on_disk = {p.name for p in (REPO / variant / "workflows").glob("*.md")}
            referenced = {
                name.split("/")[-1] for name in
                __import__("re").findall(r"workflows/([a-z-]+\.md)", claude)
            }
            self.assertEqual(referenced, on_disk, variant)


if __name__ == "__main__":
    unittest.main()
