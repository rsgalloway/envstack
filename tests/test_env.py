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
Contains unit tests for the env.py module.
"""

import os
import shutil
import sys
import unittest
import tempfile

import envstack
from envstack.env import Env, EnvVar, Scope, Source
from envstack.util import dict_diff


def create_test_root():
    """Creates a temporary directory with the contents of the "env" folder."""

    # create a temporary directory
    root = tempfile.mkdtemp()

    # copy the contents of the "env" folder to the temp dir
    env_path = os.path.join(os.path.dirname(__file__), "..", "env")

    for env in ("prod", "dev"):
        shutil.copytree(env_path, os.path.join(root, env, "env"))

    return root


def update_env_file(file_path: str, key: str, value: str):
    """Updates a key in a YAML file with a new value."""
    import yaml

    # read the YAML file
    with open(file_path, "r") as f:
        data = yaml.safe_load(f)

    for _, env_config in data.items():
        if isinstance(env_config, dict) and key in env_config:
            env_config[key] = value

    # write the modified data back to the file
    with open(file_path, "w") as f:
        yaml.safe_dump(data, f, sort_keys=False)


class TestEnvVar(unittest.TestCase):
    def test_init(self):
        v = EnvVar("$FOO:${BAR}")
        self.assertEqual(v.template, "$FOO:${BAR}")

    def test_eq(self):
        v1 = EnvVar("$FOO:${BAR}")
        v2 = EnvVar("$FOO:${BAR}")
        self.assertEqual(v1, v2)

    def test_iter(self):
        v = EnvVar("$FOO:${BAR}")
        self.assertEqual(list(v), ["$FOO", "${BAR}"])

    def test_append(self):
        v = EnvVar(["$FOO", "${BAR}"])
        v.append("baz")
        self.assertEqual(v.template, ["$FOO", "${BAR}", "baz"])

    def test_extend(self):
        v = EnvVar(["$FOO", "${BAR}"])
        v.extend(["baz", "qux"])
        self.assertEqual(v.template, ["$FOO", "${BAR}", "baz", "qux"])

    def test_expand(self):
        v = EnvVar("${BAR}")
        env = {"FOO": "foo", "BAR": "${FOO}"}
        value = v.expand(env)
        self.assertEqual(value, "foo")
        v = EnvVar("${FOO}:${BAR}")
        value = v.expand(env)
        self.assertEqual(value, "foo:foo")

    def test_parts(self):
        v = EnvVar("$FOO:${BAR}/bin")
        self.assertEqual(v.parts(), ["$FOO", "${BAR}/bin"])

    def test_vars(self):
        v = EnvVar("$FOO:${BAR}/bin")
        self.assertEqual(v.vars(), ["FOO", "BAR"])


class TestEnv(unittest.TestCase):
    def test_getitem(self):
        env = Env({"FOO": "foo", "BAR": "$FOO"})
        self.assertEqual(env["BAR"], "$FOO")

    def test_get(self):
        env = Env({"FOO": "foo", "BAR": "$FOO"})
        self.assertEqual(env.get("BAR"), "$FOO")
        self.assertEqual(env.get("BAZ"), None)
        self.assertEqual(env.get("BAZ", "default"), "default")

    def test_copy(self):
        env = Env({"FOO": "foo", "BAR": "$FOO"})
        copied = env.copy()
        self.assertEqual(copied, {"FOO": "foo", "BAR": "$FOO"})

    def test_set_namespace(self):
        env = Env()
        env.set_namespace("test")
        self.assertEqual(env.namespace, "test")

    def test_set_scope(self):
        env = Env()
        env.set_scope("/path/to/scope")
        self.assertEqual(env.scope, "/path/to/scope")


class TestScope(unittest.TestCase):
    def test_init(self):
        s = Scope("/path/to/scope")
        self.assertEqual(s.path, "/path/to/scope")


class TestSource(unittest.TestCase):
    def test_init(self):
        s = Source("/path/to/test.env")
        self.assertEqual(s.path, "/path/to/test.env")

    def test_eq(self):
        s1 = Source("/path/to/a.env")
        s2 = Source("/path/to/a.env")
        self.assertEqual(s1, s2)

    def test_ne(self):
        s1 = Source("/path/to/test.env")
        s2 = Source("/path/to/other.env")
        self.assertNotEqual(s1, s2)

    def test_str(self):
        s = Source("/path/to/test.env")
        self.assertEqual(str(s), "/path/to/test.env")

    def test_includes(self):
        s = Source("/path/to/.env")
        self.assertEqual(s.includes(), [])

    def test_length(self):
        s = Source("/path/to/.env")
        self.assertEqual(s.length(), len("/path/to/.env"))

    def test_load(self):
        s = Source("/path/to/.env")
        data = s.load()
        self.assertEqual(data, {})


class TestInit(unittest.TestCase):
    def test_init_default(self):
        """Tests init with default stack."""
        envpath = os.path.join(os.path.dirname(__file__), "..", "env")
        os.environ["ENVPATH"] = envpath
        os.environ["ROOT"] = "/var/tmp"  # cannot override ROOT
        os.environ["ENV"] = "foobar"  # cannot override ENV
        original_env = os.environ.copy()
        sys_path = sys.path.copy()
        path = os.getenv("PATH")
        python_path = os.getenv("PYTHONPATH")

        envstack.init()
        self.assertEqual(os.getenv("ENV"), os.getenv("ENV", "default"))
        self.assertEqual(os.getenv("STACK"), "default")
        self.assertEqual(os.getenv("HELLO"), "world")
        self.assertEqual(os.getenv("LOG_LEVEL"), "INFO")
        self.assertEqual(os.getenv("ROOT"), "/mnt/pipe")
        self.assertEqual(os.getenv("DEPLOY_ROOT"), "/mnt/pipe/prod")
        self.assertTrue(len(sys.path) > len(sys_path))
        self.assertTrue(len(os.getenv("PATH")) > len(path))
        self.assertTrue(len(os.getenv("PYTHONPATH")) > len(python_path))
        self.assertTrue("prod/lib/python" in os.getenv("PYTHONPATH"))
        self.assertTrue("prod/bin" in os.getenv("PATH"))

        envstack.revert()
        diffs = dict_diff(original_env, os.environ)
        self.assertEqual(diffs["added"], {})
        self.assertEqual(diffs["changed"], {})
        self.assertEqual(diffs["removed"], {})
        self.assertEqual(diffs["unchanged"], original_env)
        self.assertEqual(os.getenv("PATH"), path)
        self.assertEqual(os.getenv("PYTHONPATH"), python_path)

    def test_init_dev(self):
        """Tests init with dev stack."""
        envpath = os.path.join(os.path.dirname(__file__), "..", "env")
        os.environ["ENVPATH"] = envpath
        os.environ["HELLO"] = "goodbye"
        os.environ["LOG_LEVEL"] = "DEBUG"
        os.environ["ROOT"] = "/var/tmp"  # cannot override ROOT
        os.environ["ENV"] = "foobar"  # cannot override ENV
        original_env = os.environ.copy()
        sys_path = sys.path.copy()

        envstack.init("dev")
        self.assertEqual(os.getenv("ENV"), "dev")
        self.assertEqual(os.getenv("STACK"), "dev")
        self.assertEqual(os.getenv("HELLO"), "goodbye")
        self.assertEqual(os.getenv("LOG_LEVEL"), "DEBUG")
        self.assertEqual(os.getenv("ROOT"), "/mnt/pipe")
        self.assertEqual(os.getenv("DEPLOY_ROOT"), "/mnt/pipe/dev")
        self.assertTrue(len(sys.path) > len(sys_path))

        envstack.revert()
        diffs = dict_diff(original_env, os.environ)
        self.assertEqual(diffs["added"], {})
        self.assertEqual(diffs["changed"], {})
        self.assertEqual(diffs["removed"], {})
        self.assertEqual(diffs["unchanged"], original_env)

    def test_init_zzz_custom(self):
        """Tests init with custom test stack."""
        envpath = os.path.join(os.path.dirname(__file__), "..", "env")
        os.environ["ENVPATH"] = envpath
        os.environ["HELLO"] = "goodbye"
        os.environ["ENV"] = "foobar"  # cannot override ENV
        original_env = os.environ.copy()
        sys_path = sys.path.copy()

        envstack.init("test", "custom", ignore_missing=True)
        self.assertEqual(os.getenv("ENV"), "custom")
        self.assertEqual(os.getenv("STACK"), "custom")
        self.assertEqual(os.getenv("DEPLOY_ROOT"), "/mnt/pipe/custom")
        self.assertTrue(len(sys.path) > len(sys_path))

        envstack.revert()
        diffs = dict_diff(original_env, os.environ)
        self.assertEqual(diffs["added"], {})
        self.assertEqual(diffs["changed"], {})
        self.assertEqual(diffs["removed"], {})
        self.assertEqual(diffs["unchanged"], original_env)


class TestIssues(unittest.TestCase):
    def setUp(self):
        self.root = create_test_root()
        os.environ["ENVPATH"] = os.path.join(self.root, "prod", "env")
        os.environ["INTERACTIVE"] = "0"

    def tearDown(self):
        envstack.revert()
        shutil.rmtree(self.root)

    def test_issue_30_init(self):
        """Tests issue #30 with envstack.init()."""

        # update default.env to point to test root
        default_env_file = os.path.join(self.root, "prod", "env", "default.env")
        update_env_file(default_env_file, "ROOT", self.root)

        # update the dev hello.env to modify the PYEXE
        hello_env_file = os.path.join(self.root, "dev", "env", "hello.env")
        update_env_file(hello_env_file, "PYEXE", "/usr/bin/foobar")

        # set the ENVPATH to the test root
        os.environ["ENVPATH"] = os.path.join(self.root, "prod", "env")

        # prod stack should have default value
        envstack.init("hello")
        self.assertEqual(os.getenv("ROOT"), self.root)
        self.assertEqual(os.getenv("PYEXE"), "/usr/bin/python")
        envstack.revert()

        # dev stack should have custom value
        envstack.init("dev", "hello")
        self.assertEqual(os.getenv("ROOT"), self.root)
        self.assertEqual(os.getenv("PYEXE"), "/usr/bin/foobar")
        envstack.revert()

    def test_issue_30_sources_default(self):
        """Tests issue #30 with load_environ and checking default sources."""
        from envstack.env import load_environ

        # load hello stack
        env = load_environ("hello")
        paths = [str(source.path) for source in env.sources]

        expected_paths = [
            os.path.join(self.root, "prod", "env", "default.env"),
            os.path.join(self.root, "prod", "env", "hello.env"),
        ]
        self.assertEqual(paths, expected_paths)

    def test_issue_30_sources_dev(self):
        """Tests issue #30 with load_environ and checking dev sources."""
        from envstack.env import load_environ

        # update default.env to point to test root
        default_env_file = os.path.join(self.root, "prod", "env", "default.env")
        update_env_file(default_env_file, "ROOT", self.root)

        # load dev and hello stacks
        env = load_environ(["dev", "hello"])
        paths = [str(source.path) for source in env.sources]

        expected_paths = [
            os.path.join(self.root, "prod", "env", "default.env"),
            os.path.join(self.root, "prod", "env", "dev.env"),
            os.path.join(self.root, "prod", "env", "hello.env"),
            os.path.join(self.root, "dev", "env", "hello.env"),
        ]
        self.assertEqual(paths, expected_paths)


if __name__ == "__main__":
    unittest.main()
