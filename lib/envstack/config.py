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
Contains default configs and settings.
"""

import os
import platform
import sys


def detect_shell():
    """Detect the current shell."""
    if PLATFORM == "windows":
        comspec = os.environ.get("ComSpec")
        if comspec:
            if "cmd.exe" in comspec:
                return "cmd"
            elif "powershell.exe" in comspec:
                return "pwsh"
        else:
            return "unknown"
    else:
        shell = os.environ.get("SHELL", "/bin/bash")
        if shell:
            return shell
        else:
            return "/usr/bin/bash"


# debug mode
DEBUG = os.getenv("DEBUG")

# default namespace
DEFAULT_NAMESPACE = os.getenv("DEFAULT_ENV_STACK", "default")

# allow embedded commands
ALLOW_COMMANDS = os.getenv("ALLOW_COMMANDS", "0") in ("1", "true", "True", "TRUE")

# embedded command timeout in seconds
COMMAND_TIMEOUT = int(os.getenv("COMMAND_TIMEOUT", 5))

# default environment variables
ENV = os.getenv("ENV", "prod")
HOME = os.getenv("HOME")

# Ignore missing stack files when resolving environments
IGNORE_MISSING = os.getenv("IGNORE_MISSING", "1") in ("1", "true", "True", "TRUE")

# logging level
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

# platform and shell info
ON_POSIX = "posix" in sys.builtin_module_names
PLATFORM = platform.system().lower()
PYTHON_VERSION = sys.version_info[0]
SHELL = detect_shell()
USERNAME = os.getenv("USERNAME", os.getenv("USER"))

# set some default environment values
DEFAULT_ENV = {
    "ENV": ENV,
    "HOME": HOME,
    "PLATFORM": PLATFORM,
    "ROOT": os.getenv(
        "ROOT",
        {
            "darwin": "{HOME}/Library/Application Support/pipe",
            "linux": "{HOME}/.local/pipe",
            "windows": "C:\\ProgramData\\pipe",
        }
        .get(PLATFORM)
        .format(**locals()),
    ),
    "USER": USERNAME,
}
