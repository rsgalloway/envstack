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
        shell = os.environ.get("SHELL")
        if shell:
            return shell.split("/")[-1]
        else:
            return "unknown"


DEBUG = os.getenv("DEBUG")
DEFAULT_NAMESPACE = os.getenv("DEFAULT_ENV_STACK", "stack")
ENV = os.getenv("ENV", "prod")
HOME = os.getenv("HOME")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
ON_POSIX = "posix" in sys.builtin_module_names
PLATFORM = platform.system().lower()
PYTHON_VERSION = sys.version_info[0]
SHELL = detect_shell()
USERNAME = os.getenv("USERNAME", os.getenv("USER"))

# set some default environment variables
DEFAULT_ENV = {
    "ENV": ENV,
    "HOME": HOME,
    "PLATFORM": PLATFORM,
    "USER": USERNAME,
}

# default location of envstack files
# NOTE: the siteconf sitecustomize.py module may override this
DEFAULT_ENV_DIR = os.getenv(
    "DEFAULT_ENV_DIR",
    {
        "darwin": "{HOME}/Library/Application Support/envstack",
        "linux": "{HOME}/.local/envstack",
        "windows": "C:\\ProgramData\\envstack",
    }.get(PLATFORM).format(**DEFAULT_ENV),
)
