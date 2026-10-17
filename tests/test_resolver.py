#!/usr/bin/env python3
#
# Copyright (c) 2024-2026, Ryan Galloway (ryan@rsgalloway.com)
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
Tests for variable expansion and environment resolution.
"""

import os
import unittest

import pytest

from envstack.env import resolve_environ
from envstack.resolver import evaluate_modifiers
from envstack.util import null


class TestEvaluateModifiers(unittest.TestCase):
    """Tests for evaluate_modifiers function."""

    def test_no_substitution(self):
        """Test no substitution."""
        expression = "world"
        result = evaluate_modifiers(expression)
        self.assertEqual(result, "world")

    def test_http_url_value(self):
        """Test a url value."""
        expression = "https://example.com"
        result = evaluate_modifiers(expression)
        self.assertEqual(result, "https://example.com")

    def test_s3_url_value(self):
        """Test a s3 url value."""
        expression = "s3://bucket.amazonaws.com"
        result = evaluate_modifiers(expression)
        self.assertEqual(result, "s3://bucket.amazonaws.com")

    def test_git_url_value(self):
        """Test a git url value."""
        expression = "git://path/to/repo.git"
        result = evaluate_modifiers(expression)
        self.assertEqual(result, "git://path/to/repo.git")

    def test_direct_substitution(self):
        """Test direct substitution."""
        expression = "${VAR}"
        environ = {"VAR": "hello"}
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, "hello")

    def test_default_null_value(self):
        """Test var null value."""
        expression = "${VAR}"
        environ = {}
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, null)

    def test_default_value(self):
        """Test default value."""
        expression = "${VAR:=default}"
        environ = {"VAR": "hello"}
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, "hello")

    def test_default_value_empty_env(self):
        """Test default value with empty environment."""
        expression = "${VAR:=default}"
        environ = {}
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, "default")

    def test_pathlike_value(self):
        """Test path-like value with two vars."""
        expression = "${ROOT}/${ENV}"
        environ = {"ROOT": "/usr/local", "ENV": "env"}
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, "/usr/local/env")

    def test_pathlike_value_colon_separated(self):
        """Test colon-separated path-like value with two vars."""
        expression = "${DEPLOY_ROOT}/env:${ENVPATH}"
        environ = {"DEPLOY_ROOT": "/usr/local/lib", "ENVPATH": "/mnt/env"}
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, f"/usr/local/lib/env{os.pathsep}/mnt/env")

    def test_tokenized_value_single(self):
        """Test tokenized value with a single token."""
        expression = "${ROOT}/{foo}"
        environ = {
            "ROOT": "/var/tmp",
        }
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, r"/var/tmp/{foo}")

    def test_tokenized_value_trailing_slash(self):
        """Test tokenized value with a single token and trailing slash."""
        expression = "${ROOT}/{foo}/"
        environ = {
            "ROOT": "/var/tmp",
        }
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, r"/var/tmp/{foo}/")

    def test_tokenized_value_two_tokens(self):
        """Test tokenized value with two tokens."""
        expression = "${ROOT}/{foo}/{bar}"
        environ = {
            "ROOT": "/var/tmp",
        }
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, r"/var/tmp/{foo}/{bar}")

    def test_tokenized_value_three_tokens(self):
        """Test tokenized value with three tokens."""
        expression = "${ROOT}/{foo}/{bar}/{baz}"
        environ = {
            "ROOT": "/var/tmp",
        }
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, r"/var/tmp/{foo}/{bar}/{baz}")

    def test_tokenized_value_three_tokens_slash(self):
        """Test tokenized value with three tokens and a trailing slash."""
        expression = "${ROOT}/{foo}/{bar}/{baz}/"
        environ = {
            "ROOT": "/var/tmp",
        }
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, r"/var/tmp/{foo}/{bar}/{baz}/")

    def test_default_value_with_default_args(self):
        """Test default value with default args."""
        expression = "${HELLO:=world}"
        result = evaluate_modifiers(expression)
        self.assertEqual(result, os.getenv("HELLO", "world"))

    def test_error_message(self):
        """Test error message."""
        expression = "${VAR:?error message}"
        environ = {"VAR": "hello"}
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, "hello")

    def test_error_message_raise(self):
        """Test error message raise."""
        expression = "${VAR:?error message}"
        environ = {}
        with self.assertRaises(ValueError):
            evaluate_modifiers(expression, environ)

    def test_cyclical_reference_error(self):
        """Test variable with cyclic reference is empty string."""
        expression = "${VAR}"
        environ = {"VAR": "${FOO}", "FOO": "${BAR}", "BAR": "${VAR}"}
        value = evaluate_modifiers(expression, environ)
        self.assertEqual(value, "")

    def test_multiple_substitutions(self):
        """Test multiple substitutions."""
        expression = "${VAR}/${FOO:=foobar}/${BAR:?error message}"
        environ = {"VAR": "hello", "BAR": "world"}
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, "hello/foobar/world")

    def test_embedded_substitution(self):
        """Test embedded substitution with default."""
        expression = "${VAR:=${FOO:=bar}}"
        environ = {"FOO": "foo"}
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, "foo")

    def test_embedded_substitution_default(self):
        """Test embedded substitution with default."""
        expression = "${VAR:=${FOO:=bar}}"
        environ = {}
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, "bar")

    def test_embedded_substitution_value_var(self):
        """Test embedded substitution with value for VAR."""
        expression = "${VAR:=${FOO}}"
        environ = {"VAR": "foobar"}
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, "foobar")

    def test_embedded_substitution_value_var_foo(self):
        """Test embedded substitution with values for VAR and FOO."""
        expression = "${VAR:=${FOO}}"
        environ = {"VAR": "foobar", "FOO": "barfoo"}
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, "foobar")

    def test_embedded_substitution_value_foo(self):
        """Test embedded substitution with value for FOO."""
        expression = "${VAR:=${FOO}}"
        environ = {"FOO": "barfoo"}
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, "barfoo")

    def test_embedded_substitution_value_var_slashes(self):
        """Test embedded substitution with value with special chars."""
        expression = "${VAR:=${FOO}}"
        environ = {"VAR": "/foo/bar"}
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, "/foo/bar")

    def test_embedded_substitution_value_bar_slashes(self):
        """Test embedded substitution with value with special chars."""
        expression = "${VAR:=${FOO}}"
        environ = {"FOO": "/bar/foo"}
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, "/bar/foo")

    def test_embedded_substitution_multiple_one(self):
        """Test multiple embedded substitution."""
        expression = "${VAR:=${FOO:=${BAR}}}"
        environ = {"BAR": "/foo/bar"}
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, "/foo/bar")

    def test_embedded_substitution_multiple_two(self):
        """Test multiple embedded substitution with value."""
        expression = "${VAR:=${FOO:=${BAR}}}"
        environ = {"FOO": "/test/a/b/c"}
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, "/test/a/b/c")

    def test_embedded_substitution_multiple_three(self):
        """Test multiple embedded substitution with value."""
        expression = "${VAR:=${FOO:=${BAR}}}"
        environ = {"VAR": "/test/x/y/z"}
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, "/test/x/y/z")

    def test_embedded_substitution_multiple_default(self):
        """Test multiple embedded substitution with default value."""
        expression = "${VAR:=${FOO:=${BAR:=/foo/bar/baz}}}"
        environ = {}
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, "/foo/bar/baz")

    def test_embedded_substitution_multiple_env(self):
        """Test multiple embedded substitution with value from env."""
        expression = "${VAR:=${FOO:=${BAR:=/foo/bar/baz}}}"
        environ = {"FOO": "/a/b/c"}
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, "/a/b/c")

    def test_embedded_substitution_prefix(self):
        """Test embedded substitution with prefix."""
        expression = "${VAR:=default}/path"
        environ = {"VAR": "value"}
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, "value/path")

    def test_embedded_substitution_prefix_default(self):
        """Test embedded substitution with prefix with default."""
        expression = "${VAR:=default}/path"
        environ = {}
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, "default/path")

    def test_embedded_substitution_default_one_var_dash(self):
        """Test embedded substitution with one var default dash"""
        expression = "${VAR:=${FOO}-bar}"
        environ = {"FOO": "foo"}
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, "foo-bar")

    def test_embedded_substitution_default_one_var_slash(self):
        """Test embedded substitution with one var default slash"""
        expression = "${VAR:=${FOO}/bar}"
        environ = {"FOO": "foo"}
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, "foo/bar")

    def test_embedded_substitution_default_two_vars(self):
        """Test embedded substitution with two var default."""
        expression = "${VAR:=${FOO}/${BAR}}"
        environ = {"FOO": "foo", "BAR": "bar"}
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, "foo/bar")

    def test_embedded_substitution_default_two_vars_alt_1(self):
        """Test embedded substitution with two var default, alt 1."""
        expression = "${VAR:=/${FOO}/${BAR:=bar}}"
        environ = {"FOO": "foo", "BAR": "baz"}
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, "/foo/baz")

    def test_embedded_substitution_default_two_vars_alt_2(self):
        """Test embedded substitution with two var default, alt 2."""
        expression = "${VAR:=/${FOO}/${FOO}}"
        environ = {"FOO": "foo", "BAR": "bar"}
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, "/foo/foo")

    def test_embedded_substitution_default_two_vars_alt_3(self):
        """Test embedded substitution with two var default, alt 3."""
        expression = "${VAR:=/${FOO}}/${FOO}"
        environ = {"FOO": "foo", "BAR": "bar"}
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, "/foo/foo")

    def test_embedded_substitution_default_two_vars_alt_4(self):
        """Test embedded substitution with two var default, alt 4."""
        expression = "${VAR:=/${FOO}}/${BAR:=bar}"
        environ = {"FOO": "foo", "BAR": "baz"}
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, "/foo/baz")

    def test_embedded_substitution_default_three_vars(self):
        """Test embedded substitution with three vars."""
        expression = "${VAR:=/${FOO}/${BAR}/${BAZ:=baz}}"
        environ = {"FOO": "foo", "BAR": "bar"}
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, "/foo/bar/baz")

    def test_embedded_substitution_default_three_vars_alt_1(self):
        """Test embedded substitution with three vars, atl 1."""
        expression = "${VAR:=/${FOO}}/${BAR}/${BAZ:=baz}"
        environ = {"FOO": "foo", "BAR": "bar"}
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, "/foo/bar/baz")

    def test_embedded_substitution_default_two_vars_from_env(self):
        """Test embedded substitution with default, value from environ."""
        expression = "${VAR:=${FOO}/${BAR}}"
        environ = {"VAR": "/env/value", "FOO": "foo", "BAR": "bar"}
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, "/env/value")


class TestIssue18(unittest.TestCase):
    """Tests for issue #18."""

    def test_non_cyclical_reference_error_1(self):
        """Test non-cyclical reference with self-referencing."""
        expression = "${FOO}"
        environ = {"FOO": "${FOO}"}
        self.assertEqual(evaluate_modifiers(expression, environ), "")

    def test_non_cyclical_reference_error_2(self):
        """Test non-cyclical reference with self-referencing."""
        expression = "${FOO}"
        environ = {"FOO": "foo:${FOO}"}
        self.assertEqual(evaluate_modifiers(expression, environ), "foo:")

    def test_non_cyclical_reference_error_3(self):
        """Test non-cyclical reference with self-referencing."""
        expression = "${FOO}"
        environ = {"FOO": "bar/${FOO}"}
        self.assertEqual(evaluate_modifiers(expression, environ), "bar/")

    def test_cyclical_reference_error_1(self):
        """Test variable with cyclic reference is empty string."""
        expression = "${VAR}"
        environ = {"VAR": "${FOO}", "FOO": "${BAR}", "BAR": "${VAR}"}
        value = evaluate_modifiers(expression, environ)
        self.assertEqual(value, "")

    def test_cyclical_reference_error_2(self):
        """Test variable with cyclic reference is empty string."""
        expression = "${FOO}"
        environ = {"FOO": "${BAR}", "BAR": "${FOO}"}
        value = evaluate_modifiers(expression, environ)
        self.assertEqual(value, "")


@pytest.mark.parametrize("defined_empty", [False, True], ids=["unset", "empty"])
@pytest.mark.parametrize("operator,expected", [(":=", "hello|hello|hello"), (":-", "hello||world")])
def test_default_assignment_and_fallback(monkeypatch, defined_empty, operator, expected):
    monkeypatch.delenv("A", raising=False)
    env = {"A": ""} if defined_empty else {}
    env["B"] = "${A" + operator + "hello}|${A}|${A" + operator + "world}"
    original = dict(env)

    assert resolve_environ(env)["B"] == expected
    assert env == original


def test_cycles_without_inherited_values_terminate(monkeypatch):
    for key in ("FOO", "BAR"):
        monkeypatch.delenv(key, raising=False)
    assert dict(resolve_environ({"FOO": "${BAR}", "BAR": "${FOO}"})) == {"FOO": "", "BAR": ""}


@pytest.mark.parametrize("entry_point", ["environment", "expression"])
@pytest.mark.parametrize("shell", [None, "shell"])
@pytest.mark.parametrize(
    "expression,expected",
    [
        ("${A}", ""),
        ("${A:-hello}|${A}", "hello|"),
        ("${A:=hello}|${A}|${A:=world}", "hello|hello|hello"),
    ],
)
def test_explicit_empty_overrides_shell(monkeypatch, entry_point, shell, expression, expected):
    if shell is None:
        monkeypatch.delenv("A", raising=False)
    else:
        monkeypatch.setenv("A", shell)
    env = {"A": ""}
    if entry_point == "expression":
        actual = evaluate_modifiers(expression, env)
    else:
        env["B"] = expression
        actual = resolve_environ(env)["B"]
    assert actual == expected


@pytest.mark.parametrize("value", [None, "${A}"])
def test_absent_or_self_referencing_variable_uses_shell(monkeypatch, value):
    monkeypatch.setenv("A", "shell")
    env = {"B": "${A}"}
    if value is not None:
        env["A"] = value
    assert resolve_environ(env)["B"] == "shell"
