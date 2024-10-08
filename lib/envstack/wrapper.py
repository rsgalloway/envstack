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

from envstack import logger
from envstack.env import load_environ, expandvars


def decode_value(value):
    """Returns a decoded value that's been encoded by a wrapper.

    Decoding encoded environments can be tricky. For example, it must account for path
    templates that include curly braces, e.g. path templates string like this must be
    preserved:

        '/path/with/{variable}'

    :param value: wrapper encoded env value
    :returns: decoded value
    """
    # TODO: find a better way to encode/decode wrapper envs
    return (
        str(value)
        .replace("'[", "[")
        .replace("]'", "]")
        .replace('"[', "[")
        .replace(']"', "]")
        .replace('"{"', "{'")
        .replace('"}"', "'}")
        .replace("'{'", "{'")
        .replace("'}'", "'}")
    )


def encode(env, resolved=True):
    """Returns environment as a dict with str encoded key/values for passing to
    wrapper subprocesses.

    :param env: `Env` instance or os.environ.
    :param resolved: fully resolve values (default=True).
    :returns: dict with bytestring key/values.
    """
    c = lambda v: str(v)
    if resolved:
        return dict((c(k), c(expandvars(v, env))) for k, v in env.items())
    return dict((c(k), c(v)) for k, v in env.items())


def to_args(cmd):
    """Converts a command line string to an arg list to be passed to subprocess.Popen
    that preserves args with quotes."""

    import shlex

    return shlex.split(cmd)


class Wrapper(object):
    """Wrapper class for executables. Subprocessed with preconfigured environment.

    Subclasses should override executable():

        class ToolWrapper(Wrapper):
            def __init__(self, name, args):
                super(ToolWrapper, self).__init__(name, args)
            def executable(self):
                return '$TOOL_ROOT/bin/tool'

    To launch 'tool', create an instance of the wrapper, and pass as the first
    argument the namespace continaining config options, then call launch():

        tool = ToolWrapper('tool', sys.argv[1:])
        tool.launch()

    The log attribute can be set to a custom logger:

        tool.log = MyLogger()
    """

    def __init__(self, name, args=[]):
        super(Wrapper, self).__init__()
        self.args = args
        self.env = load_environ(name, environ=os.environ)
        self.log = logger.log
        self.name = name

    def executable(self):
        """Returns the path to the executable."""
        raise NotImplementedError

    def launch(self):
        """Launches the wrapped tool in a subprocess with env."""
        exitcode = 0

        # expand command vars before passing to subprocess
        cmd = expandvars(self.executable(), self.env, recursive=True)

        # run command in subprocess
        try:
            process = subprocess.Popen(
                args=to_args(cmd) + self.args,
                bufsize=0,
                env=encode(self.get_subprocess_env()),
            )

        except Exception as err:
            import traceback

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
        """Returns the environment that gets passed to the subprocess when launch()
        is called on the wrapper.
        """
        return self.env
