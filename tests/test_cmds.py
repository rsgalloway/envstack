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
import subprocess
import unittest


class TestUnresolved(unittest.TestCase):
    """Tests unresolved environment variables."""

    def setUp(self):
        self.envstack_bin = os.path.join(
            os.path.dirname(__file__), "..", "bin", "envstack"
        )
        envpath = os.path.join(os.path.dirname(__file__), "..", "env")
        os.environ["ENVPATH"] = envpath
        os.environ["INTERACTIVE"] = "0"

    def test_default(self):
        expected_output = """DEPLOY_ROOT=${ROOT}/${ENV}
ENV=prod
ENVPATH=${DEPLOY_ROOT}/env:${ENVPATH}
HELLO=${HELLO:=world}
LOG_LEVEL=${LOG_LEVEL:=INFO}
PATH=${DEPLOY_ROOT}/bin:${PATH}
PYTHONPATH=${DEPLOY_ROOT}/lib/python:${PYTHONPATH}
ROOT=/mnt/pipe
STACK=default
"""
        command = self.envstack_bin
        output = subprocess.check_output(command, shell=True, universal_newlines=True)
        self.assertEqual(output, expected_output)

    def test_dev(self):
        expected_output = """DEPLOY_ROOT=${ROOT}/dev
ENV=dev
ENVPATH=${ROOT}/dev/env:${ROOT}/prod/env:${ENVPATH}
HELLO=${HELLO:=world}
LOG_LEVEL=DEBUG
PATH=${ROOT}/dev/bin:${ROOT}/prod/bin:${PATH}
PYTHONPATH=${ROOT}/dev/lib/python:${ROOT}/prod/lib/python:${PYTHONPATH}
ROOT=/mnt/pipe
STACK=dev
"""
        command = "%s dev" % self.envstack_bin
        output = subprocess.check_output(command, shell=True, universal_newlines=True)
        self.assertEqual(output, expected_output)

    def test_distman(self):
        expected_output = """DEPLOY_ROOT=${ROOT}/${ENV}
ENV=${ENV:=prod}
ENVPATH=${DEPLOY_ROOT}/env:${ENVPATH}
HELLO=${HELLO:=world}
LOG_LEVEL=INFO
PATH=${DEPLOY_ROOT}/bin:${PATH}
PYTHONPATH=${DEPLOY_ROOT}/lib/python:${PYTHONPATH}
ROOT=/mnt/pipe
STACK=distman
"""
        command = "%s distman" % self.envstack_bin
        output = subprocess.check_output(command, shell=True, universal_newlines=True)
        self.assertEqual(output, expected_output)

    def test_hello(self):
        expected_output = """DEPLOY_ROOT=${ROOT}/${ENV}
ENV=prod
ENVPATH=${DEPLOY_ROOT}/env:${ENVPATH}
HELLO=${HELLO:=world}
LOG_LEVEL=${LOG_LEVEL:=INFO}
PATH=${DEPLOY_ROOT}/bin:${PATH}
PYEXE=/usr/bin/python
PYTHONPATH=${DEPLOY_ROOT}/lib/python:${PYTHONPATH}
ROOT=/mnt/pipe
STACK=hello
"""
        command = "%s hello" % self.envstack_bin
        output = subprocess.check_output(command, shell=True, universal_newlines=True)
        self.assertEqual(output, expected_output)

    def test_thing(self):
        expected_output = """CHAR_LIST=['a', 'b', 'c', '${HELLO}']
DEPLOY_ROOT=${ROOT}/${ENV}
DICT={'a': 1, 'b': 2, 'c': 3}
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


class TestResolved(unittest.TestCase):
    """Tests resolved environment variables."""

    def setUp(self):
        self.envstack_bin = os.path.join(
            os.path.dirname(__file__), "..", "bin", "envstack"
        )
        envpath = os.path.join(os.path.dirname(__file__), "..", "env")
        os.environ["ENVPATH"] = envpath
        os.environ["INTERACTIVE"] = "0"
        os.environ["ROOT"] = "/var/tmp/pipe"  # ROOT cannot be overridden

    def test_default(self):
        expected_output = """DEPLOY_ROOT=/mnt/pipe/prod
HELLO=world
ROOT=/mnt/pipe
STACK=default
"""
        command = "%s -r DEPLOY_ROOT HELLO ROOT STACK" % self.envstack_bin
        output = subprocess.check_output(command, shell=True, universal_newlines=True)
        self.assertEqual(output, expected_output)

    def test_dev(self):
        expected_output = """DEPLOY_ROOT=/mnt/pipe/dev
HELLO=world
ROOT=/mnt/pipe
STACK=dev
"""
        command = "%s dev -r DEPLOY_ROOT HELLO ROOT STACK" % self.envstack_bin
        output = subprocess.check_output(command, shell=True, universal_newlines=True)
        self.assertEqual(output, expected_output)

    def test_distman(self):
        expected_output = """DEPLOY_ROOT=/mnt/pipe/prod
ROOT=/mnt/pipe
STACK=distman
"""
        command = "%s distman -r DEPLOY_ROOT ROOT STACK" % self.envstack_bin
        output = subprocess.check_output(command, shell=True, universal_newlines=True)
        self.assertEqual(output, expected_output)

    def test_dev_distman(self):
        expected_output = """DEPLOY_ROOT=/mnt/pipe/dev
ROOT=/mnt/pipe
STACK=distman
"""
        command = "%s dev distman -r DEPLOY_ROOT ROOT STACK" % self.envstack_bin
        output = subprocess.check_output(command, shell=True, universal_newlines=True)
        self.assertEqual(output, expected_output)

    def test_test(self):
        expected_output = """DEPLOY_ROOT=/mnt/pipe/test
HELLO=world
ROOT=/mnt/pipe
STACK=test
"""
        command = (
            "ENV=blah ROOT=/var/tmp %s test -r DEPLOY_ROOT HELLO ROOT STACK"
            % self.envstack_bin
        )
        output = subprocess.check_output(command, shell=True, universal_newlines=True)
        self.assertEqual(output, expected_output)

    def test_foobar(self):
        expected_output = """DEPLOY_ROOT=/mnt/pipe/foobar
HELLO=world
ROOT=/mnt/pipe
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
        expected_output = "/mnt/pipe/test\n"
        output = subprocess.check_output(
            command, start_new_session=True, shell=True, universal_newlines=True
        )
        self.assertEqual(output, expected_output)

    def test_test_echo_deploy_root(self):
        command = "%s test foobar -- echo {DEPLOY_ROOT}" % self.envstack_bin
        expected_output = "/mnt/pipe/foobar\n"
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
        os.environ["ENVPATH"] = envpath
        os.environ["INTERACTIVE"] = "0"

    def test_default_deploy_root(self):
        os.environ["ENV"] = "invalid"  # should not be able to override ENV
        command = "%s -- %s" % (self.envstack_bin, self.python_cmd)
        expected_output = "/mnt/pipe/prod\n"
        output = subprocess.check_output(
            command, start_new_session=True, shell=True, universal_newlines=True
        )
        self.assertEqual(output, expected_output)

    def test_dev_deploy_root(self):
        os.environ["ENV"] = "invalid"  # should not be able to override ENV
        command = "%s dev -- %s" % (self.envstack_bin, self.python_cmd)
        expected_output = "/mnt/pipe/dev\n"
        output = subprocess.check_output(
            command, start_new_session=True, shell=True, universal_newlines=True
        )
        self.assertEqual(output, expected_output)

    def test_test_deploy_root(self):
        command = "ENV=invalid %s test -- %s" % (self.envstack_bin, self.python_cmd)
        expected_output = "/mnt/pipe/test\n"
        output = subprocess.check_output(
            command, start_new_session=True, shell=True, universal_newlines=True
        )
        self.assertEqual(output, expected_output)

    def test_foobar_deploy_root(self):
        command = "ENV=invalid %s test foobar -- %s" % (
            self.envstack_bin,
            self.python_cmd,
        )
        expected_output = "/mnt/pipe/foobar\n"
        output = subprocess.check_output(
            command, start_new_session=True, shell=True, universal_newlines=True
        )
        self.assertEqual(output, expected_output)


if __name__ == "__main__":
    unittest.main()
