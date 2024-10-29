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
Contains executable wrapper classes and functions.
"""

import os
import subprocess
import traceback

from envstack import logger
from envstack.env import encode, expandvars, load_environ


def to_args(cmd):
    """Converts a command line string to an arg list to be passed to subprocess.Popen
    that preserves args with quotes."""

    import shlex

    return shlex.split(cmd)


class Wrapper(object):
    """Wrapper class for executables. Subprocessed with preconfigured environment.

    Subclasses should override executable():

        class ToolWrapper(Wrapper):
            def __init__(self, namespace, args):
                super(ToolWrapper, self).__init__(namespace, args)
            def executable(self):
                return '$TOOL_ROOT/bin/tool'

    To launch 'tool', create an instance of the wrapper, and pass as the first
    argument the namespace continaining config options, then call launch():

        tool = ToolWrapper('tool', sys.argv[1:])
        tool.launch()

    The log attribute can be set to a custom logger:

        tool.log = MyLogger()
    """

    def __init__(self, namespace, args=[]):
        """Initializes the wrapper with the given namespace and args.

        :param namespace: namespace
        :param args: command line arguments
        """
        super(Wrapper, self).__init__()
        self.args = args
        self.name = namespace
        self.log = logger.log
        self.env = load_environ(namespace)

    def executable(self):
        """Returns the path to the executable."""
        raise NotImplementedError

    def launch(self):
        """Launches the wrapped tool in a subprocess with env."""
        exitcode = 0

        # get subprocess env, cmd and args
        env = self.get_subprocess_env()
        cmd = expandvars(self.executable(), env, recursive=True)
        args = " ".join(['"%s"' % arg for arg in to_args(cmd) + self.args])

        # run command in subprocess
        try:
            process = subprocess.Popen(
                args=args,
                bufsize=0,
                env=env,
                shell=True,
            )

        except Exception:
            traceback.print_exc()
            exitcode = 1

        else:
            stdout, stderr = process.communicate()
            while stdout and stderr:
                self.log.info(stdout)
                self.log.error(stderr)
            exitcode = process.poll()

        return exitcode

    def get_subprocess_env(self):
        """
        Returns the environment that gets passed to the subprocess when launch()
        is called on the wrapper.
        """
        env = os.environ.copy()
        env.update(encode(self.env))
        return env


class CommandWrapper(Wrapper):
    """Wrapper class for running wrapped commands from the command-line."""

    def __init__(self, namespace, args=[]):
        """
        Initializes the command wrapper with the given namespace and args.

        :param namespace: stack namespace
        :param args: command line arguments
        """
        super(CommandWrapper, self).__init__(namespace, args)
        self.log.debug("running command [stack: %s] %s", namespace, args)
        self.cmd = args[0]
        self.args = args[1:]

    def executable(self):
        return self.cmd


def run_command(namespace, command):
    """
    Runs a given command with the given stack namespace.

    :param namespace: stack namespace
    :param command: command to run as arg list
    :returns: exit code
    """
    logger.setup_stream_handler()
    cmd = CommandWrapper(namespace, command)
    return cmd.launch()
