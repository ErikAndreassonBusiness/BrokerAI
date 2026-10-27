"""Runs the website's JavaScript tests (tests/js) with Node's built-in test runner."""

import shutil
import subprocess
from pathlib import Path

import pytest

JS_TESTS = Path(__file__).parent / "js"


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is not installed")
def test_js():
    result = subprocess.run(
        ["node", "--test", str(JS_TESTS)], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr
