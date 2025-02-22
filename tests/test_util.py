#!/usr/bin/env python
#
# Copyright (c) 2024, Ryan Galloway (ryan@rsgalloway.com)
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
    encode,
    evaluate_modifiers,
    get_stack_name,
    partition_platform_data,
    safe_eval,
)


class TestEvaluateModifiers(unittest.TestCase):
    def test_no_substitution(self):
        expression = "world"
        result = evaluate_modifiers(expression)
        self.assertEqual(result, "world")

    def test_direct_substitution(self):
        expression = "${VAR}"
        environ = {"VAR": "hello"}
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, "hello")

    def test_default_value(self):
        expression = "${VAR:=default}"
        environ = {"VAR": "hello"}
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, "hello")

    def test_default_value_empty_env(self):
        expression = "${VAR:=default}"
        environ = {}
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, "default")

    def test_default_value_with_default_args(self):
        expression = "${HELLO:=world}"
        result = evaluate_modifiers(expression)
        self.assertEqual(result, os.getenv("HELLO", "world"))

    def test_error_message(self):
        expression = "${VAR:?error message}"
        environ = {"VAR": "hello"}
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, "hello")

    def test_error_message_raise(self):
        expression = "${VAR:?error message}"
        environ = {}
        with self.assertRaises(ValueError):
            evaluate_modifiers(expression, environ)

    def test_cyclical_reference_error(self):
        expression = "${VAR}"
        environ = {"VAR": "${FOO}", "FOO": "${BAR}", "BAR": "${VAR}"}
        with self.assertRaises(CyclicalReference):
            evaluate_modifiers(expression, environ)

    def test_multiple_substitutions(self):
        expression = "${VAR}/${FOO:=foobar}/${BAR:?error message}"
        environ = {"VAR": "hello", "BAR": "world"}
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, "hello/foobar/world")


class TestUtils(unittest.TestCase):
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


class TestDedupePaths(unittest.TestCase):
    def test_dedupe_list(self):
        """Test dedupe_list function."""
        from envstack.util import dedupe_list

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
        from envstack.util import dedupe_paths

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
        from envstack.util import dedupe_paths

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


class TestSafeEval(unittest.TestCase):
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
    def test_partition_platform_data(self):
        data = {
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
