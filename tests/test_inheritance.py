"""Regression coverage for self-reference accumulation (issue #140)."""

import os

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
        (tmp_path / (name + ".env")).write_text(yaml.safe_dump(data, sort_keys=False))

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


@pytest.fixture
def path_separator():
    return os.pathsep


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
    path_separator = ";" if platform == "windows" else ":"
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
    assert resolved["PYTHONPATH"] == path_separator.join(expected)
    if "ALIAS" in resolved:
        assert resolved["ALIAS"] == resolved["PYTHONPATH"]
    assert dict(raw) == original
    assert resolve_environ(raw) == resolved


def test_literal_reset_and_final_root_override(stacks, monkeypatch, path_separator):
    root, write = stacks
    monkeypatch.setenv("PYTHONPATH", "ORIG")
    write("reset", {"PYTHONPATH": "/reset"}, ["toola"])
    write("app", {"PYTHONPATH": "${PYTHONPATH}:/app"}, ["reset"])
    assert resolve_environ(load_environ("app", scope=str(root)))[
        "PYTHONPATH"
    ] == path_separator.join(["/reset", "/app"])
    env_module.seen_stacks.clear()
    write("override", {"TOOLA_ROOT": "/custom"}, ["toola"])
    resolved = resolve_environ(load_environ("override", platform="windows", scope=str(root)))
    assert resolved["PYTHONPATH"] == ";".join(["/base", "ORIG", "/custom/windows"])


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
    assert resolved["PYTHONPATH"] == ";".join(["/base", "ORIG", "/custom/windows", "/app"])


@pytest.mark.parametrize("reverse_keys", [False, True])
@pytest.mark.parametrize("root_value", ["${ROOT}", "${ROOT:-/fallback}"])
def test_inherited_path_uses_self_referencing_root(
    stacks, monkeypatch, root_value, path_separator, reverse_keys
):
    root, write = stacks
    monkeypatch.delenv("ROOT", raising=False)
    monkeypatch.delenv("PYTHONPATH", raising=False)
    values = {"ROOT": "/base", "PYTHONPATH": "${ROOT}/lib:${PYTHONPATH}"}
    if reverse_keys:
        values = dict(reversed(list(values.items())))
    write("base", values)
    write(
        "app",
        {"ROOT": root_value, "PYTHONPATH": "${PYTHONPATH}:/app"},
        ["base"],
    )

    resolved = resolve_environ(load_environ("app", scope=str(root)))

    assert resolved["ROOT"] == "/base"
    assert resolved["PYTHONPATH"] == path_separator.join(["/base/lib", "/app"])


@pytest.mark.parametrize("reverse_keys", [False, True])
def test_self_reference_through_inherited_alias(stacks, monkeypatch, path_separator, reverse_keys):
    root, write = stacks
    monkeypatch.delenv("FOO", raising=False)
    monkeypatch.delenv("BAR", raising=False)
    values = {"FOO": "/base", "BAR": "${FOO}"}
    if reverse_keys:
        values = dict(reversed(list(values.items())))
    write("base", values)
    write("app", {"FOO": "${BAR}:/app"}, ["base"])

    resolved = resolve_environ(load_environ("app", scope=str(root)))

    expected = path_separator.join(["/base", "/app"])
    assert resolved["FOO"] == expected
    assert resolved["BAR"] == expected


@pytest.mark.parametrize("variable", ["PATH", "PYTHONPATH", "PLUGIN_PATH"])
@pytest.mark.parametrize("shell", [None, "", "original"])
@pytest.mark.parametrize("platform", ["linux", "windows"])
def test_search_path_variables(stacks, monkeypatch, variable, shell, platform):

    root, write = stacks
    sep = ";" if platform == "windows" else ":"
    base = "C:/shared" if platform == "windows" else "/shared"
    original = "C:/Windows/System32" if platform == "windows" else "/usr/bin"
    if shell is None:
        monkeypatch.delenv(variable, raising=False)
    else:
        monkeypatch.setenv(variable, original if shell else "")
    write("base", {variable: base + "/bin" + sep + "${" + variable + "}"})
    write("first", {variable: "${" + variable + "}" + sep + base + "/first/bin"}, ["base"])
    write("second", {variable: "${" + variable + "}" + sep + base + "/second/bin"}, ["base"])
    write("combined", {"ALIAS": "${" + variable + "}"}, ["first", "second"])
    raw = load_environ("combined", platform=platform, scope=str(root))
    resolved = resolve_environ(raw)
    expected = [base + "/bin"] + ([original] if shell else [])
    expected += [base + "/first/bin", base + "/second/bin"]
    assert resolved[variable] == sep.join(expected)
    assert resolved["ALIAS"] == resolved[variable]


@pytest.mark.parametrize("platform", ["linux", "darwin", "windows"])
@pytest.mark.parametrize("python_version", ["3.10", "3.11", "3.12"])
def test_tools_example(monkeypatch, platform, python_version):
    import json
    from pathlib import Path

    from envstack import config, wrapper

    root = Path(__file__).resolve().parents[1] / "examples" / "tools"
    monkeypatch.setattr(env_module, "seen_stacks", set())
    for key in ("PILLOW_ROOT", "OPENEXR_ROOT", "OPENEXR_VERSION", "NUMPY_ROOT", "NUMPY_VERSION"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("ENVPATH", str(root))
    monkeypatch.setenv("ROOT", "/shared")
    monkeypatch.setenv("PILLOW_VERSION", "custom-build")
    monkeypatch.setattr(config, "ALLOW_COMMANDS", True)
    commands = []

    def capture_output(command):
        commands.append(command)
        return 0, python_version, ""

    monkeypatch.setattr(wrapper, "capture_output", capture_output)
    monkeypatch.setenv("PATH", "/system/bin")
    monkeypatch.setenv("PYTHONPATH", "/existing/python")
    raw = load_environ("tools", platform=platform, scope=str(root))
    assert [source.namespace() for source in raw.sources] == [
        "default",
        "numpy",
        "pillow",
        "openexr",
        "tools",
    ]
    resolved = resolve_environ(raw)
    assert commands and all("sys.version_info" in command for command in commands)
    numpy = f"/shared/prod/tools/numpy/2.2.6/{platform}/python{python_version}"
    pillow = f"/shared/prod/tools/pillow/custom-build/{platform}"
    openexr = f"/shared/prod/tools/openexr/3.4.13/{platform}"
    manifest = json.loads((root / "dist.json").read_text())
    for name, path in (
        ("numpy", numpy),
        ("pillow", pillow.replace("custom-build", "12.3.0")),
        ("openexr", openexr),
    ):
        destination = manifest["targets"][name]["destination"]
        destination = destination.format(DEPLOY_ROOT=resolved["DEPLOY_ROOT"])
        destination = destination.replace("%1", platform).replace("%2", "python" + python_version)
        assert destination == path
    sep = ";" if platform == "windows" else ":"
    assert resolved["PYTHONPATH"] == sep.join(
        [
            "/shared/prod/lib/python",
            "/existing/python",
            numpy + "/lib/python",
            pillow + "/lib/python",
            openexr + "/lib/python",
            "/shared/prod/apps/tools/lib/python",
        ]
    )
    expected_path = ["/shared/prod/bin", "/system/bin"]
    if platform == "windows":
        expected_path += [pillow + "/bin", openexr + "/bin"]
    assert resolved["PATH"] == sep.join(expected_path)


@pytest.mark.parametrize("platform", ["linux", "darwin", "windows"])
def test_openexr_example_includes_numpy(monkeypatch, platform):
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "examples" / "tools"
    monkeypatch.setattr(env_module, "seen_stacks", set())
    monkeypatch.setenv("ENVPATH", str(root))
    raw = load_environ("openexr", platform=platform, scope=str(root))
    assert [source.namespace() for source in raw.sources] == ["default", "numpy", "openexr"]


@pytest.mark.integration
def test_numpy_example_detects_runtime(monkeypatch):
    import os
    import shutil
    import subprocess
    import sys
    from pathlib import Path

    from envstack import config, util

    root = Path(__file__).resolve().parents[1] / "examples" / "tools"
    monkeypatch.setenv(
        "PATH", os.path.dirname(sys.executable) + os.pathsep + os.environ.get("PATH", "")
    )
    python = shutil.which("python")
    if python is None:
        pytest.skip("python is not available on PATH")
    expected = subprocess.check_output(
        [python, "-c", "import sys; print('%s.%s' % sys.version_info[:2])"], text=True
    ).strip()
    monkeypatch.setattr(config, "ALLOW_COMMANDS", True)
    monkeypatch.setattr(env_module, "seen_stacks", set())
    monkeypatch.setenv("ENVPATH", str(root))
    monkeypatch.setenv("ROOT", "/shared")
    monkeypatch.setenv("NUMPY_VERSION", "2.2.6")
    monkeypatch.delenv("NUMPY_ROOT", raising=False)
    monkeypatch.delenv("PYTHONPATH", raising=False)
    resolved = resolve_environ(load_environ("numpy", scope=str(root)))
    assert util.split_paths(resolved["PYTHONPATH"]) == [
        "/shared/prod/lib/python",
        f"/shared/prod/tools/numpy/2.2.6/{config.PLATFORM}/python{expected}/lib/python",
    ]


@pytest.mark.parametrize("reverse_keys", [False, True])
def test_late_bound_root_and_alias(stacks, monkeypatch, path_separator, reverse_keys):
    root, write = stacks
    for key in ("ROOT", "ALIAS", "PYTHONPATH"):
        monkeypatch.delenv(key, raising=False)
    values = {
        "ROOT": "/base",
        "ALIAS": "${ROOT}",
        "PYTHONPATH": "${ALIAS}/lib:${PYTHONPATH}",
    }
    if reverse_keys:
        values = dict(reversed(list(values.items())))
    write("base", values)
    write("app", {"ROOT": "/custom", "PYTHONPATH": "${PYTHONPATH}:/app"}, ["base"])
    raw = load_environ("app", scope=str(root))
    original = dict(raw)
    resolved = resolve_environ(raw)
    assert resolved["ROOT"] == resolved["ALIAS"] == "/custom"
    assert resolved["PYTHONPATH"] == path_separator.join(["/custom/lib", "/app"])
    assert dict(raw) == original
    assert resolve_environ(raw) == resolved


@pytest.mark.parametrize("shell_root", [None, "/shell"])
def test_deleted_variable_is_not_restored_from_sources(stacks, monkeypatch, shell_root):
    root, write = stacks
    if shell_root is None:
        monkeypatch.delenv("ROOT", raising=False)
    else:
        monkeypatch.setenv("ROOT", shell_root)
    write("base", {"ROOT": "/base", "LIB": "${ROOT}/lib"})
    raw = load_environ("base", scope=str(root))
    del raw["ROOT"]

    resolved = resolve_environ(raw)

    assert "ROOT" not in raw
    assert "ROOT" not in resolved
    assert resolved["LIB"] == (shell_root or "") + "/lib"


@pytest.mark.parametrize("variable", ["PATH", "PYTHONPATH", "PLUGIN_PATH"])
def test_empty_assignment_resets_inherited_paths(stacks, monkeypatch, variable, path_separator):
    root, write = stacks
    monkeypatch.setenv(variable, "/shell")
    write("base", {variable: "/base:${" + variable + "}"})
    write("reset", {variable: "", "ALIAS": "${" + variable + "}"}, ["base"])
    resolved = resolve_environ(load_environ("reset", scope=str(root)))
    assert resolved[variable] == resolved["ALIAS"] == ""

    env_module.seen_stacks.clear()
    write("app", {variable: "${" + variable + "}:/app"}, ["reset"])
    resolved = resolve_environ(load_environ("app", scope=str(root)))
    assert resolved[variable] == resolved["ALIAS"] == path_separator.join(["/app"])


@pytest.mark.parametrize("reverse_keys", [False, True])
@pytest.mark.parametrize("operator", [":=", ":-"])
@pytest.mark.parametrize("shell_root", [None, "/shell"])
def test_inherited_default_preserves_final_root(
    stacks, monkeypatch, reverse_keys, operator, shell_root
):
    root, write = stacks
    if shell_root is None:
        monkeypatch.delenv("ROOT", raising=False)
    else:
        monkeypatch.setenv("ROOT", shell_root)
    write("base", {"ROOT": "${ROOT" + operator + "/base}"})
    write("middle", {"ROOT": "${ROOT}/middle"}, ["base"])
    values = {"ROOT": "${ROOT}/suffix", "LIB": "${ROOT}/lib", "ALIAS": "${ROOT}"}
    if reverse_keys:
        values = dict(reversed(list(values.items())))
    write("app", values, ["middle"])
    raw = load_environ("app", scope=str(root))
    original = dict(raw)

    resolved = resolve_environ(raw)

    expected = (shell_root or "/base") + "/middle/suffix"
    assert resolved["ROOT"] == resolved["ALIAS"] == expected
    assert resolved["LIB"] == expected + "/lib"
    assert dict(raw) == original
    assert resolve_environ(raw) == resolved


@pytest.mark.parametrize("platform", ["linux", "darwin", "windows"])
def test_selected_platform_controls_path_normalization(stacks, monkeypatch, platform):
    root, write = stacks
    monkeypatch.delenv("PYTHONPATH", raising=False)
    monkeypatch.delenv("MISSING", raising=False)
    sep = ";" if platform == "windows" else ":"
    base = "//server/base" if platform == "windows" else "/base"
    app = "//server/app" if platform == "windows" else "/app"
    write("base", {"PYTHONPATH": base + sep + base})
    write(
        "app",
        {
            "PYTHONPATH": "${PYTHONPATH}" + sep + app,
            "FALLBACK": "${MISSING:-" + base + sep + base + "}",
            "NESTED": [base + sep + base, {"path": "${PYTHONPATH}"}],
        },
        ["base"],
    )

    resolved = resolve_environ(load_environ("app", platform=platform, scope=str(root)))

    assert resolved["PYTHONPATH"] == sep.join([base, app])
    assert resolved["FALLBACK"] == base
    assert resolved["NESTED"] == [base, {"path": sep.join([base, app])}]
    assert resolved.platform == platform
    assert resolve_environ(resolved) == resolved
