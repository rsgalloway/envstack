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
from envstack.encrypt import AESGCMEncryptor, FernetEncryptor
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
    def setUp(self):
        self.root = {
            "linux": "/mnt/pipe",
            "win32": "X:/pipe",
            "darwin": "/Volumes/pipe",
        }.get(sys.platform)

    def tearDown(self):
        envstack.revert()

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
        self.assertEqual(os.getenv("ENV"), "prod")
        self.assertEqual(os.getenv("STACK"), "default")
        self.assertEqual(os.getenv("HELLO"), "world")
        self.assertEqual(os.getenv("ROOT"), self.root)
        self.assertEqual(os.getenv("DEPLOY_ROOT"), f"{self.root}/prod")
        self.assertTrue(len(sys.path) > len(sys_path))
        self.assertTrue(len(os.getenv("PATH")) > len(path))
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
        self.assertEqual(os.getenv("ROOT"), self.root)
        self.assertEqual(os.getenv("DEPLOY_ROOT"), f"{self.root}/dev")
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
        self.assertEqual(os.getenv("DEPLOY_ROOT"), f"{self.root}/custom")
        self.assertTrue(len(sys.path) > len(sys_path))

        envstack.revert()
        diffs = dict_diff(original_env, os.environ)
        self.assertEqual(diffs["added"], {})
        self.assertEqual(diffs["changed"], {})
        self.assertEqual(diffs["removed"], {})
        self.assertEqual(diffs["unchanged"], original_env)


class TestBakeEnviron(unittest.TestCase):
    def setUp(self):
        self.root = create_test_root()
        self.envpath = os.path.join(self.root, "prod", "env")
        os.environ["ENVPATH"] = self.envpath
        os.environ["INTERACTIVE"] = "0"

    def tearDown(self):
        envstack.revert()
        shutil.rmtree(self.root)

    def bake_environ(self, stack_name):
        """Bakes a given stack and compares values."""
        from envstack.env import bake_environ, load_environ

        default = load_environ(stack_name)
        envstack.revert()  # FIXME: revert should not be required
        baked = bake_environ(stack_name)

        # make sure environment sources are different
        self.assertNotEqual(default.sources, baked.sources)
        self.assertTrue(len(default) > 0)
        self.assertTrue(len(baked) > 0)

        for key, value in default.items():
            if key == "STACK":  # skip the stack name
                continue
            self.assertEqual(baked[key], value)

        # bake to a file, reload and compare
        envstack.revert()  # FIXME: revert should not be required
        baked_file = os.path.join(self.envpath, "baked.env")
        baked2 = bake_environ(stack_name, filename=baked_file)
        self.assertTrue(os.path.exists(baked_file))

        envstack.revert()  # FIXME: revert should not be required
        baked2_reloaded = load_environ("baked")
        self.assertNotEqual(baked2.sources, baked2_reloaded.sources)
        self.assertTrue(len(baked2) > 0)
        self.assertTrue(len(baked2_reloaded) > 0)

        for key, value in baked.items():
            if key == "STACK":
                continue
            self.assertEqual(baked2_reloaded[key], value)

        if os.path.exists(baked_file):
            os.unlink(baked_file)

    def test_bake_default(self):
        """Tests baking the default environment."""
        self.bake_environ("default")

    def test_bake_dev(self):
        """Tests baking the dev environment."""
        self.bake_environ("dev")

    def test_bake_thing(self):
        """Tests baking the thing environment."""
        self.bake_environ("thing")

    def test_bake_dev_thing(self):
        """Tests baking the multiple environments."""
        self.bake_environ(["dev", "thing"])


class TestEncryptEnviron(unittest.TestCase):
    def setUp(self):
        self.root = create_test_root()
        self.envpath = os.path.join(self.root, "prod", "env")
        os.environ["ENVPATH"] = self.envpath
        os.environ["INTERACTIVE"] = "0"
        # remove so we use base64 encoding by default
        if AESGCMEncryptor.KEY_VAR_NAME in os.environ:
            del os.environ[AESGCMEncryptor.KEY_VAR_NAME]
        if FernetEncryptor.KEY_VAR_NAME in os.environ:
            del os.environ[FernetEncryptor.KEY_VAR_NAME]

    def tearDown(self):
        envstack.revert()
        if self.root and os.path.exists(self.root):
            shutil.rmtree(self.root)

    def encrypt_environ(self, stack_name):
        """Tests load_environ with encryption (Base64 only)."""
        from envstack.env import load_environ, encrypt_environ
        from envstack.node import EncryptedNode

        env = load_environ(stack_name)
        encrypted = encrypt_environ(env)

        # make sure environment sources are not empty
        self.assertTrue(len(env) > 0)
        self.assertTrue(len(encrypted) > 0)

        for key, value in env.items():
            if key == "STACK":  # skip the stack name
                continue
            encrypted_value = encrypted[key]
            resolved_encrypted_value = encrypted_value.resolve(env=env)
            self.assertTrue(isinstance(encrypted_value, EncryptedNode))
            self.assertNotEqual(encrypted_value, value)
            self.assertEqual(resolved_encrypted_value, value)

    def load_encrypted_environ(self, stack_name):
        """Tests load_environ with encryption."""
        from envstack.env import load_environ

        default = load_environ(stack_name, encrypt=False)
        envstack.revert()  # FIXME: revert should not be required
        encrypted = load_environ(stack_name, encrypt=True)

        # make sure environment sources are not empty
        self.assertTrue(len(default) > 0)
        self.assertTrue(len(encrypted) > 0)

        for key, value in default.items():
            if key == "STACK":  # skip the stack name
                continue
            encrypted_value = encrypted[key]
            resolved_value = encrypted_value.resolve()
            self.assertNotEqual(encrypted_value, resolved_value)
            self.assertNotEqual(encrypted_value, value)
            self.assertEqual(resolved_value, value)

    # TODO: bake to a file, reload and compare
    def bake_encrypted_environ(self, stack_name):
        """Tests bake_environ with encryption."""
        from envstack.env import bake_environ, load_environ
        from envstack.node import EncryptedNode

        default = load_environ(stack_name)
        envstack.revert()  # FIXME: revert should not be required
        encrypted = bake_environ(stack_name, encrypt=True)

        # make sure environment sources are different and not empty
        self.assertNotEqual(default.sources, encrypted.sources)
        self.assertTrue(len(default) > 0)
        self.assertTrue(len(encrypted) > 0)

        for key, value in default.items():
            if key == "STACK":  # skip the stack name
                continue
            encrypted_value = encrypted[key]
            self.assertTrue(isinstance(encrypted_value, EncryptedNode))
            self.assertEqual(encrypted_value.original_value, None)
            # self.assertNotEqual(encrypted_value.original_value, value)  # from_yaml only
            self.assertEqual(encrypted_value.value, value)
            # the 'encrypted' env may contain encryption keys
            self.assertEqual(encrypted_value.resolve(env=encrypted), value)

    def resolve_encrypted_environ(self, stack_name):
        """Tests resolve_environ with encrypted environ."""
        from envstack.env import encrypt_environ, load_environ, resolve_environ
        from envstack.encrypt import AESGCMEncryptor, FernetEncryptor

        env = load_environ(stack_name)  # unresolved values
        resolved = resolve_environ(env)  # resolved values
        encrypted = encrypt_environ(env)  # encrypted values
        encrypted_resolved = resolve_environ(encrypted)  # resolved encrypted values

        # make sure environments are not empty
        self.assertTrue(len(encrypted) > 0)
        self.assertTrue(len(resolved) > 0)

        # make sure keys are not accidentally left in resolved environments
        for key_name in [AESGCMEncryptor.KEY_VAR_NAME, FernetEncryptor.KEY_VAR_NAME]:
            for _env in (env, resolved, encrypted, encrypted_resolved):
                self.assertTrue(key_name not in _env)

        for key, value in env.items():
            if key == "STACK":  # skip the stack name
                continue
            encrypted_value = encrypted[key]  # encrypted value
            resolved_value = resolved[key]  # resolved value
            encrypted_resolved_value = encrypted_resolved[
                key
            ]  # resolved encrypted value
            self.assertNotEqual(encrypted_value, None)
            self.assertNotEqual(resolved_value, None)
            self.assertNotEqual(encrypted_resolved_value, None)
            self.assertNotEqual(encrypted_value, value)
            self.assertNotEqual(encrypted_value, resolved_value)
            self.assertEqual(resolved_value, encrypted_resolved_value)

    def run_tests(self, stack_name):
        """Runs all tests for a given stack."""
        self.encrypt_environ(stack_name)
        self.load_encrypted_environ(stack_name)
        self.bake_encrypted_environ(stack_name)
        self.resolve_encrypted_environ(stack_name)

        # add encryption key to environment and test again
        if AESGCMEncryptor.KEY_VAR_NAME not in os.environ:
            key = AESGCMEncryptor.generate_key()
            os.environ[AESGCMEncryptor.KEY_VAR_NAME] = key

        self.load_encrypted_environ(stack_name)
        self.bake_encrypted_environ(stack_name)
        self.resolve_encrypted_environ(stack_name)

    def test_default(self):
        """Tests encrypting the default environment."""
        self.run_tests("default")

    def test_dev(self):
        """Tests encrypting the dev environment."""
        self.run_tests("dev")

    def test_thing(self):
        """Tests encrypting the thing environment."""
        self.run_tests("thing")


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

    def test_issue_36(self):
        """Tests issue #36 with init and yaml import."""
        envpath = os.path.join(os.path.dirname(__file__), "..", "env")
        os.environ["ENVPATH"] = envpath

        # clear sys path to simulate no yaml module
        sys.path = []

        # init the dev environment
        try:
            envstack.init("dev")
            import yaml

            success = yaml is not None
        except ImportError:
            success = False

        self.assertTrue(success)
        self.assertTrue("yaml" in sys.modules)
        self.assertTrue(len(sys.path) > 0)


if __name__ == "__main__":
    unittest.main()
