"""The extra_commands registration seam: a wiki registers custom CLI verbs
with the engine instead of intercepting argv before wikilint.main(), so one
usage string lists every verb and every registration is validated at startup.
"""

import tempfile
import unittest
from pathlib import Path

from helpers import VARIANTS, load_variant_config


class CommandTest(unittest.TestCase):
    def setUp(self):
        from wikilint.settings import CONFIG
        saved = dict(CONFIG)
        self.addCleanup(lambda: (CONFIG.clear(), CONFIG.update(saved)))

    def wiki_root(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "CLAUDE.md").write_text("---\ntype: tooling\n---\n\n# stub\n")
        return root


class TestDispatch(CommandTest):
    def test_registered_command_is_dispatched_with_the_root(self):
        from wikilint import main
        calls = []

        def hello(root):
            calls.append(root)
            return 0

        root = self.wiki_root()
        rc = main(
            {"page_dirs": [], "extra_commands": {"hello": (hello, "say hi")}},
            lambda fields: "", argv=["hello"], root=str(root),
        )
        self.assertEqual(rc, 0)
        self.assertEqual(calls, [root])

    def test_registered_command_returns_its_own_exit_code(self):
        from wikilint import main
        rc = main(
            {"page_dirs": [], "extra_commands": {"hello": (lambda root: 7, "hi")}},
            lambda fields: "", argv=["hello"], root=str(self.wiki_root()),
        )
        self.assertEqual(rc, 7)

    def test_registered_command_needs_no_wiki_root(self):
        """Registered verbs dispatch ahead of the CLAUDE.md root guard, so a
        pure-reporting verb (a schema dump, say) works from any cwd."""
        from wikilint import main
        with tempfile.TemporaryDirectory() as tmp:  # no CLAUDE.md in it
            rc = main(
                {"page_dirs": [], "extra_commands": {"hello": (lambda root: 7, "hi")}},
                lambda fields: "", argv=["hello"], root=tmp,
            )
        self.assertEqual(rc, 7)

    def test_help_exits_zero_without_a_wiki_root(self):
        from wikilint import main
        with tempfile.TemporaryDirectory() as tmp:
            for verb in ("help", "-h", "--help"):
                self.assertEqual(
                    main({"page_dirs": []}, lambda fields: "", argv=[verb], root=tmp),
                    0, verb)

    def test_root_guard_still_applies_to_engine_verbs(self):
        """Only registered verbs and `help` skip the guard."""
        from wikilint import main
        with tempfile.TemporaryDirectory() as tmp:
            for verb in ("check", "rebuild-index", "nonsense"):
                self.assertEqual(
                    main({"page_dirs": []}, lambda fields: "", argv=[verb], root=tmp),
                    2, verb)

    def test_unknown_verb_still_exits_two(self):
        from wikilint import main
        rc = main({"page_dirs": []}, lambda fields: "",
                  argv=["nonsense"], root=str(self.wiki_root()))
        self.assertEqual(rc, 2)


class TestUsage(CommandTest):
    def test_usage_lists_engine_and_registered_verbs(self):
        from wikilint.cli import usage
        from wikilint.settings import configure
        configure(
            {"page_dirs": [], "extra_commands": {"hello": (lambda root: 0, "say hi")}},
            lambda fields: "",
        )
        text = usage()
        for verb in ("check", "rebuild-index", "reverse-deps", "coverage", "help", "hello"):
            self.assertIn(verb, text)
        self.assertIn("say hi", text)

    def test_usage_covers_every_builtin(self):
        """usage() renders BUILTIN_COMMANDS, so the verb list has exactly one
        declaration and cannot drift from what main() dispatches."""
        from wikilint.cli import usage
        from wikilint.settings import BUILTIN_COMMANDS, configure
        configure({"page_dirs": []}, lambda fields: "")
        text = usage()
        for verb, help_text in BUILTIN_COMMANDS:
            self.assertIn(verb, text)
            self.assertIn(help_text, text)


class TestRegistrationValidation(CommandTest):
    def configure_with(self, commands):
        from wikilint.settings import configure
        configure({"page_dirs": [], "extra_commands": commands}, lambda fields: "")

    def test_verb_shadowing_a_builtin_is_rejected(self):
        from wikilint.settings import BUILTIN_COMMANDS, ConfigError
        for verb, _help in BUILTIN_COMMANDS:
            with self.assertRaises(ConfigError, msg=verb):
                self.configure_with({verb: (lambda root: 0, "shadow")})

    def test_non_callable_handler_is_rejected(self):
        from wikilint.settings import ConfigError
        with self.assertRaises(ConfigError):
            self.configure_with({"hello": ("nope", "desc")})

    def test_malformed_entry_is_rejected(self):
        from wikilint.settings import ConfigError
        with self.assertRaises(ConfigError):
            self.configure_with({"hello": lambda root: 0})

    def test_empty_help_is_rejected(self):
        from wikilint.settings import ConfigError
        for help_text in ("", "   ", None):
            with self.assertRaises(ConfigError, msg=repr(help_text)):
                self.configure_with({"hello": (lambda root: 0, help_text)})

    def test_empty_verb_is_rejected(self):
        from wikilint.settings import ConfigError
        for verb in ("", "  "):
            with self.assertRaises(ConfigError, msg=repr(verb)):
                self.configure_with({verb: (lambda root: 0, "desc")})

    def test_non_dict_table_is_rejected(self):
        from wikilint.settings import ConfigError
        with self.assertRaises(ConfigError):
            self.configure_with([("hello", (lambda root: 0, "desc"))])

    def test_a_bad_registration_fails_before_any_dispatch(self):
        from wikilint import main
        rc = main({"page_dirs": [], "extra_commands": {"check": (lambda r: 0, "x")}},
                  lambda fields: "", argv=["check"], root=str(self.wiki_root()))
        self.assertEqual(rc, 2)


class TestTemplateUnaffected(unittest.TestCase):
    def test_the_shipped_template_registers_no_command(self):
        """The seam is additive: the template registers nothing, so its usage
        output and dispatch are unchanged."""
        from wikilint.settings import CONFIG, configure
        for variant in VARIANTS:
            config, extra = load_variant_config(variant)
            self.assertNotIn("extra_commands", config, variant)
            configure(config, extra)
            self.assertEqual(CONFIG["extra_commands"], {}, variant)


if __name__ == "__main__":
    unittest.main()
