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


class TestBake(unittest.TestCase):
    """Tests bake command."""

    def setUp(self):
        self.filename = "baketest.env"
        if os.path.exists(self.filename):
            os.remove(self.filename)
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
        # remove so we use base64 encoding by default
        if AESGCMEncryptor.KEY_VAR_NAME in os.environ:
            del os.environ[AESGCMEncryptor.KEY_VAR_NAME]
        if FernetEncryptor.KEY_VAR_NAME in os.environ:
            del os.environ[FernetEncryptor.KEY_VAR_NAME]

    def tearDown(self):
        if os.path.exists(self.filename):
            os.remove(self.filename)

    def test_default(self):
        """Tests baking the default stack."""
        command = f"%s -o {self.filename}; cat {self.filename}" % self.envstack_bin
        expected_output = """#!/usr/bin/env envstack
include: []
all: &all
  <<: *all
  DEPLOY_ROOT: ${ROOT}/${ENV}
  ENV: prod
  ENVPATH: ${DEPLOY_ROOT}/env:${ENVPATH}
  HELLO: ${HELLO:=world}
  LOG_LEVEL: ${LOG_LEVEL:=INFO}
  PATH: ${DEPLOY_ROOT}/bin:${PATH}
  PYTHONPATH: ${DEPLOY_ROOT}/lib/python:${PYTHONPATH}
darwin:
  <<: *all
  ROOT: /Volumes/pipe
linux:
  <<: *all
  ROOT: /mnt/pipe
windows:
  <<: *all
  ROOT: X:/pipe
"""
        output = subprocess.check_output(
            command,
            shell=True,
            universal_newlines=True,
        )
        self.assertEqual(output, expected_output)

    def test_dev(self):
        """Tests baking the dev stack."""
        command = f"%s dev -o {self.filename}; cat {self.filename}" % self.envstack_bin
        expected_output = """#!/usr/bin/env envstack
include: []
all: &all
  <<: *all
  DEPLOY_ROOT: ${ROOT}/dev
  ENV: dev
  ENVPATH: ${ROOT}/dev/env:${ROOT}/prod/env:${ENVPATH}
  HELLO: ${HELLO:=world}
  LOG_LEVEL: DEBUG
  PATH: ${ROOT}/dev/bin:${ROOT}/prod/bin:${PATH}
  PYTHONPATH: ${ROOT}/dev/lib/python:${ROOT}/prod/lib/python:${PYTHONPATH}
darwin:
  <<: *all
  ROOT: /Volumes/pipe
linux:
  <<: *all
  ROOT: /mnt/pipe
windows:
  <<: *all
  ROOT: X:/pipe
"""
        output = subprocess.check_output(
            command,
            shell=True,
            universal_newlines=True,
        )
        self.assertEqual(output, expected_output)

    def test_thing(self):
        """Tests baking the thing stack with depth of 1."""
        command = (
            f"%s thing -o {self.filename} --depth 1; cat {self.filename}"
            % self.envstack_bin
        )
        expected_output = """#!/usr/bin/env envstack
include: [default]
all: &all
  <<: *all
  CHAR_LIST: [a, b, c, "${HELLO}"]
  DICT: {a: 1, b: 2, c: "${INT}"}
  FLOAT: 1.0
  HELLO: goodbye
  INT: 5
  LOG_LEVEL: ${LOG_LEVEL:=INFO}
  NUMBER_LIST: [1, 2, 3]
darwin:
  <<: *all
  ROOT: ${HOME}/Library/Application Support/pipe
linux:
  <<: *all
  ROOT: ${HOME}/.local/pipe
windows:
  <<: *all
  ROOT: C:/ProgramData/pipe
"""
        output = subprocess.check_output(
            command,
            shell=True,
            universal_newlines=True,
        )
        self.assertEqual(output, expected_output)

    def test_default_encrypted(self):
        """Tests baking the default stack encrypted with base64."""
        command = (
            f"%s --encrypt -o {self.filename}; cat {self.filename}" % self.envstack_bin
        )
        expected_output = """#!/usr/bin/env envstack
include: []
all: &all
  <<: *all
  DEPLOY_ROOT: !encrypt JHtST09UfS8ke0VOVn0=
  ENV: !encrypt cHJvZA==
  ENVPATH: !encrypt JHtERVBMT1lfUk9PVH0vZW52OiR7RU5WUEFUSH0=
  HELLO: !encrypt JHtIRUxMTzo9d29ybGR9
  LOG_LEVEL: !encrypt JHtMT0dfTEVWRUw6PUlORk99
  PATH: !encrypt JHtERVBMT1lfUk9PVH0vYmluOiR7UEFUSH0=
  PYTHONPATH: !encrypt JHtERVBMT1lfUk9PVH0vbGliL3B5dGhvbjoke1BZVEhPTlBBVEh9
darwin:
  <<: *all
  ROOT: !encrypt L1ZvbHVtZXMvcGlwZQ==
linux:
  <<: *all
  ROOT: !encrypt L21udC9waXBl
windows:
  <<: *all
  ROOT: !encrypt WDovcGlwZQ==
"""
        output = subprocess.check_output(
            command,
            shell=True,
            universal_newlines=True,
        )
        self.assertEqual(output, expected_output)

    def test_thing_encrypted(self):
        """Tests baking the thing stack with depth of 1 excrypted."""
        command = (
            f"%s thing --encrypt -o {self.filename} --depth 1; cat {self.filename}"
            % self.envstack_bin
        )
        expected_output = """#!/usr/bin/env envstack
include: [default]
all: &all
  <<: *all
  CHAR_LIST: !encrypt WydhJywgJ2InLCAnYycsICcke0hFTExPfSdd
  DICT: !encrypt eydhJzogMSwgJ2InOiAyLCAnYyc6ICcke0lOVH0nfQ==
  FLOAT: !encrypt MS4w
  HELLO: !encrypt Z29vZGJ5ZQ==
  INT: !encrypt NQ==
  LOG_LEVEL: !encrypt JHtMT0dfTEVWRUw6PUlORk99
  NUMBER_LIST: !encrypt WzEsIDIsIDNd
darwin:
  <<: *all
  ROOT: !encrypt JHtIT01FfS9MaWJyYXJ5L0FwcGxpY2F0aW9uIFN1cHBvcnQvcGlwZQ==
linux:
  <<: *all
  ROOT: !encrypt JHtIT01FfS8ubG9jYWwvcGlwZQ==
windows:
  <<: *all
  ROOT: !encrypt QzovUHJvZ3JhbURhdGEvcGlwZQ==
"""
        output = subprocess.check_output(
            command,
            shell=True,
            universal_newlines=True,
        )
        self.assertEqual(output, expected_output)

    def test_blank(self):
        """Tests baking a blank stack."""
        command = (
            f"%s doesnotexist -o {self.filename}; cat {self.filename}"
            % self.envstack_bin
        )
        expected_output = """#!/usr/bin/env envstack
include: []
all: &all
  <<: *all
darwin:
  <<: *all
linux:
  <<: *all
windows:
  <<: *all
"""
        output = subprocess.check_output(
            command,
            shell=True,
            universal_newlines=True,
        )
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
        """Tests the default stack with an echo command."""
        command = "%s -- echo {HELLO}" % self.envstack_bin
        expected_output = "world\n"
        output = subprocess.check_output(
            command,
            shell=True,
            universal_newlines=True,
        )
        self.assertEqual(output, expected_output)

    def test_default_ls(self):
        """Tests the default stack with an ls command."""
        command = "%s -- ls" % self.envstack_bin
        expected_output = subprocess.check_output(
            "ls", start_new_session=True, shell=True, universal_newlines=True
        )
        output = subprocess.check_output(command, shell=True, universal_newlines=True)
        self.assertEqual(output, expected_output)

    def test_thing_echo(self):
        """Tests the thing stack with an echo command."""
        command = "%s thing -- echo {HELLO}" % self.envstack_bin
        expected_output = "goodbye\n"
        output = subprocess.check_output(
            command, start_new_session=True, shell=True, universal_newlines=True
        )
        self.assertEqual(output, expected_output)

    def test_test_echo_deploy_root(self):
        """Tests the test stack with an echo command."""
        command = "%s test -- echo {DEPLOY_ROOT}" % self.envstack_bin
        expected_output = f"{self.root}/test\n"
        output = subprocess.check_output(
            command, start_new_session=True, shell=True, universal_newlines=True
        )
        self.assertEqual(output, expected_output)

    def test_test_echo_deploy_root(self):
        """Tests the test stack with an echo command."""
        command = "%s test foobar -- echo {DEPLOY_ROOT}" % self.envstack_bin
        expected_output = f"{self.root}/foobar\n"
        output = subprocess.check_output(
            command, start_new_session=True, shell=True, universal_newlines=True
        )
        self.assertEqual(output, expected_output)


class TestSet(unittest.TestCase):
    """Tests various envstack set commands."""

    def setUp(self):
        self.filename = "settest.env"
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

    def tearDown(self):
        if os.path.exists(self.filename):
            os.remove(self.filename)

    def test_hello_world(self):
        """Tests setting HELLO to world."""
        command = "%s --set HELLO:world" % self.envstack_bin
        expected_output = "HELLO=world\n"
        output = subprocess.check_output(
            command,
            shell=True,
            universal_newlines=True,
        )
        self.assertEqual(output, expected_output)

    def test_hello_world_encrypted(self):
        """Tests setting HELLO to world encrypted."""
        command = "%s --set HELLO:world --encrypt" % self.envstack_bin
        expected_output = "HELLO=d29ybGQ=\n"
        output = subprocess.check_output(
            command,
            shell=True,
            universal_newlines=True,
        )
        self.assertEqual(output, expected_output)

    def test_foo_bar(self):
        """Tests setting FOO and BAR."""
        command = r"%s -s FOO:foo BAR:\${FOO}" % self.envstack_bin
        expected_output = "FOO=foo\nBAR=${FOO}\n"
        output = subprocess.check_output(
            command,
            shell=True,
            universal_newlines=True,
        )
        self.assertEqual(output, expected_output)

    def test_foo_bar_encrypted(self):
        """Tests setting FOO and BAR encrypted."""
        command = r"%s -s FOO:foo BAR:\${FOO} --encrypt" % self.envstack_bin
        expected_output = "FOO=Zm9v\nBAR=JHtGT099\n"
        output = subprocess.check_output(
            command,
            shell=True,
            universal_newlines=True,
        )
        self.assertEqual(output, expected_output)

    def test_foo_bar_bake(self):
        """Tests setting FOO and BAR and bake it out to a file."""
        command = r"%s --set FOO:foo BAR:\${FOO} -o %s; cat %s" % (
            self.envstack_bin,
            self.filename,
            self.filename,
        )
        expected_output = """#!/usr/bin/env envstack
include: []
all: &all
  <<: *all
  BAR: ${FOO}
  FOO: foo
darwin:
  <<: *all
linux:
  <<: *all
windows:
  <<: *all
"""
        output = subprocess.check_output(
            command,
            shell=True,
            universal_newlines=True,
        )
        self.assertEqual(output, expected_output)

    def test_foo_bar_bake_encrypted(self):
        """Tests setting FOO and BAR and bake it out to a file with encrypted values."""
        command = r"%s --set FOO:foo BAR:\${FOO} -eo %s; cat %s" % (
            self.envstack_bin,
            self.filename,
            self.filename,
        )
        expected_output = """#!/usr/bin/env envstack
include: []
all: &all
  <<: *all
  BAR: !encrypt JHtGT099
  FOO: !encrypt Zm9v
darwin:
  <<: *all
linux:
  <<: *all
windows:
  <<: *all
"""
        output = subprocess.check_output(
            command,
            shell=True,
            universal_newlines=True,
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

    def test_issue_55(self):
        """Tests issue 55 missing env files using test environments.
        Tests dynamic ${ENVPATH} values that use ${STACK} in the path,

        env/dev.env:
            ENVPATH: ${ROOT}/dev/env:${ROOT}/prod/env:${ENVPATH}

        env/test.env:
            ENVPATH: ${ROOT}/${STACK}/env:${ROOT}/prod/env
        """
        from envstack.env import Env

        # update default.env to point to test root
        default_env_file = os.path.join(self.root, "prod", "env", "default.env")
        update_env_file(default_env_file, "ROOT", self.root)

        # create a new test env file that only exists in our test env dir
        test_env = os.path.join(self.root, "test_issue_55", "env")
        os.makedirs(test_env, exist_ok=True)
        test_env_file = os.path.join(test_env, "test_issue_55.env")

        data = {"FOO": "foo", "BAR": "bar", "BAZ": self.root}
        Env(data).write(test_env_file)
        self.assertTrue(os.path.exists(test_env_file))

        # dev.env does not use STACK in ENVPATH
        command = "%s dev test_issue_55 --sources" % self.envstack_bin
        expected_output = f"""{self.root}/prod/env/default.env
{self.root}/prod/env/dev.env
"""
        output = subprocess.check_output(
            command, start_new_session=True, shell=True, universal_newlines=True
        )
        self.assertEqual(output, expected_output)

        # test.env does use STACK in ENVPATH and should include our test env
        command = "%s test test_issue_55 --sources" % self.envstack_bin
        expected_output = f"""{self.root}/prod/env/default.env
{self.root}/prod/env/dev.env
{self.root}/prod/env/test.env
{self.root}/test_issue_55/env/test_issue_55.env
"""
        output = subprocess.check_output(
            command, start_new_session=True, shell=True, universal_newlines=True
        )
        self.assertEqual(output, expected_output)


if __name__ == "__main__":
    unittest.main()
