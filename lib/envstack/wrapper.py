#!/usr/bin/env python3
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


def to_args(cmd: str):
    """
    Converts a command line string to an arg list to be passed to
    subprocess.Popen that preserves args with quotes.

    :param cmd: command line string.
    """
    return shlex.split(cmd)


def shell_join(args):
    """
    Joins a list of arguments into a single quoted shell string.

    :param args: list of arguments.
    :returns: shell string.
    """
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

    shell: bool = False

    def __init__(self, namespace, args=[]):
        """Initializes the wrapper with the given namespace and args.

        :param namespace: environment stack namespace.
        :param args: command line arguments.
        """
        super(Wrapper, self).__init__()
        self.args = args
        self.name = namespace
        self.shell = self.shell
        self.log = logger.log
        self.env = load_environ(namespace)

    def executable(self):
        """Returns the path to the executable."""
        raise NotImplementedError

    def launch(self):
        """Launches the wrapped tool in a subprocess with env."""
        env = self.get_subprocess_env()
        command = self.get_subprocess_command(env)

        try:
            proc = subprocess.run(
                command,
                env=encode(env),
                shell=self.shell,
                check=False,
            )
            return proc.returncode
        except Exception:
            traceback.print_exc()
            return 1

    def get_subprocess_args(self, cmd):
        """Returns the arguments to be passed to the subprocess."""
        return self.args

    def get_subprocess_command(self, env):
        """Returns argv (preferred) or a command string if shell=True."""
        cmd = evaluate_modifiers(self.executable(), env)
        args = self.get_subprocess_args(cmd)

        if self.shell:
            return " ".join([cmd] + args)

        return [cmd] + args

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

            >>> cmd = CommandWrapper(stack, ['ls', '-al'])
            >>> print(cmd.executable())
            ls
            >>> print(cmd.args)
            ['-al']

        :param namespace: environment stack name (default: 'default').
        :param args: command and arguments as a list.
        """
        super(CommandWrapper, self).__init__(namespace, args)
        self.cmd = list(args)

    def executable(self):
        """Returns the command to run."""
        return self.cmd[0]

    def get_subprocess_args(self, cmd):
        return self.cmd[1:]


class ShellWrapper(Wrapper):
    """
    Runs a *string expression* under the user's shell using -c.
    Useful for wrapping shell expressions that need variable expansion:

        >>> shell = ShellWrapper('default', 'echo {HOME}')
    """

    def __init__(self, namespace=config.DEFAULT_NAMESPACE, expr: str = ""):
        super().__init__(namespace, args=[])
        self.expr = expr

    def get_interactive(self, env: dict = os.environ):
        override = env.get("INTERACTIVE")
        if override is not None:
            return str(override).lower() in {"1", "true", "yes", "on"}
        return False  # default safe

    def get_subprocess_command(self, env: dict = os.environ):
        interactive = self.get_interactive(env)
        if interactive:
            return [config.SHELL, "-i", "-c", self.expr]
        return [config.SHELL, "-c", self.expr]

    def executable(self):
        """Returns the shell command to run the original command."""
        return self.cmd


class CmdWrapper(CommandWrapper):
    """Wrapper class for running wrapped commands in Windows cmd.exe."""

    def __init__(self, namespace=config.DEFAULT_NAMESPACE, args=[]):
        super().__init__(namespace, args)

        # Always run through cmd.exe explicitly
        self.shell = False
        self._cmd_exe = config.SHELL  # expected: "cmd" or "cmd.exe"

        # Join the intended argv into one command-line string for /c
        cmdline = shell_join(self.cmd)

        # cmd.exe /c <command>
        self._subprocess_argv = [self._cmd_exe, "/c", cmdline]

    def executable(self):
        return self._cmd_exe

    def get_subprocess_args(self, cmd):
        # Not used (we override get_subprocess_command)
        return []

    def get_subprocess_command(self, env):
        return list(self._subprocess_argv)


def capture_output(
    command: str,
    namespace: str = config.DEFAULT_NAMESPACE,
    timeout: int = config.COMMAND_TIMEOUT,
):
    """
    Runs a command (string or argv) with the given stack namespace and captures stdout/stderr.

    Returns: (returncode, stdout, stderr)
    """
    import errno

    shellname = os.path.basename(config.SHELL).lower()
    argv = list(command) if isinstance(command, (list, tuple)) else to_args(command)

    # build env exactly like Wrapper.launch()
    env = os.environ.copy()
    env.update(resolve_environ(load_environ(namespace)))

    # prefer argv execution where possible
    if shellname in ["bash", "sh", "zsh"]:
        needs_shell = any(re.search(r"\{(\w+)\}", a) for a in argv)
        if needs_shell:
            expr_argv = [re.sub(r"\{(\w+)\}", r"${\1}", a) for a in argv]
            expr = shell_join(expr_argv)
            cmd = [config.SHELL, "-c", expr]
        else:
            cmd = argv

    # for cmd always use original command string
    elif shellname in ["cmd"]:
        cmd = command

    else:
        cmd = argv

    try:
        proc = subprocess.run(
            cmd,
            env=encode(env),
            shell=False,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except FileNotFoundError as e:
        # no process ran; synthesize a bash-like error and code
        # 127 is the conventional "command not found" code in shells
        missing = e.filename or (
            cmd[0] if isinstance(cmd, list) and cmd else str(command)
        )
        return 127, "", f"{missing}: command not found"
    except OSError as e:
        # Other OS-level execution errors (permission, exec format, etc.)
        rc = 126 if getattr(e, "errno", None) in (errno.EACCES,) else 1
        return rc, "", str(e)
    except subprocess.TimeoutExpired as e:
        return 124, "", f"Command timed out after {timeout} seconds"


def run_command(command: str, namespace: str = config.DEFAULT_NAMESPACE):
    """
    Runs a given command with the given stack namespace.

        >>> run_command(['ls', '-l'])

    Or to run in a specific stack namespace:

        >>> run_command(['ls', '-l'], 'my-stack')

     - Automatically detects the shell to use.
     - Converts {VAR} to $VAR for bash, sh, zsh, and %VAR% for cmd.

    :param command: command to run as a list of arguments.
    :param namespace: environment stack name (default: 'default').
    :returns: command exit code
    """
    logger.setup_stream_handler()
    shellname = os.path.basename(config.SHELL).lower()
    argv = list(command) if isinstance(command, (list, tuple)) else to_args(command)

    if shellname in ["bash", "sh", "zsh"]:
        needs_shell = any(re.search(r"\{(\w+)\}", a) for a in argv)
        if needs_shell:
            expr_argv = [re.sub(r"\{(\w+)\}", r"${\1}", a) for a in argv]
            expr = shell_join(expr_argv)
            return ShellWrapper(namespace, expr).launch()

        return CommandWrapper(namespace, argv).launch()

    if shellname in ["cmd"]:
        expr = [re.sub(r"\{(\w+)\}", r"%\1%", a) for a in argv]
        return CmdWrapper(namespace, expr).launch()

    return CommandWrapper(namespace, argv).launch()
