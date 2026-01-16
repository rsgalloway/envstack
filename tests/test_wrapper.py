#!/usr/bin/env python3
#
# Copyright (c) 2024-2025, Ryan Galloway (ryan@rsgalloway.com)
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#  - Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
#  - Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
#  - Neither the name of the software nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#

"""
Contains unit tests for the wrapper.py module.
"""

import os
import sys
import pytest
from types import SimpleNamespace

import envstack.wrapper as wrapper_mod
from envstack.wrapper import Wrapper, CommandWrapper, run_command


IS_WINDOWS = sys.platform.startswith("win")


@pytest.fixture
def stub_env(monkeypatch):
    """
    Make wrapper tests independent of real envstack stack files.
    """
    def _fake_load_environ(namespace):
        env = dict(os.environ)
        env["ENV"] = namespace or "prod"
        env["ROOT"] = (
            "C:\\tmp\\envstack-root" if IS_WINDOWS else "/tmp/envstack-root"
        )
        return env

    monkeypatch.setattr(wrapper_mod, "load_environ", _fake_load_environ)
    return _fake_load_environ


class HelloWrapper(Wrapper):
    """
    Wrapper that prints an env var passed as argv[0].
    Uses shell=True with platform-safe quoting.
    """
    shell = True

    def executable(self):
        if IS_WINDOWS:
            return (
                'python -c "import os,sys;print(os.getenv(sys.argv[1]))"'
            )
        return (
            "python3 -c 'import os,sys;print(os.getenv(sys.argv[1]))'"
        )


def test_wrapper_shell_true_allows_command_string(stub_env, capfd):
    w = HelloWrapper("hello", ["ROOT"])
    rc = w.launch()
    out, err = capfd.readouterr()
    assert rc == 0
    assert out.strip() == (
        "C:\\tmp\\envstack-root" if IS_WINDOWS else "/tmp/envstack-root"
    )


def test_commandwrapper_runs_argv_without_shell(stub_env, capfd):
    if IS_WINDOWS:
        cmd = ["cmd", "/c", "echo hi there"]
    else:
        cmd = ["echo", "hi there"]

    w = CommandWrapper("hello", cmd)
    rc = w.launch()
    out, err = capfd.readouterr()
    assert rc == 0
    assert out.strip().lower() == "hi there"


def test_run_command_brace_expands_to_env_value(stub_env, capfd):
    rc = run_command(["echo", "{ROOT}"], namespace="hello")
    out, err = capfd.readouterr()
    assert rc == 0
    assert "{ROOT}" not in out
    assert "envstack-root" in out


@pytest.mark.skipif(not IS_WINDOWS, reason="Windows only")
def test_windows_cmd_echo_root():
    rc = run_command(["echo", "{ROOT}"], namespace="hello")
    assert rc == 0


@pytest.mark.skipif(IS_WINDOWS, reason="POSIX-only quoting semantics")
def test_run_command_preserves_quoted_arg_in_argv_mode(stub_env):
    rc = run_command(
        ["bash", "-c", "printf '%s\n' \"sleep 5\""],
        namespace="hello",
    )
    assert rc == 0


@pytest.mark.skipif(IS_WINDOWS, reason="POSIX-only shell behavior")
def test_run_command_two_in_series_no_stop(stub_env, capfd):
    rc1 = run_command(["bash", "-c", "echo one"], namespace="hello")
    rc2 = run_command(["bash", "-c", "echo two"], namespace="hello")
    out, err = capfd.readouterr()
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    assert rc1 == 0 and rc2 == 0
    assert lines[-2:] == ["one", "two"]


@pytest.mark.parametrize(
    "override, expected",
    [
        ("1", True),
        ("true", True),
        ("yes", True),
        ("on", True),
        ("0", False),
        ("false", False),
        ("no", False),
        ("off", False),
    ],
)
def test_interactive_env_override_parsing(
    stub_env, monkeypatch, override, expected
):
    env = dict(os.environ)
    env["INTERACTIVE"] = override

    ShellWrapper = getattr(wrapper_mod, "ShellWrapper", None)
    if ShellWrapper is None:
        pytest.skip("ShellWrapper not present")

    sw = ShellWrapper("hello", "echo test")
    assert sw.get_interactive(env) is expected


def test_capture_output_success(monkeypatch):
    import envstack.wrapper as w

    # Make env plumbing deterministic
    monkeypatch.setattr(w, "load_environ", lambda ns: {"A": "1"})
    monkeypatch.setattr(w, "resolve_environ", lambda env: env)
    monkeypatch.setattr(w, "encode", lambda env: env)
    monkeypatch.setattr(w.config, "SHELL", "/bin/bash")

    calls = {}

    def fake_run(cmd, env=None, shell=None, check=None, capture_output=None, text=None, timeout=None):
        calls["cmd"] = cmd
        calls["env"] = env
        calls["shell"] = shell
        calls["check"] = check
        calls["capture_output"] = capture_output
        calls["text"] = text
        calls["timeout"] = timeout
        return SimpleNamespace(returncode=0, stdout="Python 3.8.17\n", stderr="")

    monkeypatch.setattr(w.subprocess, "run", fake_run)

    rc, out, err = w.capture_output("python --version", namespace="test")

    assert rc == 0
    assert out == "Python 3.8.17\n"
    assert err == ""

    # Ensure argv mode (safer default)
    assert isinstance(calls["cmd"], list)
    assert calls["cmd"][0] == "python"
    assert calls["shell"] is False
    assert calls["check"] is False
    assert calls["capture_output"] is True
    assert calls["text"] is True

    # Ensure env passed through
    assert calls["env"]["A"] == "1"


def test_capture_output_nonzero_exit_preserves_stdout_stderr(monkeypatch):
    import envstack.wrapper as w

    monkeypatch.setattr(w, "load_environ", lambda ns: {})
    monkeypatch.setattr(w, "resolve_environ", lambda env: env)
    monkeypatch.setattr(w, "encode", lambda env: env)
    monkeypatch.setattr(w.config, "SHELL", "/bin/bash")

    def fake_run(*args, **kwargs):
        return SimpleNamespace(returncode=2, stdout="", stderr="boom\n")

    monkeypatch.setattr(w.subprocess, "run", fake_run)

    rc, out, err = w.capture_output("somecmd --flag", namespace="test")
    assert rc == 2
    assert out == ""
    assert err == "boom\n"


def test_capture_output_command_not_found_returns_127_and_stderr(monkeypatch):
    import envstack.wrapper as w

    monkeypatch.setattr(w, "load_environ", lambda ns: {})
    monkeypatch.setattr(w, "resolve_environ", lambda env: env)
    monkeypatch.setattr(w, "encode", lambda env: env)
    monkeypatch.setattr(w.config, "SHELL", "/bin/bash")

    def fake_run(cmd, **kwargs):
        # Emulate what subprocess.run does when executable doesn't exist
        raise FileNotFoundError(2, "No such file or directory", cmd[0])

    monkeypatch.setattr(w.subprocess, "run", fake_run)

    rc, out, err = w.capture_output("python4 --version", namespace="test")

    assert rc == 127
    assert out == ""
    # don’t over-specify text; just ensure it’s useful
    assert "python4" in err.lower()
    assert "not found" in err.lower() or "no such file" in err.lower()


def test_capture_output_preserves_spaces_in_command(monkeypatch):
    """
    Guardrail: ensure command parsing doesn't drop arguments.
    """
    import envstack.wrapper as w

    monkeypatch.setattr(w, "load_environ", lambda ns: {})
    monkeypatch.setattr(w, "resolve_environ", lambda env: env)
    monkeypatch.setattr(w, "encode", lambda env: env)
    monkeypatch.setattr(w.config, "SHELL", "/bin/bash")

    seen = {}

    def fake_run(cmd, **kwargs):
        seen["cmd"] = cmd
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(w.subprocess, "run", fake_run)

    w.capture_output("python -c 'print(123)'", namespace="test")

    assert seen["cmd"][0] == "python"
    assert "-c" in seen["cmd"]


@pytest.mark.integration
def test_capture_output_integration_python_stdout():
    import envstack.wrapper as w

    # Use the current interpreter for maximum reliability
    cmd = f'"{sys.executable}" -c "print(12345)"'

    rc, out, err = w.capture_output(cmd)

    assert rc == 0
    assert out.strip() == "12345"
    assert err.strip() == ""


@pytest.mark.integration
@pytest.mark.skipif(os.name != "nt", reason="Windows CMD-specific behavior")
def test_capture_output_integration_windows_cmd_quoting():
    import envstack.wrapper as w

    # This contains nested quotes and spaces that often break if you re-shell-join badly.
    cmd = f'"{sys.executable}" -c "import sys; print(sys.version_info[0])"'

    rc, out, err = w.capture_output(cmd)

    assert rc == 0
    assert out.strip().isdigit()
    assert err.strip() == ""


@pytest.mark.integration
def test_capture_output_integration_command_not_found():
    import envstack.wrapper as w

    rc, out, err = w.capture_output("definitely_not_a_real_command_12345")

    assert rc != 0
    assert out.strip() == ""
    # err message varies widely; just ensure something was produced
    assert err.strip() != ""
