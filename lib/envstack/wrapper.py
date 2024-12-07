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
import re
import shlex
import subprocess
import traceback

from envstack import config, logger
from envstack.env import load_environ, resolve_environ
from envstack.util import encode, evaluate_modifiers


def to_args(cmd):
    """Converts a command line string to an arg list to be passed to
    subprocess.Popen that preserves args with quotes."""
    return shlex.split(cmd)


def shell_join(args):
    """Joins a list of arguments into a single quoted shell string."""
    argstr = ".".join(args)
    if '"' in argstr or "'" in argstr:
        try:
            return shlex.join(args)
        except AttributeError:
            return " ".join(shlex.quote(arg) for arg in args)
    else:
        return " ".join(args)


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
        self.shell = True
        self.log = logger.log
        self.env = load_environ(namespace)

    def executable(self):
        """Returns the path to the executable."""
        raise NotImplementedError

    def launch(self):
        """Launches the wrapped tool in a subprocess with env."""
        exitcode = 0
        env = self.get_subprocess_env()
        command = self.get_subprocess_command(env)

        try:
            process = subprocess.Popen(
                args=command,
                bufsize=0,
                env=encode(env),
                shell=self.shell,
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

    def get_subprocess_args(self, cmd):
        """Returns the arguments to be passed to the subprocess."""
        return self.args

    def get_subprocess_command(self, env):
        """Returns the command to be passed to the subprocess."""
        cmd = evaluate_modifiers(self.executable(), env)
        args = self.get_subprocess_args(cmd)
        return " ".join([cmd] + args)

    def get_subprocess_env(self):
        """
        Returns the environment that gets passed to the subprocess when launch()
        is called on the wrapper.
        """
        env = os.environ.copy()
        env.update(resolve_environ(self.env))
        return env


class CommandWrapper(Wrapper):
    """Wrapper class for running wrapped commands from the command-line."""

    def __init__(self, namespace=config.DEFAULT_NAMESPACE, args=[]):
        """
        Initializes the command wrapper with the given namespace and args, e.g.:

            >>> cmd = CommandWrapper('stack', ['ls', '-al'])
            >>> print(cmd.executable())
            ls
            >>> print(cmd.args)
            ['-al']

        :param namespace: stack namespace (default: 'stack')
        :param args: command and arguments as a list
        """
        super(CommandWrapper, self).__init__(namespace, args)
        self.cmd = args

    def executable(self):
        """Returns the command to run."""
        return config.SHELL


class ShellWrapper(CommandWrapper):
    """Wrapper class for running wrapped commands in bash, sh, or zsh."""

    def __init__(self, namespace=config.DEFAULT_NAMESPACE, args=[]):
        """
        Initializes the command wrapper with the given namespace and args,
        replacing the original command with the shell command, e.g.:

            >>> cmd = ShellWrapper('stack', ['ls', '-l'])
            >>> print(cmd.executable())
            bash
            >>> print(cmd.args)
            ['-i', '-c', 'ls -l']

        :param namespace: stack namespace (default: 'stack')
        :param args: command and arguments as a list
        """
        super(ShellWrapper, self).__init__(namespace, args)

    def get_subprocess_command(self, env):
        """Returns the command to be passed to the shell in a subprocess."""
        if re.search(r"\$\w+", self.cmd):
            return f'{config.SHELL} -i -c "{self.cmd}"'
        else:
            escaped_command = shlex.quote(self.cmd)
            return f"{config.SHELL} -i -c {escaped_command}"

    def executable(self):
        """Returns the shell command to run the original command."""
        return self.cmd


class CmdWrapper(CommandWrapper):
    """Wrapper class for running wrapped commands in command prompt."""

    def __init__(self, namespace=config.DEFAULT_NAMESPACE, args=[]):
        """
        Initializes the command wrapper with the given namespace and args,
        replacing the original command with the shell command, e.g.:

            >>> cmd = CmdWrapper('stack', ['dir'])
            >>> print(cmd.executable())
            cmd
            >>> print(cmd.args)
            ['/c', 'dir']

        :param namespace: stack namespace (default: 'stack')
        :param args: command and arguments as a list
        """
        super(CmdWrapper, self).__init__(namespace, args)
        self.args = ["/c", self.cmd]
        self.shell = False

    def get_subprocess_args(self, cmd):
        """Returns the arguments to be passed to the subprocess."""
        return [cmd] + self.args

    def executable(self):
        """Returns the shell command to run the original command."""
        self.cmd = config.SHELL
        return self.cmd


def run_command(command: str, namespace: str = config.DEFAULT_NAMESPACE):
    """
    Runs a given command with the given stack namespace.

        >>> run_command(['ls', '-l'])

    Or to run in a specific stack namespace:

        >>> run_command(['ls', '-l'], 'my-stack')

     - Automatically detects the shell to use based on the config.SHELL value.
     - Converts {VAR} to $VAR for bash, sh, zsh, and %VAR% for cmd.

    :param command: command to run as a list of arguments
    :param namespace: environment stack namespace (default: 'stack')
    :returns: command exit code
    """
    logger.setup_stream_handler()
    if config.SHELL in ["bash", "sh", "zsh"]:
        # convert {VAR} to ${VAR}, e.g. 'echo {VAR}' -> 'echo ${VAR}'
        command = re.sub(r"\{(\w+)\}", r"${\1}", shell_join(command))
        cmd = ShellWrapper(namespace, command)
    elif config.SHELL in ["cmd"]:
        # convert {VAR} to %VAR%, e.g. 'echo {VAR}' -> 'echo %VAR%'
        command = re.sub(r"\{(\w+)\}", r"%\1%", " ".join(command))
        cmd = CmdWrapper(namespace, command)
    else:
        cmd = CommandWrapper(namespace, command)
    return cmd.launch()
