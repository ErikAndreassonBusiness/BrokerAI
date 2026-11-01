"""Runs the website's JavaScript tests (tests/js) with Node's built-in test runner."""

import shutil
import subprocess
from pathlib import Path

import pytest

JS_TESTS = Path(__file__).parent / "js"


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is not installed")
def test_js():
    # Pass the files, not the folder: Node 22 (on the CI runner) can't run a folder.
    files = sorted(str(path) for path in JS_TESTS.glob("*.test.js"))
    assert files, f"no JS tests in {JS_TESTS}"
    result = subprocess.run(
        ["node", "--test", *files], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr
