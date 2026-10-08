"""The engine's Python floor: the oldest CPython still in security support
(3.11 until 2027-10). Older interpreters must get one clear message at
import, before any module that may use newer stdlib behavior loads."""

import unittest

from helpers import REPO


class TestPythonFloor(unittest.TestCase):
    def test_floor_is_3_11(self):
        from wikilint import MIN_PYTHON
        self.assertEqual(MIN_PYTHON, (3, 11))

    def test_old_interpreter_gets_a_clear_message(self):
        from wikilint import python_version_error
        msg = python_version_error((3, 9, 6))
        self.assertIn("3.11+", msg)
        self.assertIn("3.9.6", msg)

    def test_floor_and_newer_pass(self):
        from wikilint import python_version_error
        self.assertIsNone(python_version_error((3, 11, 0)))
        self.assertIsNone(python_version_error((3, 14, 4)))

    def test_guard_runs_before_engine_imports(self):
        """The check must fire before cli (and everything it imports) loads,
        or an old interpreter could fail on newer stdlib use first."""
        source = (REPO / "wiki" / "wikilint" / "__init__.py").read_text()
        self.assertLess(source.index("raise SystemExit"), source.index("from .cli import"))

    def test_readme_states_the_floor(self):
        self.assertIn("Python 3.11+", (REPO / "README.md").read_text())

    def test_ci_tests_floor_and_latest(self):
        workflow = next((REPO / ".github" / "workflows").glob("*.yml")).read_text()
        self.assertIn('"3.11"', workflow)
        self.assertIn('"3.14"', workflow)


if __name__ == "__main__":
    unittest.main()
