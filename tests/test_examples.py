"""Check example deployment destinations against their runtime stacks."""

import json
from functools import partial
from pathlib import Path

import pytest

from envstack import env as env_module
from envstack import util
from envstack.env import load_environ, resolve_environ


@pytest.mark.parametrize("platform", ["linux", "darwin", "windows"])
def test_pyside_example(monkeypatch, platform):
    root = Path(__file__).resolve().parents[1] / "examples" / "pyside"
    monkeypatch.setattr(env_module, "seen_stacks", set())
    monkeypatch.setattr(util, "dedupe_paths", partial(util.dedupe_paths, platform=platform))
    monkeypatch.setenv("ENVPATH", str(root))
    monkeypatch.setenv("ROOT", "/shared")
    monkeypatch.setenv("PYTHONPATH", "/existing/python")
    monkeypatch.delenv("PYSIDE6_ROOT", raising=False)
    monkeypatch.delenv("PYSIDE6_VERSION", raising=False)
    resolved = resolve_environ(load_environ("pyside6", platform=platform, scope=str(root)))
    manifest = json.loads((root / "dist.json").read_text())
    destination = manifest["targets"]["pyside6"]["destination"]
    destination = destination.format(DEPLOY_ROOT=resolved["DEPLOY_ROOT"]).replace("%1", platform)
    sep = ";" if platform == "windows" else ":"
    assert resolved["PYTHONPATH"] == sep.join(
        ["/shared/prod/lib/python", "/existing/python", destination + "/lib/python"]
    )
    assert resolved["PYSIDE6_ROOT"] + "/" + platform == destination
    assert (root / "default.env").read_text() == (root.parent / "tools/default.env").read_text()
