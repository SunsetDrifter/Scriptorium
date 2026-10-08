"""Lint runs must leave no bytecode behind. The template ships no
.gitignore, so a wikilint/__pycache__/ written by a lint run would be
swept into the wiki's history by the agent's next `git add -A`; and the
test suite must not litter the template it tests."""

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import REPO


def pycache_dirs(root):
    return sorted(p.relative_to(root).as_posix() for p in Path(root).rglob("__pycache__"))


class TestNoBytecode(unittest.TestCase):
    def test_lint_run_writes_no_pycache_in_an_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            install = Path(tmp) / "w"
            shutil.copytree(REPO / "wiki", install,
                            ignore=shutil.ignore_patterns("__pycache__"))
            (install / "raw" / "inbox").mkdir(parents=True)
            result = subprocess.run(
                [sys.executable, "lint.py", "check"], cwd=install,
                capture_output=True, text=True,
                env={"PATH": "/usr/bin:/bin"},  # no inherited PYTHONDONTWRITEBYTECODE
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(pycache_dirs(install), [])

    def test_suite_does_not_write_bytecode(self):
        self.assertTrue(sys.dont_write_bytecode)

    def test_compile_check_writes_nothing(self):
        source = (REPO / "tests" / "test_variants.py").read_text()
        self.assertNotIn("py_compile", source)


if __name__ == "__main__":
    unittest.main()
