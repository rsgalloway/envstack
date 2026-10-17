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
Contains unit tests for the util.py module.
"""

import os
import unittest
from unittest.mock import patch

from envstack import config, util
from envstack.util import (
    dedupe_list,
    dedupe_paths,
    detect_path,
    encode,
    evaluate_command,
    get_stack_name,
    partition_platform_data,
    safe_eval,
    split_paths,
    split_posix_paths,
    split_windows_paths,
)


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
        # TODO: uncomment to test colon delimiter and lowercase drive letters
        # self.assertTrue(detect_path("c:\\Program Files\\Python:d:/path2:e:/path3"))
        self.assertTrue(detect_path("X:/path/to/folder;Z:/folder2"))
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

        # TODO: uncomment to test colon delimiter and lowercase drive letters
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
        expected_result = os.pathsep.join(["/usr/bin", "/usr/local/bin", "/some/other/path"])
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
        self.assertEqual(result, "C:\\Program Files\\Python;D:/path2;E:/path3;/usr/local/bin")

        # mixed paths
        path = "//tools/pipe/prod/env;//tools/pipe/prod/env;/home/user/envstack/env"
        result = dedupe_paths(path, platform="windows")
        self.assertEqual(result, "//tools/pipe/prod/env;/home/user/envstack/env")

        # mixed paths with duplicate
        path = "C:\\Program Files\\Python;D:/path2;E:/path3;/usr/local/bin:/usr/local/bin"
        result = dedupe_paths(path, platform="windows")
        self.assertEqual(result, "C:\\Program Files\\Python;D:/path2;E:/path3;/usr/local/bin")


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


class TestEvaluateCommand(unittest.TestCase):
    """Tests for evaluate_command function."""

    def test_no_match_returns_original_and_does_not_call_capture(self):
        with patch("envstack.wrapper.capture_output") as cap:
            s = "PYVERSION=${PYVERSION:=default}"
            self.assertEqual(evaluate_command(s), s)
            cap.assert_not_called()

    def test_success_returns_stripped_stdout(self):
        with patch(
            "envstack.wrapper.capture_output", return_value=(0, "Python 3.8.17\n", "")
        ) as cap:
            self.assertEqual(evaluate_command("$(python --version)"), "Python 3.8.17")
            cap.assert_called_once_with("python --version")

    def test_failure_returns_stripped_stderr(self):
        with patch(
            "envstack.wrapper.capture_output",
            return_value=(127, "", "python4: command not found\n"),
        ) as cap:
            self.assertEqual(
                evaluate_command("$(python4 --version)"),
                "python4: command not found",
            )
            cap.assert_called_once_with("python4 --version")

    def test_failure_returns_null_when_no_stderr(self):
        with patch("envstack.wrapper.capture_output", return_value=(1, "", "")) as cap:
            self.assertEqual(evaluate_command("$(somecmd)"), util.null)
            cap.assert_called_once_with("somecmd")


if __name__ == "__main__":
    unittest.main()
