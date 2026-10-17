"""CLI variable selection without launching a shell or installed executable."""

import sys

import pytest

from envstack import cli
from envstack import env as env_module


@pytest.fixture
def run_cli(tmp_path, monkeypatch, capsys):
    (tmp_path / "sample.env").write_text("all:\n  ROOT: /base\n  LIB: ${ROOT}/lib\n  EMPTY: ''\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ENVPATH", str(tmp_path))
    monkeypatch.setattr(env_module, "seen_stacks", set())

    def run(*args):
        monkeypatch.setattr(sys, "argv", ["envstack", *args])
        status = cli.main()
        return status or 0, capsys.readouterr().out

    return run


@pytest.mark.parametrize("option", ["-u", "--unresolved"])
def test_unresolved_variable_selection(run_cli, option):
    assert run_cli("sample", option, "LIB", "EMPTY") == (0, "EMPTY=\nLIB=${ROOT}/lib\n")


def test_unresolved_without_variables_keeps_full_output(run_cli):
    status, output = run_cli("sample", "-u")
    assert status == 0
    assert "LIB=${ROOT}/lib\n" in output
    assert "ROOT=/base\n" in output
    assert "STACK=sample\n" in output


@pytest.mark.parametrize("option,expected", [("-u", "${ROOT}/lib\n"), ("-r", "/base/lib\n")])
def test_selected_value_quiet(run_cli, option, expected):
    assert run_cli("sample", option, "LIB", "-q") == (0, expected)


def test_unresolved_quiet_rejects_multiple_variables(run_cli):
    status, output = run_cli("sample", "-u", "ROOT", "LIB", "-q")
    assert status == 2
    assert output == "error: --quiet requires exactly one KEY\n"


@pytest.mark.parametrize("option", ["-u", "-r"])
def test_unknown_variable_is_omitted(run_cli, option):
    assert run_cli("sample", option, "UNKNOWN") == (0, "")


def test_unresolved_repeated_option_rejected(run_cli):
    with pytest.raises(SystemExit) as exc:
        run_cli("sample", "-u", "LIB", "-u", "ROOT")
    assert exc.value.code == 2
