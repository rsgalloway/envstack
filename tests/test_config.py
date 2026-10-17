"""Verify import-time settings through fresh CLI and Python API processes."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("namespace", [None, "custom"])
@pytest.mark.parametrize("explicit", [None, "chosen"])
def test_default_namespace_at_startup(tmp_path, namespace, explicit):
    for name in ("default", "custom", "chosen"):
        (tmp_path / (name + ".env")).write_text("all:\n  SELECTED: " + name + "\n")
    process_env = dict(os.environ)
    process_env.pop("DEFAULT_NAMESPACE", None)
    if namespace is not None:
        process_env["DEFAULT_NAMESPACE"] = namespace
    process_env["ENVPATH"] = str(tmp_path)
    process_env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "lib")
    expected = explicit or namespace or "default"
    code = """
import json
import sys
from envstack import config, load_environ
from envstack.cli import parse_args
explicit = sys.argv[1:]
sys.argv = ["envstack"] + explicit + ["-u", "SELECTED"]
args, command = parse_args()
api = load_environ(*explicit)
cli = load_environ(args.namespace)
print(json.dumps([config.DEFAULT_NAMESPACE, api["SELECTED"], cli["SELECTED"]]))
"""
    result = subprocess.run(
        [sys.executable, "-c", code] + ([explicit] if explicit else []),
        env=process_env,
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(result.stdout) == [namespace or "default", expected, expected]
