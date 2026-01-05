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

__doc__ = """
Contains unit tests for running commands.
"""

import os
import pytest

import envstack.wrapper as wrapper_mod
from envstack.wrapper import Wrapper, CommandWrapper, run_command


@pytest.fixture
def stub_env(monkeypatch):
    """
    Make wrapper tests independent of real envstack stack files.

    We monkeypatch load_environ(namespace) to return a deterministic env.
    Adjust ROOT/ENV values as needed.
    """
    def _fake_load_environ(namespace):
        # minimal env for tests; include PATH so subprocess can find tools
        env = dict(os.environ)
        env["ENV"] = namespace or "prod"
        env["ROOT"] = "/tmp/envstack-root"
        return env

    monkeypatch.setattr(wrapper_mod, "load_environ", _fake_load_environ)
    return _fake_load_environ


class HelloWrapper(Wrapper):
    """
    Example wrapper that prints an env var passed as argv[0].
    Uses shell=True because executable() returns a command-line string.
    """
    shell = True

    def executable(self):
        # prints env var named by first arg
        return "python3 -c 'import os,sys;print(os.getenv(sys.argv[1]))'"


def test_wrapper_shell_true_allows_command_string(stub_env, capfd):
    """Test that Wrapper with shell=True runs command string."""
    w = HelloWrapper("hello", ["ROOT"])
    rc = w.launch()
    out, err = capfd.readouterr()
    assert rc == 0
    assert out.strip() == "/tmp/envstack-root"


def test_commandwrapper_runs_argv_without_shell(stub_env, capfd):
    """Test that CommandWrapper runs argv mode without shell."""
    w = CommandWrapper("hello", ["echo", "hi there"])
    rc = w.launch()
    out, err = capfd.readouterr()
    assert rc == 0
    assert out.strip() == "hi there"


def test_run_command_preserves_quoted_arg_in_argv_mode(stub_env):
    """Test that run_command preserves quoted args when shell=False."""
    # Regression for: envstack -- bash -c "sleep 5" breaking into bash -c sleep 5
    # Here we use something observable instead of sleep.
    rc = run_command(["bash", "-c", "printf '%s\n' \"sleep 5\""], namespace="hello")
    assert rc == 0


def test_run_command_brace_expands_to_env_value(stub_env, capfd):
    """Test that {VAR} in command args expands to env var value."""
    rc = run_command(["echo", "{ROOT}"], namespace="hello")
    out, err = capfd.readouterr()
    assert rc == 0
    assert out.strip() == "/tmp/envstack-root"


def test_run_command_two_in_series_no_stop(stub_env, capfd):
    """Test that two commands run in series without stopping the process."""
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
def test_interactive_env_override_parsing(stub_env, monkeypatch, override, expected):
    env = dict(os.environ)
    env["INTERACTIVE"] = override

    # example: if you implemented ShellWrapper.get_interactive(env)
    ShellWrapper = getattr(wrapper_mod, "ShellWrapper", None)
    if ShellWrapper is None:
        pytest.skip("ShellWrapper not present in envstack.wrapper")

    sw = ShellWrapper("hello", "echo test")
    assert sw.get_interactive(env) is expected
