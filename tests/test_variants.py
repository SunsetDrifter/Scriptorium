"""Cross-variant invariants: byte-identical engine, compilable heads, sane
configs, line budgets, and hook correctness properties."""

import py_compile
import unittest

from helpers import REPO, VARIANTS, load_variant_config


class TestEngineIdentity(unittest.TestCase):
    def test_wikilint_byte_identical_across_variants(self):
        reference = {
            p.name: p.read_bytes() for p in (REPO / "generic" / "wikilint").glob("*.py")
        }
        self.assertTrue(reference)
        for variant in VARIANTS[1:]:
            files = {
                p.name: p.read_bytes() for p in (REPO / variant / "wikilint").glob("*.py")
            }
            self.assertEqual(files.keys(), reference.keys(), variant)
            for name, blob in reference.items():
                self.assertEqual(files[name], blob, f"{variant}/wikilint/{name} differs")

    def test_everything_compiles(self):
        for variant in VARIANTS:
            py_compile.compile(str(REPO / variant / "lint.py"), doraise=True)
            for p in (REPO / variant / "wikilint").glob("*.py"):
                py_compile.compile(str(p), doraise=True)


class TestConfigSanity(unittest.TestCase):
    def test_configs_load_and_share_keys(self):
        key_sets = []
        for variant in VARIANTS:
            config, extra = load_variant_config(variant)
            self.assertTrue(callable(extra), variant)
            key_sets.append((variant, set(config)))
        _, reference = key_sets[0]
        for variant, keys in key_sets[1:]:
            self.assertEqual(keys, reference, f"{variant} CONFIG keys diverge from generic")

    def test_reverse_fields_are_known_fields(self):
        for variant in VARIANTS:
            config, _ = load_variant_config(variant)
            known = set(config["path_fields"]) | set(config["edge_fields"])
            for field in config["reverse_fields"]:
                self.assertIn(field, known, f"{variant}: reverse field {field} unresolvable")

    def test_membership_references_real_types(self):
        for variant in VARIANTS:
            config, _ = load_variant_config(variant)
            rule = config["membership"]
            if not rule:
                continue
            self.assertIn(rule["member_type"], config["type_required"], variant)
            self.assertIn(rule["container_type"], config["type_required"], variant)
            self.assertIn(rule["container_field"],
                          config["path_fields"] + config["edge_fields"], variant)

    def test_extension_defaults_present_and_consistent(self):
        """Every variant's effective config carries the extension keys, and no
        variant silently overrides one to a different value (which would
        enable/disable a knob for that variant's users unnoticed)."""
        from wikilint.settings import DEFAULTS, configure, CONFIG
        seen = {}
        for variant in VARIANTS:
            config, extra = load_variant_config(variant)
            configure(config, extra)
            for key in DEFAULTS:
                self.assertIn(key, CONFIG, f"{variant} missing extension key {key}")
                seen.setdefault(key, CONFIG[key])
                self.assertEqual(CONFIG[key], seen[key],
                                 f"{variant} diverges on extension key {key}")


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
    def test_hook_lints_staged_snapshot_and_is_identical(self):
        reference = (REPO / "generic" / ".githooks" / "pre-commit").read_bytes()
        self.assertIn(b"checkout-index", reference)
        for variant in VARIANTS:
            hook = REPO / variant / ".githooks" / "pre-commit"
            self.assertEqual(hook.read_bytes(), reference, variant)
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
