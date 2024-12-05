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


class TestStacks(unittest.TestCase):
    def setUp(self):
        self.envstack_bin = os.path.join(
            os.path.dirname(__file__), "..", "bin", "envstack"
        )
        envpath = os.path.join(os.path.dirname(__file__), "..", "env")
        os.environ["ENVPATH"] = envpath

    def test_default(self):
        expected_output = """DEPLOY_ROOT=${ROOT}/${ENV}
ENV=${ENV:=${STACK}}
ENVPATH=${ROOT}/${STACK}/env:${ENVPATH}
HELLO=${HELLO:=world}
LOG_LEVEL=${LOG_LEVEL:=INFO}
PATH=${ROOT}/${STACK}/bin:${PATH}
PYTHONPATH=${ROOT}/${STACK}/lib/python:${PYTHONPATH}
ROOT=${HOME}/.local/pipe
STACK=default
"""
        command = self.envstack_bin
        output = subprocess.check_output(command, shell=True, universal_newlines=True)
        self.assertEqual(output, expected_output)

    def test_prod(self):
        expected_output = """DEPLOY_ROOT=${ROOT}/prod
ENV=prod
ENVPATH=${DEPLOY_ROOT}/env
HELLO=${HELLO:=world}
LOG_LEVEL=${LOG_LEVEL:=INFO}
PATH=${DEPLOY_ROOT}/bin:${PATH}
PYTHONPATH=${DEPLOY_ROOT}/lib/python:${PYTHONPATH}
ROOT=/mnt/pipe
STACK=prod
"""
        command = "%s prod" % self.envstack_bin
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

    def test_hello(self):
        expected_output = """DEPLOY_ROOT=${ROOT}/${ENV}
ENV=${ENV:=${STACK}}
ENVPATH=${ROOT}/${STACK}/env:${ENVPATH}
HELLO=${HELLO:=world}
LOG_LEVEL=${LOG_LEVEL:=INFO}
PATH=${ROOT}/${STACK}/bin:${PATH}
PYEXE=python
PYTHONPATH=${ROOT}/${STACK}/lib/python:${PYTHONPATH}
ROOT=${HOME}/.local/pipe
STACK=hello
"""
        command = "%s hello" % self.envstack_bin
        output = subprocess.check_output(command, shell=True, universal_newlines=True)
        self.assertEqual(output, expected_output)

    def test_thing(self):
        expected_output = """CHAR_LIST=['a', 'b', 'c']
DEPLOY_ROOT=${ROOT}/dev
DICT={'a': 1, 'b': 2, 'c': 3}
ENV=dev
ENVPATH=${ROOT}/dev/env:${ROOT}/prod/env:${ENVPATH}
FLOAT=1.0
HELLO=goodbye
INT=5
LOG_LEVEL=${LOG_LEVEL:=INFO}
NUMBER_LIST=[1, 2, 3]
PATH=${ROOT}/dev/bin:${ROOT}/prod/bin:${PATH}
PYTHONPATH=/usr/local/lib/python2.7/site-packages:${PYTHONPATH}
ROOT=/mnt/tools
STACK=thing
"""
        command = "%s thing" % self.envstack_bin
        output = subprocess.check_output(command, shell=True, universal_newlines=True)
        self.assertEqual(output, expected_output)


class TestCommands(unittest.TestCase):
    def setUp(self):
        self.envstack_bin = os.path.join(
            os.path.dirname(__file__), "..", "bin", "envstack"
        )
        envpath = os.path.join(os.path.dirname(__file__), "..", "env")
        os.environ["ENVPATH"] = envpath

    def test_default_echo(self):
        command = "%s -- echo {HELLO}" % self.envstack_bin
        expected_output = "world\n"
        output = subprocess.check_output(
            command, start_new_session=True, shell=True, universal_newlines=True
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


if __name__ == "__main__":
    unittest.main()
