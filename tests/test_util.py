#!/usr/bin/env python
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
Contains unit tests for the util.py module.
"""

import os
import unittest

from envstack import config
from envstack.exceptions import CyclicalReference
from envstack.util import (
    null,
    encode,
    evaluate_modifiers,
    dedupe_list,
    dedupe_paths,
    detect_path,
    get_stack_name,
    partition_platform_data,
    safe_eval,
    split_paths,
    split_posix_paths,
    split_windows_paths,
)


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
        """Test cyclical reference error."""
        expression = "${VAR}"
        environ = {"VAR": "${FOO}", "FOO": "${BAR}", "BAR": "${VAR}"}
        with self.assertRaises(CyclicalReference):
            evaluate_modifiers(expression, environ)

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


class TestUtils(unittest.TestCase):
    """Tests for util.py module."""

    def test_encode(self):
        env = {
            "VAR1": "value1",
            "VAR2": 1,
            "VAR3": 4.5,
        }
        encoded_env = encode(env)
        expected_encoded_env = {
            "VAR1": "value1",
            "VAR2": "1",
            "VAR3": "4.5",
        }
        self.assertEqual(encoded_env, expected_encoded_env)

    def test_detect_path(self):
        self.assertTrue(detect_path("/usr/bin:/usr/local/bin:/some/other/path"))
        self.assertTrue(detect_path("/usr/bin"))
        self.assertTrue(detect_path("C:\\Program Files\\Python;D:/path2;E:/path3"))
        self.assertTrue(detect_path("c:\\Program Files\\Python:d:/path2:e:/path3"))
        self.assertTrue(detect_path("x:/path/to/folder;z:/folder2"))
        self.assertTrue(detect_path("C:\\Program Files\\Python"))
        self.assertTrue(detect_path("C:/Program Files/Python/site-packages"))
        self.assertTrue(detect_path("/path/to/some/file.txt"))
        self.assertTrue(detect_path("\\\\server\\share\\path\\to\\folder"))
        self.assertFalse(detect_path("http://example.com"))
        self.assertFalse(detect_path("https://example.com"))
        self.assertFalse(detect_path("git://path/to/repo.git"))
        self.assertFalse(detect_path("s3://bucket.amazonaws.com"))
        self.assertFalse(detect_path("README"))
        self.assertFalse(detect_path("README.txt"))
        self.assertFalse(detect_path("example.com"))
        self.assertFalse(detect_path(""))

    def test_get_stack_name_string(self):
        name = "stack_name"
        result = get_stack_name(name)
        self.assertEqual(result, "stack_name")

    def test_get_stack_name_tuple(self):
        name = ("namespace", "stack_name")
        result = get_stack_name(name)
        self.assertEqual(result, "stack_name")

    def test_get_stack_name_list(self):
        name = ["namespace", "stack_name"]
        result = get_stack_name(name)
        self.assertEqual(result, "stack_name")

    def test_get_stack_name_empty(self):
        name = []
        result = get_stack_name(name)
        self.assertEqual(result, config.DEFAULT_NAMESPACE)

    def test_get_stack_name_invalid_type(self):
        name = 123
        with self.assertRaises(ValueError):
            get_stack_name(name)

    def test_unquote_strings(self):
        content = """#!/usr/bin/env envstack
include: ['other']
all: &all
  KEY: !base64 'VGhpcyBpcyBlbmNyeXB0ZWQ='
darwin:
  '<<': '*all'
        """
        import tempfile
        from envstack.util import unquote_strings

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
            temp_file.write(content)

        unquote_strings(temp_file.name)

        with open(temp_file.name, "r") as modified_file:
            modified_content = modified_file.read()

        expected_content = """#!/usr/bin/env envstack
include: [other]
all: &all
  KEY: !base64 VGhpcyBpcyBlbmNyeXB0ZWQ=
darwin:
  <<: *all
        """
        self.assertEqual(modified_content, expected_content)

        os.remove(temp_file.name)


class TestSplitPaths(unittest.TestCase):
    """Tests for path splitting functions."""

    def test_split_posix_paths(self):
        """Test split_posix_paths function."""

        paths = "/usr/bin:/usr/local/bin:/some/other/path"
        result = split_posix_paths(paths)
        self.assertEqual(result, ["/usr/bin", "/usr/local/bin", "/some/other/path"])

        paths = "/usr/bin"
        result = split_posix_paths(paths)
        self.assertEqual(result, ["/usr/bin"])

        paths = ""
        result = split_posix_paths(paths)
        self.assertEqual(result, [])

    def test_split_windows_paths(self):
        """Test split_windows_paths function."""

        paths = "C:\\Program Files\\Python;D:/path2;E:/path3"
        result = split_windows_paths(paths)
        self.assertEqual(result, ["C:\\Program Files\\Python", "D:/path2", "E:/path3"])

        # same path but using colon delimiter
        paths = "C:\\Program Files\\Python:D:/path2:E:/path3"
        result = split_windows_paths(paths)
        self.assertEqual(result, ["C:\\Program Files\\Python", "D:/path2", "E:/path3"])

        # lowercase drive letter
        # paths = "c:\\Program Files\\Python:d:/path2:e:/path3"
        # result = split_windows_paths(paths)
        # self.assertEqual(result, ["c:\\Program Files\\Python", "d:/path2", "e:/path3"])

        paths = "C:\\Program Files\\Python"
        result = split_windows_paths(paths)
        self.assertEqual(result, ["C:\\Program Files\\Python"])

        paths = ""
        result = split_windows_paths(paths)
        self.assertEqual(result, [])

    def test_split_paths(self):
        """Test split_paths function."""

        paths = "/usr/bin:/usr/local/bin:/some/other/path"
        result = split_paths(paths)
        self.assertEqual(result, ["/usr/bin", "/usr/local/bin", "/some/other/path"])

        paths = "/usr/bin"
        result = split_paths(paths)
        self.assertEqual(result, ["/usr/bin"])

        # will paths and urls ever be mixed?
        # paths = "/usr/bin:http://example.com"
        # result = split_paths(paths)
        # self.assertEqual(result, ["/usr/bin", "http://example.com"])

        paths = ""
        result = split_paths(paths)
        self.assertEqual(result, [])

    def test_split_paths_windows(self):
        """Test split_paths function on windows."""

        paths = "C:\\Program Files\\Python;D:/path2;E:/path3"
        result = split_paths(paths, platform="windows")
        self.assertEqual(result, ["C:\\Program Files\\Python", "D:/path2", "E:/path3"])

        paths = "C:\\Program Files\\Python:D:/path2:E:/path3"
        result = split_paths(paths, platform="windows")
        self.assertEqual(result, ["C:\\Program Files\\Python", "D:/path2", "E:/path3"])

        paths = "C:\\Program Files\\Python"
        result = split_paths(paths, platform="windows")
        self.assertEqual(result, ["C:\\Program Files\\Python"])

        paths = ""
        result = split_paths(paths, platform="windows")
        self.assertEqual(result, [])


class TestDedupePaths(unittest.TestCase):
    """Tests for dedupe_paths function."""

    def test_dedupe_list(self):
        """Test dedupe_list function."""

        paths = [
            "/usr/bin",
            "/usr/local/bin",
            "/usr/local/bin",
            "/usr/bin",
            "/usr/local/bin",
            "/some/other/path",
        ]
        result = dedupe_list(paths)
        self.assertEqual(result, ["/usr/bin", "/usr/local/bin", "/some/other/path"])

        paths = ["/usr/bin"]
        result = dedupe_list(paths)
        self.assertEqual(result, ["/usr/bin"])

        paths = []
        result = dedupe_list(paths)
        self.assertEqual(result, [])

    def test_dedupe_paths(self):
        """Test dedupe_paths function."""

        paths = [
            "/usr/bin",
            "/usr/local/bin",
            "/usr/bin",
            "/usr/local/bin",
            "",
            "/usr/local/bin",
            "/some/other/path",
        ]
        result = dedupe_paths(":".join(paths))
        expected_result = os.pathsep.join(
            ["/usr/bin", "/usr/local/bin", "/some/other/path"]
        )
        self.assertEqual(result, expected_result)

        paths = ["/usr/bin"]
        result = dedupe_paths(":".join(paths))
        self.assertEqual(result, "/usr/bin")

        paths = ["/usr/bin", ""]
        result = dedupe_paths(os.pathsep.join(paths))
        self.assertEqual(result, "/usr/bin")

        paths = []
        result = dedupe_paths(":".join(paths))
        self.assertEqual(result, "")

    def test_dedupe_paths_windows(self):
        """Test dedupe_paths function on windows."""

        paths = [
            "C:\\Program Files\\Python",
            "D:/path2",
            "E:/path3",
        ]
        result = dedupe_paths(":".join(paths), platform="windows")
        self.assertEqual(result, "C:\\Program Files\\Python;D:/path2;E:/path3")

        paths = [
            "C:\\Program Files\\Python",
            "C:\\Program Files\\Python",
            "D:/path2",
            "E:/path3",
            "E:/path3",
            "/usr/local/bin",
        ]
        path = ":".join(paths)
        result = dedupe_paths(path, platform="windows")
        self.assertEqual(
            result, "C:\\Program Files\\Python;D:/path2;E:/path3;/usr/local/bin"
        )

        # mixed paths
        path = "X:/pipe/prod/env;X:/pipe/prod/env:/home/user/envstack/env"
        result = dedupe_paths(path, platform="windows")
        self.assertEqual(result, "X:/pipe/prod/env;/home/user/envstack/env")

        # mixed paths with duplicate
        path = (
            "C:\\Program Files\\Python;D:/path2;E:/path3:/usr/local/bin:/usr/local/bin"
        )
        result = dedupe_paths(path, platform="windows")
        self.assertEqual(
            result, "C:\\Program Files\\Python;D:/path2;E:/path3;/usr/local/bin"
        )

        # mixed paths with url (will urls ever be mixed with paths?)
        # path = (
        #     "C:\\Program Files\\Python;/usr/local/bin:D:/path2:https://test.com"
        # )
        # result = dedupe_paths(path, platform="windows")
        # self.assertEqual(
        #     result, "C:\\Program Files\\Python;/usr/local/bin;D:/path2;https://test.com"
        # )


class TestSafeEval(unittest.TestCase):
    """Tests for safe_eval function."""

    def test_safe_eval_string(self):
        value = "hello"
        result = safe_eval(value)
        self.assertEqual(result, "hello")

    def test_safe_eval_integer(self):
        value = "123"
        result = safe_eval(value)
        self.assertEqual(result, 123)

    def test_safe_eval_float(self):
        value = "3.14"
        result = safe_eval(value)
        self.assertEqual(result, 3.14)

    def test_safe_eval_list(self):
        value = "['a', 'b', 'c']"
        result = safe_eval(value)
        self.assertEqual(result, ["a", "b", "c"])

    def test_safe_eval_dict(self):
        value = "{'key': 'value'}"
        result = safe_eval(value)
        self.assertEqual(result, {"key": "value"})

    def test_safe_eval_invalid_value(self):
        value = "invalid"
        result = safe_eval(value)
        self.assertEqual(result, "invalid")


class TestPartitionPlatformData(unittest.TestCase):
    """Tests for partition_platform_data function."""

    def test_partition_platform_data_empty(self):
        """Test partition_platform_data with empty data."""
        data = {}
        result = partition_platform_data(data)
        expected_result = {
            "include": [],
            "all": {
                "<<": "*all",
            },
            "darwin": {
                "<<": "*all",
            },
            "linux": {
                "<<": "*all",
            },
            "windows": {
                "<<": "*all",
            },
        }
        self.assertEqual(result, expected_result)

    def test_partition_platform_data_empty_includes(self):
        """Test partition_platform_data with empty includes."""
        data = {"include": []}
        result = partition_platform_data(data)
        expected_result = {
            "include": [],
            "all": {
                "<<": "*all",
            },
            "darwin": {
                "<<": "*all",
            },
            "linux": {
                "<<": "*all",
            },
            "windows": {
                "<<": "*all",
            },
        }
        self.assertEqual(result, expected_result)

    def test_partition_platform_data(self):
        """Test partition_platform_data with data."""
        data = {
            "include": [],
            "all": {
                "key1": "value1",
                "key2": "value2",
                "key3": "value3",
            },
            "darwin": {
                "key1": "value1",
                "key2": "value2",
                "key3": "darwin_value3",
                "key4": "darwin_value4",
            },
            "linux": {
                "key1": "value1",
                "key2": "value2",
                "key3": "linux_value3",
                "key4": "linux_value4",
            },
            "windows": {
                "key1": "value1",
                "key2": "value2",
                "key3": "windows_value3",
                "key4": "windows_value4",
            },
        }

        expected_result = {
            "include": [],
            "all": {
                "<<": "*all",
                "key1": "value1",
                "key2": "value2",
                # "key3": "value3",  # key3 removed, is that what we want?
            },
            "darwin": {
                "<<": "*all",
                "key3": "darwin_value3",
                "key4": "darwin_value4",
            },
            "linux": {
                "<<": "*all",
                "key3": "linux_value3",
                "key4": "linux_value4",
            },
            "windows": {
                "<<": "*all",
                "key3": "windows_value3",
                "key4": "windows_value4",
            },
        }

        result = partition_platform_data(data)
        self.assertEqual(result, expected_result)


class TestIssue18(unittest.TestCase):
    """Tests for issue #18."""

    def test_non_cyclical_reference_error_1(self):
        expression = "${FOO}"
        environ = {"FOO": "${FOO}"}
        self.assertEqual(evaluate_modifiers(expression, environ), "")

    def test_non_cyclical_reference_error_2(self):
        expression = "${FOO}"
        environ = {"FOO": "foo:${FOO}"}
        self.assertEqual(evaluate_modifiers(expression, environ), "foo:")

    def test_non_cyclical_reference_error_3(self):
        expression = "${FOO}"
        environ = {"FOO": "bar/${FOO}"}
        self.assertEqual(evaluate_modifiers(expression, environ), "bar/")

    def test_cyclical_reference_error_1(self):
        expression = "${VAR}"
        environ = {"VAR": "${FOO}", "FOO": "${BAR}", "BAR": "${VAR}"}
        with self.assertRaises(CyclicalReference):
            evaluate_modifiers(expression, environ)

    def test_cyclical_reference_error_2(self):
        expression = "${FOO}"
        environ = {"FOO": "${BAR}", "BAR": "${FOO}"}
        with self.assertRaises(CyclicalReference):
            evaluate_modifiers(expression, environ)


if __name__ == "__main__":
    unittest.main()
