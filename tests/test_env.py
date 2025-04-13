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
    def setUp(self):
        self.filename = "testenv.env"
        envpath = os.path.join(os.path.dirname(__file__), "..", "env")
        self.root = {
            "linux": "/mnt/pipe",
            "win32": "X:/pipe",
            "darwin": "/Volumes/pipe",
        }.get(sys.platform)
        os.environ["ENVPATH"] = envpath
        # remove so we use base64 encoding by default
        if AESGCMEncryptor.KEY_VAR_NAME in os.environ:
            del os.environ[AESGCMEncryptor.KEY_VAR_NAME]
        if FernetEncryptor.KEY_VAR_NAME in os.environ:
            del os.environ[FernetEncryptor.KEY_VAR_NAME]

    def tearDown(self):
        if os.path.exists(self.filename):
            os.remove(self.filename)

    def test_getitem(self):
        """Tests getting an item from the environment."""
        env = Env({"FOO": "foo", "BAR": "$FOO"})
        self.assertEqual(env["BAR"], "$FOO")

    def test_get(self):
        """Tests getting a value from the environment."""
        env = Env({"FOO": "foo", "BAR": "$FOO"})
        self.assertEqual(env.get("BAR"), "$FOO")
        self.assertEqual(env.get("BAZ"), None)
        self.assertEqual(env.get("BAZ", "default"), "default")

    def test_copy(self):
        """Tests copying an environment."""
        env = Env({"FOO": "foo", "BAR": "$FOO"})
        copied = env.copy()
        self.assertEqual(copied, {"FOO": "foo", "BAR": "$FOO"})

    def test_set_namespace(self):
        """Tests setting the namespace of the environment."""
        env = Env()
        env.set_namespace("test")
        self.assertEqual(env.namespace, "test")

    def test_set_scope(self):
        """Tests setting the scope of the environment."""
        env = Env()
        env.set_scope("/path/to/scope")
        self.assertEqual(env.scope, "/path/to/scope")

    def test_bake(self):
        """Tests baking an environment."""
        from envstack.env import load_environ
        env = load_environ("thing")
        baked = env.bake()
        for k, v in env.items():
            if k == "STACK":
                continue
            self.assertEqual(baked[k], v)

    def test_bake_out(self):
        """Tests bake, write and load an environment."""
        from envstack.env import load_environ
        env1 = load_environ("thing")
        self.filename = "test_bake_out.env"
        env1.write(self.filename)
        env2 = load_environ(self.filename)
        for k, v in env1.items():
            if k == "STACK":
                continue
            self.assertEqual(env2[k], v)

    def test_write_simple(self):
        """Tests writing an environment to a file."""
        from envstack.env import load_environ, resolve_environ
        env1 = Env({"FOO": "foo", "BAR": "${FOO}"})
        self.filename = "test_write_simple.env"
        env1.write(self.filename)
        env2 = load_environ(self.filename)
        env3 = resolve_environ(env2)
        self.assertEqual(env1["FOO"], "foo")
        self.assertEqual(env1["BAR"], "${FOO}")
        self.assertEqual(env2["FOO"], "foo")
        self.assertEqual(env2["BAR"], "${FOO}")
        self.assertEqual(env3["FOO"], "foo")
        self.assertEqual(env3["BAR"], "foo")

    def test_write_custom(self):
        """Tests writing an environment with a custom node to a file."""
        from envstack.env import load_environ, resolve_environ
        from envstack.node import EncryptedNode
        env1 = Env({"FOO": "foo", "BAR": EncryptedNode("bar")})
        self.filename = "test_write_custom.env"
        # write it out and reload it
        env1.write(self.filename)
        env2 = load_environ(self.filename)
        env3 = resolve_environ(env2)
        # write it back out again and reload it (test for double encryption)
        env3.write(self.filename)
        env4 = resolve_environ(load_environ(self.filename))
        self.assertEqual(env1["FOO"], "foo")
        self.assertEqual(env1["BAR"], EncryptedNode("bar"))
        self.assertEqual(env2["FOO"], "foo")
        self.assertEqual(env2["BAR"], EncryptedNode('YmFy'))
        self.assertEqual(EncryptedNode('YmFy').resolve(env=env2), "bar")
        self.assertEqual(env3["FOO"], "foo")
        self.assertEqual(env3["BAR"], "bar")
        self.assertEqual(env4["FOO"], "foo")
        self.assertEqual(env4["BAR"], "bar")


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
        # self.assertTrue(len(os.getenv("PATH")) > len(path))
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


class TestResolveEnviron(unittest.TestCase):
    """Tests the resolve_environ function."""

    def test_home(self):
        """Tests to make sure ${HOME} is resolved."""
        from envstack.env import resolve_environ

        # ${HOME} is undefined on windows
        home = os.getenv("HOME", os.path.expanduser("~"))
        os.environ["HOME"] = home
        env = {"FOO": "${HOME}/foo"}
        resolved = resolve_environ(env)
        self.assertEqual(resolved["FOO"], f"{home}/foo")

    def test_custom(self):
        """Tests to make sure ${CUSTOM} is resolved from os.environ."""
        from envstack.env import resolve_environ

        os.environ["CUSTOM"] = "/var/tmp"
        env = {"FOO": "${CUSTOM}/foo"}
        resolved = resolve_environ(env)
        self.assertEqual(resolved["FOO"], f"/var/tmp/foo")

    def test_simple(self):
        """Tests resolving a simple environment."""
        from envstack.env import resolve_environ

        env = {"FOO": "foo", "BAR": "${FOO}"}
        resolved = resolve_environ(env)
        self.assertEqual(resolved["BAR"], "foo")

    def test_nested(self):
        """Tests resolving a nested environment."""
        from envstack.env import resolve_environ

        env = {"FOO": "foo", "BAR": "${FOO}", "BAZ": "${BAR}"}
        resolved = resolve_environ(env)
        self.assertEqual(resolved["BAZ"], "foo")

    def test_recursive(self):
        """Tests resolving a recursive environment."""
        from envstack.env import resolve_environ

        env = {"FOO": "foo", "BAR": "${FOO}", "BAZ": "${BAR}", "QUX": "${BAZ}"}
        resolved = resolve_environ(env)
        self.assertEqual(resolved["QUX"], "foo")

    def test_recursive_list(self):
        """Tests resolving a recursive list environment."""
        from envstack.env import resolve_environ

        env = {"FOO": "foo", "BAR": "${FOO}", "BAZ": ["${BAR}"]}
        resolved = resolve_environ(env)
        self.assertEqual(resolved["BAZ"], ["foo"])

    def test_recursive_dict(self):
        """Tests resolving a recursive dict environment."""
        from envstack.env import resolve_environ

        env = {"FOO": "foo", "BAR": "${FOO}", "BAZ": {"qux": "${BAR}"}}
        resolved = resolve_environ(env)
        self.assertEqual(resolved["BAZ"], {"qux": "foo"})

    def test_expansion_modifier(self):
        """Tests var with an expansion modifier."""
        from envstack.env import resolve_environ

        env = {"VAR": "${VAR:=/foo/bar}"}
        resolved = resolve_environ(env)
        self.assertEqual(resolved["VAR"], "/foo/bar")

    def test_expansion_modifier_alt(self):
        """Tests var with an expansion modifier using alt modifier."""
        from envstack.env import resolve_environ

        env = {"VAR": "${VAR:-/foo/bar}"}
        resolved = resolve_environ(env)
        self.assertEqual(resolved["VAR"], "/foo/bar")

    def test_expansion_modifier_nested_undefined(self):
        """Tests expansion modifier with no value."""
        from envstack.env import resolve_environ

        env = {"VAR": "${VAR:=${FOO}}"}
        resolved = resolve_environ(env)
        self.assertEqual(resolved["VAR"], "")

    def test_expansion_modifier_nested_default(self):
        """Tests expansion modifier with default value."""
        from envstack.env import resolve_environ

        env = {"VAR": "${VAR:=${FOO:=bar}}"}
        resolved = resolve_environ(env)
        self.assertEqual(resolved["VAR"], "bar")

    def test_expansion_modifier_nested_default_slash(self):
        """Tests expansion modifier with special chars."""
        from envstack.env import resolve_environ

        # remove ENV and ROOT from the environment
        if "FOO" in os.environ:
            del os.environ["FOO"]
        if "VAR" in os.environ:
            del os.environ["VAR"]
        env = {"VAR": "${VAR:=${FOO:=/foo/bar}}"}
        resolved = resolve_environ(env)
        self.assertEqual(resolved["VAR"], "/foo/bar")

    def test_deploy_root_two(self):
        """Tests $DEPLOY_ROOT with two vars."""
        from envstack.env import resolve_environ

        # set ENV and ROOT in the environment
        os.environ["ROOT"] = "/mnt/pipe"
        os.environ["ENV"] = "dev"
        env = {
            "DEPLOY_ROOT": "${ROOT}/${ENV}}",
            "ENV": "${ENV:=prod}",
            "ROOT": "${ROOT:=/var/tmp}",
        }
        resolved = resolve_environ(env)
        self.assertEqual(resolved["DEPLOY_ROOT"], "/mnt/pipe/dev")

    def test_deploy_root_three(self):
        """Tests $DEPLOY_ROOT with three vars."""
        from envstack.env import resolve_environ

        env_value = os.getenv("ENV", "prod")
        env = {
            "DEPLOY_ROOT": "${MOUNT}/${DRIVE}/${ENV}}",
            "ENV": "${ENV:=prod}",
            "MOUNT": "/mnt",
            "DRIVE": "${DRIVE:=pipe}",
        }
        resolved = resolve_environ(env)
        self.assertEqual(resolved["DEPLOY_ROOT"], f"/mnt/pipe/{env_value}")

    def test_deploy_root_default_one(self):
        """Tests $DEPLOY_ROOT with default value and one var."""
        from envstack.env import resolve_environ

        # remove DEPLOY_ROOT, ENV and ROOT from the environment
        if "DEPLOY_ROOT" in os.environ:
            del os.environ["DEPLOY_ROOT"]
        if "ENV" in os.environ:
            del os.environ["ENV"]
        if "ROOT" in os.environ:
            del os.environ["ROOT"]
        env = {
            "DEPLOY_ROOT": "${DEPLOY_ROOT:=${TMP}}",
            "ENV": "${ENV:=prod}",
            "ROOT": "${ROOT:=/var/tmp}",
            "TMP": "${ROOT}/${ENV}",
        }
        resolved = resolve_environ(env)
        self.assertEqual(resolved["DEPLOY_ROOT"], "/var/tmp/prod")

    def test_deploy_root_default_two(self):
        """Tests $DEPLOY_ROOT with default value and two vars."""
        from envstack.env import resolve_environ

        # remove DEPLOY_ROOT, ENV and ROOT from the environment
        if "DEPLOY_ROOT" in os.environ:
            del os.environ["DEPLOY_ROOT"]
        if "ENV" in os.environ:
            del os.environ["ENV"]
        if "ROOT" in os.environ:
            del os.environ["ROOT"]
        env = {
            "DEPLOY_ROOT": "${DEPLOY_ROOT:=${ROOT}/${ENV}}",
            "ENV": "${ENV:=prod}",
            "ROOT": "${ROOT:=/var/lib}",
        }
        resolved = resolve_environ(env)
        self.assertEqual(resolved["DEPLOY_ROOT"], "/var/lib/prod")

    def test_deploy_root_default_two_from_env(self):
        """Tests $DEPLOY_ROOT with default value from env."""
        from envstack.env import resolve_environ

        # remove DEPLOY_ROOT, ENV and ROOT from the environment
        if "ENV" in os.environ:
            del os.environ["ENV"]
        if "ROOT" in os.environ:
            del os.environ["ROOT"]
        os.environ["DEPLOY_ROOT"] = "/some/path/here"
        env = {
            "DEPLOY_ROOT": "${DEPLOY_ROOT:=${ROOT}/${ENV}}",
            "ENV": "${ENV:=prod}",
            "ROOT": "${ROOT:=/var/lib}",
        }
        resolved = resolve_environ(env)
        self.assertEqual(resolved["DEPLOY_ROOT"], "/some/path/here")

    def test_expansion_modifier_deferred(self):
        """Tests expansion modifier with deferred value."""
        from envstack.env import resolve_environ

        env = {
            "VAR": "${VAR:=${FOO}}",
            "FOO": "${FOO:=/foo/bar}",
            "BAR": "${BAZ}",  # has null value
        }
        resolved = resolve_environ(env)
        self.assertEqual(resolved["VAR"], "/foo/bar")
        self.assertEqual(resolved["FOO"], "/foo/bar")
        self.assertEqual(resolved["BAR"], "")

    def test_expansion_modifier_deferred_default(self):
        """Tests expansion modifier with multiple deferred values."""
        from envstack.env import resolve_environ

        env = {
            "VAR": "${VAR:=${FOO}}",
            "FOO": "${FOO:=${BAR}}",
            "BAR": "${BAZ:=/baz/qux}", # has a default value
        }
        resolved = resolve_environ(env)
        self.assertEqual(resolved["VAR"], "/baz/qux")
        self.assertEqual(resolved["FOO"], "/baz/qux")
        self.assertEqual(resolved["BAR"], "/baz/qux")

    def test_expansion_modifier_deferred_null_value(self):
        """Tests expansion modifier with multiple deferred values and null."""
        from envstack.env import resolve_environ

        env = {
            "VAR": "${VAR:=${FOO}}",
            "FOO": "${FOO:=${BAR}}",
            "BAR": "${BAZ:=/baz/qux}",
            "BAZ": "${QUX}",  # has null value
        }
        resolved = resolve_environ(env)
        self.assertEqual(resolved["VAR"], "/baz/qux")
        self.assertEqual(resolved["FOO"], "/baz/qux")
        self.assertEqual(resolved["BAR"], "/baz/qux")
        self.assertEqual(resolved["BAZ"], "")
        self.assertRaises(KeyError, lambda: resolved["QUX"])

    def test_recursive_list_dict(self):
        """Tests resolving a recursive list dict environment."""
        from envstack.env import resolve_environ

        env = {"FOO": "foo", "BAR": "${FOO}", "BAZ": [{"qux": "${BAR}"}]}
        resolved = resolve_environ(env)
        self.assertEqual(resolved["BAZ"], [{"qux": "foo"}])

    def test_recursive_dict_list(self):
        """Tests resolving a recursive dict list environment."""
        from envstack.env import resolve_environ

        env = {"FOO": "foo", "BAR": "${FOO}", "BAZ": {"qux": ["${BAR}"]}}
        resolved = resolve_environ(env)
        self.assertEqual(resolved["BAZ"], {"qux": ["foo"]})

    def test_recursive_list_list(self):
        """Tests resolving a recursive list list environment."""
        from envstack.env import resolve_environ

        env = {"FOO": "foo", "BAR": "${FOO}", "BAZ": [["${BAR}"]]}
        resolved = resolve_environ(env)
        self.assertEqual(resolved["BAZ"], [["foo"]])


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

        env = load_environ(stack_name)
        envstack.revert()  # FIXME: revert should not be required
        baked = bake_environ(stack_name)

        # make sure environment sources are different
        if stack_name == "doesnotexist":
            self.assertEqual(env.sources, [])
            self.assertEqual(len(baked.sources), 1)
        elif stack_name == "default":
            self.assertTrue(len(env.sources[0].includes()) == 0)
        else:
            self.assertNotEqual(env.sources, baked.sources)
            self.assertTrue(len(env.sources) > 0)
            self.assertEqual(len(baked.sources), 1)
            self.assertTrue(len(env) > 0)
            self.assertTrue(len(baked) > 0)

        # "include" key should not be present
        self.assertTrue("include" not in env)
        self.assertTrue("include" not in baked)

        # compare the values
        for key, value in env.items():
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

        # make sure environment sources are different
        if stack_name == "doesnotexist":
            self.assertEqual(env.sources, [])
            self.assertEqual(len(baked.sources), 1)
        else:
            self.assertNotEqual(baked2.sources, baked2_reloaded.sources)
            self.assertTrue(len(baked2) > 0)
            self.assertTrue(len(baked2_reloaded) > 0)

        # "include" key should not be present
        self.assertTrue("include" not in env)
        self.assertTrue("include" not in baked2)

        # compare the values
        for key, value in env.items():
            if key == "STACK":
                continue
            self.assertEqual(baked2_reloaded[key], value)

        if os.path.exists(baked_file):
            os.unlink(baked_file)

    def test_bake_default(self):
        """Tests baking the default environment."""
        self.bake_environ("default")

    def test_bake_empty(self):
        """Tests baking new environment."""
        self.bake_environ("doesnotexist")

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

        # "include" key should not be present
        self.assertTrue("include" not in env)
        self.assertTrue("include" not in encrypted)

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

        # "include" key should not be present
        self.assertTrue("include" not in default)
        self.assertTrue("include" not in encrypted)

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

    def test_encrypt_environ_as_env(self):
        """Tests encrypting an environment as Env."""
        from envstack.env import encrypt_environ
        from envstack.node import EncryptedNode

        env = Env({"HELLO": "world", "FOO": "foo", "BAR": "${FOO}"})
        encrypted = encrypt_environ(env)
        self.assertNotEqual(encrypted["HELLO"], "d29ybGQ=")
        self.assertTrue(isinstance(encrypted["HELLO"], EncryptedNode))
        self.assertEqual(encrypted["HELLO"].resolve(env=env), "world")
        self.assertNotEqual(encrypted["FOO"], env["FOO"])
        self.assertEqual(encrypted["FOO"].resolve(env=env), env["FOO"])
        self.assertNotEqual(encrypted["BAR"], env["BAR"])
        self.assertEqual(encrypted["BAR"].resolve(env=env), env["BAR"])

    def test_encrypt_environ_as_dict(self):
        """Tests encrypting an environment as dict."""
        from envstack.env import encrypt_environ
        from envstack.node import EncryptedNode

        env = {"HELLO": "world", "FOO": "foo", "BAR": "${FOO}"}
        encrypted = encrypt_environ(env)
        self.assertNotEqual(encrypted["HELLO"], "d29ybGQ=")
        self.assertTrue(isinstance(encrypted["HELLO"], EncryptedNode))
        self.assertEqual(encrypted["HELLO"].resolve(env=env), "world")
        self.assertNotEqual(encrypted["FOO"], env["FOO"])
        self.assertEqual(encrypted["FOO"].resolve(env=env), env["FOO"])
        self.assertNotEqual(encrypted["BAR"], env["BAR"])
        self.assertEqual(encrypted["BAR"].resolve(env=env), env["BAR"])


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

    def test_issue_51(self):
        """Tests issue #51 with URL values on all platforms."""
        from envstack.env import load_environ
        env = Env({
            "URL": "https://example.com",
            "S3": "s3://bucket.amazonaws.com",
            "GIT": "git://path/to/repo.git",
        })
        self.filename = os.path.join(self.root, "test_issue_51.env")
        env.write(self.filename)
        self.assertEqual(env["URL"], "https://example.com")
        self.assertEqual(env["S3"], "s3://bucket.amazonaws.com")
        self.assertEqual(env["GIT"], "git://path/to/repo.git")

        for platform in ("linux", "windows", "darwin"):
            env = load_environ(self.filename, platform=platform)
            self.assertEqual(env["URL"], "https://example.com")
            self.assertEqual(env["S3"], "s3://bucket.amazonaws.com")
            self.assertEqual(env["GIT"], "git://path/to/repo.git")

    def test_issue_55(self):
        """Tests issue #55 with missing environment file.
        Tests dynamic ${ENVPATH} values that use ${STACK} in the path,

        env/test.env:
            ENVPATH: ${ROOT}/${STACK}/env:${ROOT}/prod/env

        The STACK name and the test env file name should be the same.
        """
        from envstack.env import load_environ, Env

        # update default.env to point to test root
        default_env_file = os.path.join(self.root, "prod", "env", "default.env")
        dev_env_file = os.path.join(self.root, "prod", "env", "dev.env")
        update_env_file(default_env_file, "ROOT", self.root)

        # create a new test env file that only exists in our test env dir
        test_env = os.path.join(self.root, "test_issue_55", "env")
        os.makedirs(test_env, exist_ok=True)
        test_env_file = os.path.join(test_env, "test_issue_55.env")

        data = {"FOO": "foo", "BAR": "bar", "BAZ": self.root}
        Env(data).write(test_env_file)
        self.assertTrue(os.path.exists(test_env_file))

        # try to load our test env file by loading the "dev" env first, which
        # does not use STACK in ENVPATH
        env1 = load_environ(["dev", "test_issue_55"])

        # last env file should be the "dev" env file
        self.assertEqual(str(env1.sources[-1].path), dev_env_file)
        self.assertRaises(KeyError, lambda: env1["FOO"])
        self.assertRaises(KeyError, lambda: env1["BAR"])
        self.assertRaises(KeyError, lambda: env1["BAZ"])

        # FIXME: why is this necessary? (think it's caching seen stacks)
        envstack.revert()

        # load our test env file by loading the "test" env first, which
        # does use STACK in ENVPATH
        env2 = load_environ(["test", "test_issue_55"])

        # last env file should be our test env file
        self.assertEqual(str(env2.sources[-1].path), test_env_file)
        self.assertEqual(env2["FOO"], "foo")
        self.assertEqual(env2["BAR"], "bar")
        self.assertEqual(env2["BAZ"], self.root)
        self.assertEqual(env2["STACK"], "test_issue_55")

    def test_issue_58(self):
        """Tests issue #58 for inherited environment variables.

        grandparent:
            FOO: grandparent
        parent:
            include: [grandparent]
            FOO: ${FOO:=parent}
        child:
            include: [parent]
            FOO: ${FOO:=child}
        """
        from envstack.env import load_environ, resolve_environ, Source

        # create grandparent.env that sets a value for FOO
        grandparent = {
            "include": [],
            "all": {"FOO": "grandparent"}
        }
        grandparent_env_file = os.path.join(self.root, "prod", "env", "grandparent.env")
        grandparent_source = Source(grandparent_env_file)
        grandparent_source.data = grandparent
        grandparent_source.write()

        # create parent.env that includes grandparent
        parent = {
            "include": ["grandparent"],
            "all": {"FOO": "${FOO:=parent}"}
        }
        parent_env_file = os.path.join(self.root, "prod", "env", "parent.env")
        parent_source = Source(parent_env_file)
        parent_source.data = parent
        parent_source.write()

        # create child.env that includes parent
        child = {
            "include": ["parent"],
            "all": {"FOO": "${FOO:=child}"}
        }
        child_env_file = os.path.join(self.root, "prod", "env", "child.env")
        child_source = Source(child_env_file)
        child_source.data = child
        child_source.write()

        env = load_environ("child")
        resolved = resolve_environ(env)
        self.assertEqual(resolved["FOO"], "grandparent")

        envstack.revert()  # simulate a new process
        envstack.init("child")
        self.assertEqual(os.getenv("FOO"), "grandparent")


if __name__ == "__main__":
    unittest.main()
