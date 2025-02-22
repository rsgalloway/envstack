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
Contains unit tests for running commands.
"""

import os
import shutil
import subprocess
import sys
import unittest

import envstack
from envstack.encrypt import AESGCMEncryptor, FernetEncryptor

from test_env import create_test_root, update_env_file


class TestUnresolved(unittest.TestCase):
    """Tests unresolved environment variables from the cli."""

    def setUp(self):
        self.envstack_bin = os.path.join(
            os.path.dirname(__file__), "..", "bin", "envstack"
        )
        envpath = os.path.join(os.path.dirname(__file__), "..", "env")
        self.root = {
            "linux": "/mnt/pipe",
            "win32": "X:/pipe",
            "darwin": "/Volumes/pipe",
        }.get(sys.platform)
        os.environ["ENVPATH"] = envpath
        os.environ["INTERACTIVE"] = "0"

    def test_default(self):
        expected_output = (
            """DEPLOY_ROOT=${ROOT}/${ENV}
ENV=prod
ENVPATH=${DEPLOY_ROOT}/env:${ENVPATH}
HELLO=${HELLO:=world}
LOG_LEVEL=${LOG_LEVEL:=INFO}
PATH=${DEPLOY_ROOT}/bin:${PATH}
PYTHONPATH=${DEPLOY_ROOT}/lib/python:${PYTHONPATH}
ROOT=%s
STACK=default
"""
            % self.root
        )
        command = self.envstack_bin
        output = subprocess.check_output(command, shell=True, universal_newlines=True)
        self.assertEqual(output, expected_output)

    def test_dev(self):
        expected_output = (
            """DEPLOY_ROOT=${ROOT}/dev
ENV=dev
ENVPATH=${ROOT}/dev/env:${ROOT}/prod/env:${ENVPATH}
HELLO=${HELLO:=world}
LOG_LEVEL=DEBUG
PATH=${ROOT}/dev/bin:${ROOT}/prod/bin:${PATH}
PYTHONPATH=${ROOT}/dev/lib/python:${ROOT}/prod/lib/python:${PYTHONPATH}
ROOT=%s
STACK=dev
"""
            % self.root
        )
        command = "%s dev" % self.envstack_bin
        output = subprocess.check_output(command, shell=True, universal_newlines=True)
        self.assertEqual(output, expected_output)

    def test_distman(self):
        expected_output = (
            """DEPLOY_ROOT=${ROOT}/${ENV}
ENV=${ENV:=prod}
ENVPATH=${DEPLOY_ROOT}/env:${ENVPATH}
HELLO=${HELLO:=world}
LOG_LEVEL=INFO
PATH=${DEPLOY_ROOT}/bin:${PATH}
PYTHONPATH=${DEPLOY_ROOT}/lib/python:${PYTHONPATH}
ROOT=%s
STACK=distman
"""
            % self.root
        )
        command = "%s distman" % self.envstack_bin
        output = subprocess.check_output(command, shell=True, universal_newlines=True)
        self.assertEqual(output, expected_output)

    def test_hello(self):
        expected_output = (
            """DEPLOY_ROOT=${ROOT}/${ENV}
ENV=prod
ENVPATH=${DEPLOY_ROOT}/env:${ENVPATH}
HELLO=${HELLO:=world}
LOG_LEVEL=${LOG_LEVEL:=INFO}
PATH=${DEPLOY_ROOT}/bin:${PATH}
PYEXE=/usr/bin/python
PYTHONPATH=${DEPLOY_ROOT}/lib/python:${PYTHONPATH}
ROOT=%s
STACK=hello
"""
            % self.root
        )
        command = "%s hello" % self.envstack_bin
        output = subprocess.check_output(command, shell=True, universal_newlines=True)
        self.assertEqual(output, expected_output)

    def test_thing(self):
        expected_output = """CHAR_LIST=['a', 'b', 'c', '${HELLO}']
DEPLOY_ROOT=${ROOT}/${ENV}
DICT={'a': 1, 'b': 2, 'c': '${INT}'}
ENV=prod
ENVPATH=${DEPLOY_ROOT}/env:${ENVPATH}
FLOAT=1.0
HELLO=goodbye
INT=5
LOG_LEVEL=${LOG_LEVEL:=INFO}
NUMBER_LIST=[1, 2, 3]
PATH=${DEPLOY_ROOT}/bin:${PATH}
PYTHONPATH=${DEPLOY_ROOT}/lib/python:${PYTHONPATH}
ROOT=${HOME}/.local/pipe
STACK=thing
"""
        command = "%s thing" % self.envstack_bin
        output = subprocess.check_output(command, shell=True, universal_newlines=True)
        self.assertEqual(output, expected_output)


class TestEncrypt(unittest.TestCase):
    """Tests encrypting environment variables from the cli."""

    def setUp(self):
        self.envstack_bin = os.path.join(
            os.path.dirname(__file__), "..", "bin", "envstack"
        )
        envpath = os.path.join(os.path.dirname(__file__), "..", "env")
        self.root = {
            "linux": "/mnt/pipe",
            "win32": "X:/pipe",
            "darwin": "/Volumes/pipe",
        }.get(sys.platform)
        os.environ["ENVPATH"] = envpath
        os.environ["INTERACTIVE"] = "0"
        os.environ["ROOT"] = "/var/tmp/pipe"  # ROOT cannot be overridden
        # remove so we use base64 encoding by default
        if AESGCMEncryptor.KEY_VAR_NAME in os.environ:
            del os.environ[AESGCMEncryptor.KEY_VAR_NAME]
        if FernetEncryptor.KEY_VAR_NAME in os.environ:
            del os.environ[FernetEncryptor.KEY_VAR_NAME]

    def tearDown(self):
        envstack.revert()

    def test_default(self):
        expected_output = """DEPLOY_ROOT=JHtST09UfS8ke0VOVn0=
ENV=cHJvZA==
ENVPATH=JHtERVBMT1lfUk9PVH0vZW52OiR7RU5WUEFUSH0=
HELLO=JHtIRUxMTzo9d29ybGR9
LOG_LEVEL=JHtMT0dfTEVWRUw6PUlORk99
PATH=JHtERVBMT1lfUk9PVH0vYmluOiR7UEFUSH0=
PYTHONPATH=JHtERVBMT1lfUk9PVH0vbGliL3B5dGhvbjoke1BZVEhPTlBBVEh9
ROOT=L21udC9waXBl
STACK=ZGVmYXVsdA==
"""
        command = "%s --encrypt" % self.envstack_bin
        output = subprocess.check_output(command, shell=True, universal_newlines=True)
        self.assertEqual(output, expected_output)

    def test_default_AESGCM(self):
        """Test that the AESGCM encryption works, and resolves vars since the
        encrypted values change every time."""
        os.environ[AESGCMEncryptor.KEY_VAR_NAME] = AESGCMEncryptor.generate_key()
        expected_output = f"""DEPLOY_ROOT={self.root}/prod
ENV=prod
ROOT={self.root}
"""
        command = "%s --encrypt -r ENV ROOT DEPLOY_ROOT" % self.envstack_bin
        output = subprocess.check_output(
            command, shell=True, env=os.environ, universal_newlines=True
        )
        self.assertEqual(output, expected_output)

    def test_default_resolve(self):
        expected_output = f"""DEPLOY_ROOT={self.root}/prod
ENV=prod
ROOT={self.root}
"""
        command = "%s --encrypt -r ENV ROOT DEPLOY_ROOT" % self.envstack_bin
        output = subprocess.check_output(command, shell=True, universal_newlines=True)
        self.assertEqual(output, expected_output)

    def test_default_command_echo(self):
        expected_output = f"""{self.root}/prod
"""
        command = "%s --encrypt -- echo {DEPLOY_ROOT}" % self.envstack_bin
        output = subprocess.check_output(command, shell=True, universal_newlines=True)
        self.assertEqual(output, expected_output)

    def test_dev(self):
        expected_output = """DEPLOY_ROOT=JHtST09UfS9kZXY=
ENV=ZGV2
ENVPATH=JHtST09UfS9kZXYvZW52OiR7Uk9PVH0vcHJvZC9lbnY6JHtFTlZQQVRIfQ==
HELLO=JHtIRUxMTzo9d29ybGR9
LOG_LEVEL=REVCVUc=
PATH=JHtST09UfS9kZXYvYmluOiR7Uk9PVH0vcHJvZC9iaW46JHtQQVRIfQ==
PYTHONPATH=JHtST09UfS9kZXYvbGliL3B5dGhvbjoke1JPT1R9L3Byb2QvbGliL3B5dGhvbjoke1BZVEhPTlBBVEh9
ROOT=L21udC9waXBl
STACK=ZGV2
"""
        command = "%s dev --encrypt" % self.envstack_bin
        output = subprocess.check_output(command, shell=True, universal_newlines=True)
        self.assertEqual(output, expected_output)

    def test_dev_resolve(self):
        expected_output = f"""DEPLOY_ROOT={self.root}/dev
ENV=dev
ROOT={self.root}
"""
        command = "%s dev --encrypt -r ENV ROOT DEPLOY_ROOT" % self.envstack_bin
        output = subprocess.check_output(command, shell=True, universal_newlines=True)
        self.assertEqual(output, expected_output)

    def test_dev_command_echo(self):
        expected_output = f"""{self.root}/dev
"""
        command = "%s dev --encrypt -- echo {DEPLOY_ROOT}" % self.envstack_bin
        output = subprocess.check_output(command, shell=True, universal_newlines=True)
        self.assertEqual(output, expected_output)


class TestResolved(unittest.TestCase):
    """Tests resolved environment variables."""

    def setUp(self):
        self.envstack_bin = os.path.join(
            os.path.dirname(__file__), "..", "bin", "envstack"
        )
        envpath = os.path.join(os.path.dirname(__file__), "..", "env")
        self.root = {
            "linux": "/mnt/pipe",
            "win32": "X:/pipe",
            "darwin": "/Volumes/pipe",
        }.get(sys.platform)
        os.environ["ENVPATH"] = envpath
        os.environ["INTERACTIVE"] = "0"
        os.environ["ROOT"] = "/var/tmp/pipe"  # ROOT cannot be overridden

    def test_default(self):
        expected_output = f"""DEPLOY_ROOT={self.root}/prod
HELLO=world
ROOT={self.root}
STACK=default
"""
        command = "%s -r DEPLOY_ROOT HELLO ROOT STACK" % self.envstack_bin
        output = subprocess.check_output(command, shell=True, universal_newlines=True)
        self.assertEqual(output, expected_output)

    def test_dev(self):
        expected_output = f"""DEPLOY_ROOT={self.root}/dev
HELLO=world
ROOT={self.root}
STACK=dev
"""
        command = "%s dev -r DEPLOY_ROOT HELLO ROOT STACK" % self.envstack_bin
        output = subprocess.check_output(command, shell=True, universal_newlines=True)
        self.assertEqual(output, expected_output)

    def test_distman(self):
        expected_output = f"""DEPLOY_ROOT={self.root}/prod
ROOT={self.root}
STACK=distman
"""
        command = "%s distman -r DEPLOY_ROOT ROOT STACK" % self.envstack_bin
        output = subprocess.check_output(command, shell=True, universal_newlines=True)
        self.assertEqual(output, expected_output)

    def test_dev_distman(self):
        expected_output = f"""DEPLOY_ROOT={self.root}/dev
ROOT={self.root}
STACK=distman
"""
        command = "%s dev distman -r DEPLOY_ROOT ROOT STACK" % self.envstack_bin
        output = subprocess.check_output(command, shell=True, universal_newlines=True)
        self.assertEqual(output, expected_output)

    def test_test(self):
        expected_output = f"""DEPLOY_ROOT={self.root}/test
HELLO=world
ROOT={self.root}
STACK=test
"""
        command = (
            "ENV=blah ROOT=/var/tmp %s test -r DEPLOY_ROOT HELLO ROOT STACK"
            % self.envstack_bin
        )
        output = subprocess.check_output(command, shell=True, universal_newlines=True)
        self.assertEqual(output, expected_output)

    def test_foobar(self):
        expected_output = f"""DEPLOY_ROOT={self.root}/foobar
HELLO=world
ROOT={self.root}
STACK=foobar
"""
        command = (
            "ENV=blah ROOT=/var/tmp %s test foobar -r DEPLOY_ROOT HELLO ROOT STACK"
            % self.envstack_bin
        )
        output = subprocess.check_output(command, shell=True, universal_newlines=True)
        self.assertEqual(output, expected_output)

    def test_thing(self):
        home = os.getenv("HOME")
        deploy_root = f"{home}/.local/pipe/prod"  # linux only for now
        expected_output = f"""CHAR_LIST=['a', 'b', 'c', 'goodbye']
DEPLOY_ROOT={deploy_root}
HELLO=goodbye
"""
        command = "%s thing -r DEPLOY_ROOT HELLO CHAR_LIST" % self.envstack_bin
        output = subprocess.check_output(command, shell=True, universal_newlines=True)
        self.assertEqual(output, expected_output)


class TestCommands(unittest.TestCase):
    """Tests various envstack commands."""

    def setUp(self):
        self.envstack_bin = os.path.join(
            os.path.dirname(__file__), "..", "bin", "envstack"
        )
        envpath = os.path.join(os.path.dirname(__file__), "..", "env")
        self.root = {
            "linux": "/mnt/pipe",
            "win32": "X:/pipe",
            "darwin": "/Volumes/pipe",
        }.get(sys.platform)
        os.environ["ENVPATH"] = envpath
        os.environ["INTERACTIVE"] = "0"

    def test_default_echo(self):
        command = "%s -- echo {HELLO}" % self.envstack_bin
        expected_output = "world\n"
        output = subprocess.check_output(
            command,
            shell=True,
            universal_newlines=True,
        )
        self.assertEqual(output, expected_output)

    def test_default_ls(self):
        command = "%s -- ls" % self.envstack_bin
        expected_output = subprocess.check_output(
            "ls", start_new_session=True, shell=True, universal_newlines=True
        )
        output = subprocess.check_output(command, shell=True, universal_newlines=True)
        self.assertEqual(output, expected_output)

    def test_thing_echo(self):
        command = "%s thing -- echo {HELLO}" % self.envstack_bin
        expected_output = "goodbye\n"
        output = subprocess.check_output(
            command, start_new_session=True, shell=True, universal_newlines=True
        )
        self.assertEqual(output, expected_output)

    def test_test_echo_deploy_root(self):
        command = "%s test -- echo {DEPLOY_ROOT}" % self.envstack_bin
        expected_output = f"{self.root}/test\n"
        output = subprocess.check_output(
            command, start_new_session=True, shell=True, universal_newlines=True
        )
        self.assertEqual(output, expected_output)

    def test_test_echo_deploy_root(self):
        command = "%s test foobar -- echo {DEPLOY_ROOT}" % self.envstack_bin
        expected_output = f"{self.root}/foobar\n"
        output = subprocess.check_output(
            command, start_new_session=True, shell=True, universal_newlines=True
        )
        self.assertEqual(output, expected_output)


class TestVarFlow(unittest.TestCase):
    """Tests the flow of environment variables through stacks."""

    def setUp(self):
        self.envstack_bin = os.path.join(
            os.path.dirname(__file__), "..", "bin", "envstack"
        )
        envpath = os.path.join(os.path.dirname(__file__), "..", "env")
        os.environ["ENVPATH"] = envpath
        os.environ["INTERACTIVE"] = "0"

    def test_default_hello(self):
        command = "%s -- echo {HELLO}" % self.envstack_bin
        expected_output = "world\n"
        output = subprocess.check_output(
            command, start_new_session=True, shell=True, universal_newlines=True
        )
        self.assertEqual(output, expected_output)

    def test_dev_hello(self):
        command = "%s dev -- echo {HELLO}" % self.envstack_bin
        expected_output = "world\n"
        output = subprocess.check_output(
            command, start_new_session=True, shell=True, universal_newlines=True
        )
        self.assertEqual(output, expected_output)

    def test_thing_hello(self):
        command = "%s thing -- echo {HELLO}" % self.envstack_bin
        expected_output = "goodbye\n"
        output = subprocess.check_output(
            command, start_new_session=True, shell=True, universal_newlines=True
        )
        self.assertEqual(output, expected_output)

    def test_thing_hello_multiple(self):
        command = "%s default dev thing -- echo {HELLO}" % self.envstack_bin
        expected_output = "goodbye\n"
        output = subprocess.check_output(
            command, start_new_session=True, shell=True, universal_newlines=True
        )
        self.assertEqual(output, expected_output)


class TestDistman(unittest.TestCase):
    """Tests value for $DEPLOY_ROOT under various environment configurations."""

    def setUp(self):
        self.envstack_bin = os.path.join(
            os.path.dirname(__file__), "..", "bin", "envstack"
        )
        self.python_cmd = """python -c \"import os,envstack;envstack.init('distman');print(os.getenv('DEPLOY_ROOT'))\""""
        envpath = os.path.join(os.path.dirname(__file__), "..", "env")
        self.root = {
            "linux": "/mnt/pipe",
            "win32": "X:/pipe",
            "darwin": "/Volumes/pipe",
        }.get(sys.platform)
        os.environ["ENVPATH"] = envpath
        os.environ["INTERACTIVE"] = "0"

    def test_default_deploy_root(self):
        os.environ["ENV"] = "invalid"  # should not be able to override ENV
        command = "%s -- %s" % (self.envstack_bin, self.python_cmd)
        expected_output = f"{self.root}/prod\n"
        output = subprocess.check_output(
            command, start_new_session=True, shell=True, universal_newlines=True
        )
        self.assertEqual(output, expected_output)

    def test_dev_deploy_root(self):
        os.environ["ENV"] = "invalid"  # should not be able to override ENV
        command = "%s dev -- %s" % (self.envstack_bin, self.python_cmd)
        expected_output = f"{self.root}/dev\n"
        output = subprocess.check_output(
            command, start_new_session=True, shell=True, universal_newlines=True
        )
        self.assertEqual(output, expected_output)

    def test_test_deploy_root(self):
        command = "ENV=invalid %s test -- %s" % (self.envstack_bin, self.python_cmd)
        expected_output = f"{self.root}/test\n"
        output = subprocess.check_output(
            command, start_new_session=True, shell=True, universal_newlines=True
        )
        self.assertEqual(output, expected_output)

    def test_foobar_deploy_root(self):
        command = "ENV=invalid %s test foobar -- %s" % (
            self.envstack_bin,
            self.python_cmd,
        )
        expected_output = f"{self.root}/foobar\n"
        output = subprocess.check_output(
            command, start_new_session=True, shell=True, universal_newlines=True
        )
        self.assertEqual(output, expected_output)


class TestIssues(unittest.TestCase):
    def setUp(self):
        self.root = create_test_root()
        self.envstack_bin = os.path.join(
            os.path.dirname(__file__), "..", "bin", "envstack"
        )
        os.environ["ENVPATH"] = os.path.join(self.root, "prod", "env")
        os.environ["INTERACTIVE"] = "0"

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_issue_30_echo(self):
        """Test that the correct value of PYEXE is used."""

        # update default.env to point to test root
        default_env_file = os.path.join(self.root, "prod", "env", "default.env")
        update_env_file(default_env_file, "ROOT", self.root)

        # update the dev hello.env to modify the PYEXE
        hello_env_file = os.path.join(self.root, "dev", "env", "hello.env")
        update_env_file(hello_env_file, "PYEXE", "/usr/bin/foobar")

        # test "default" should have values from prod only
        command = "%s hello -- echo {PYEXE}" % self.envstack_bin
        expected_output = "/usr/bin/python\n"
        output = subprocess.check_output(
            command, start_new_session=True, shell=True, universal_newlines=True
        )
        self.assertEqual(output, expected_output)

        # test "dev" should have values from dev and prod
        command = "%s dev hello -- echo {PYEXE}" % self.envstack_bin
        expected_output = "/usr/bin/foobar\n"
        output = subprocess.check_output(
            command, start_new_session=True, shell=True, universal_newlines=True
        )
        self.assertEqual(output, expected_output)

    # TODO: add test with dev env file that includes other dev env files
    def test_issue_30_sources(self):
        """Test that the correct sources are used."""

        # update default.env to point to test root
        default_env_file = os.path.join(self.root, "prod", "env", "default.env")
        update_env_file(default_env_file, "ROOT", self.root)

        # update the dev hello.env to modify the PYEXE
        hello_env_file = os.path.join(self.root, "dev", "env", "hello.env")
        update_env_file(hello_env_file, "PYEXE", "/usr/bin/foobar")

        # test "default" should only include prod sources
        command = "%s hello --sources" % self.envstack_bin
        expected_output = f"""{self.root}/prod/env/default.env
{self.root}/prod/env/hello.env
"""
        output = subprocess.check_output(
            command, start_new_session=True, shell=True, universal_newlines=True
        )
        self.assertEqual(output, expected_output)

        # test "dev" should include prod and dev sources
        command = "%s dev hello --sources" % self.envstack_bin
        expected_output = f"""{self.root}/prod/env/default.env
{self.root}/prod/env/dev.env
{self.root}/prod/env/hello.env
{self.root}/dev/env/hello.env
"""
        output = subprocess.check_output(
            command, start_new_session=True, shell=True, universal_newlines=True
        )
        self.assertEqual(output, expected_output)


if __name__ == "__main__":
    unittest.main()
