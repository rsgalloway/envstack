"""Regression coverage for self-reference accumulation (issue #140)."""

import pytest
import yaml

from envstack import env as env_module
from envstack.env import load_environ, resolve_environ


@pytest.fixture
def stacks(tmp_path, monkeypatch):
    monkeypatch.setenv("ENVPATH", str(tmp_path))
    monkeypatch.setattr(env_module, "seen_stacks", set())

    def write(name, values, includes=()):
        data = {"include": list(includes)}
        for platform in ("linux", "darwin", "windows"):
            data[platform] = {
                k: v.replace("PLATFORM", platform) if isinstance(v, str) else v
                for k, v in values.items()
            }
        (tmp_path / (name + ".env")).write_text(yaml.safe_dump(data))

    write("default", {"PYTHONPATH": "/base:${PYTHONPATH}"})
    write(
        "toola",
        {"PYTHONPATH": "${PYTHONPATH}:${TOOLA_ROOT}/PLATFORM", "TOOLA_ROOT": "/toola"},
        ["default"],
    )
    write("toolb", {"PYTHONPATH": "${PYTHONPATH}:/toolb/PLATFORM"}, ["default"])
    write("app_two", {"X": 1, "ALIAS": "${PYTHONPATH}"}, ["toola", "toolb"])
    write("app_set", {"PYTHONPATH": "${PYTHONPATH}:/app"}, ["toola"])
    return tmp_path, write


@pytest.mark.parametrize("platform", ["linux", "darwin", "windows"])
@pytest.mark.parametrize("shell", [None, "", "ORIG"])
@pytest.mark.parametrize(
    "names,tools",
    [
        ("toola", ["toola"]),
        ("app_two", ["toola", "toolb"]),
        ("app_set", ["toola", "app"]),
        (["toola", "toolb"], ["toola", "toolb"]),
    ],
)
def test_accumulation(stacks, monkeypatch, platform, shell, names, tools):
    root, _ = stacks
    if shell is None:
        monkeypatch.delenv("PYTHONPATH", raising=False)
    else:
        monkeypatch.setenv("PYTHONPATH", shell)
    raw = load_environ(names, platform=platform, scope=str(root))
    original = dict(raw)
    expected = ["/base"] + ([shell] if shell else [])
    expected += ["/app" if tool == "app" else "/" + tool + "/" + platform for tool in tools]
    resolved = resolve_environ(raw)
    assert resolved["PYTHONPATH"] == ":".join(expected)
    if "ALIAS" in resolved:
        assert resolved["ALIAS"] == resolved["PYTHONPATH"]
    assert dict(raw) == original
    assert resolve_environ(raw) == resolved


def test_literal_reset_and_final_root_override(stacks, monkeypatch):
    root, write = stacks
    monkeypatch.setenv("PYTHONPATH", "ORIG")
    write("reset", {"PYTHONPATH": "/reset"}, ["toola"])
    write("app", {"PYTHONPATH": "${PYTHONPATH}:/app"}, ["reset"])
    assert resolve_environ(load_environ("app", scope=str(root)))["PYTHONPATH"] == "/reset:/app"
    env_module.seen_stacks.clear()
    write("override", {"TOOLA_ROOT": "/custom"}, ["toola"])
    resolved = resolve_environ(load_environ("override", platform="windows", scope=str(root)))
    assert resolved["PYTHONPATH"] == "/base:ORIG:/custom/windows"


@pytest.mark.parametrize("operator", [":=", ":-"])
def test_defaults_use_nearest_include(stacks, monkeypatch, operator):
    root, write = stacks
    monkeypatch.setenv("VALUE", "shell")
    write("first", {"VALUE": "first"})
    write("second", {"VALUE": "second"}, ["first"])
    write("third", {"VALUE": "${VALUE" + operator + "fallback}"}, ["second"])
    assert resolve_environ(load_environ("third", scope=str(root)))["VALUE"] == "second"


def test_root_override_applies_to_accumulated_paths(stacks, monkeypatch):
    root, write = stacks
    monkeypatch.setenv("PYTHONPATH", "ORIG")
    write("app", {"TOOLA_ROOT": "/custom", "PYTHONPATH": "${PYTHONPATH}:/app"}, ["toola"])
    resolved = resolve_environ(load_environ("app", platform="windows", scope=str(root)))
    assert resolved["PYTHONPATH"] == "/base:ORIG:/custom/windows:/app"
