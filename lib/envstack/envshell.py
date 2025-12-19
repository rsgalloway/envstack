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

"""
Contains envshell wrapper class.

Goal: drop the user into an interactive shell *without* sourcing their usual
shell rc files, so prompt vars (PS1/PROMPT) set by envstack can survive.

Notes:
- You can override the detected shell with ENVSTACK_SHELL.
  Examples:
    ENVSTACK_SHELL=/bin/zsh envstack --shell
    ENVSTACK_SHELL=pwsh envstack --shell
"""

import os
from pathlib import Path
from typing import List

from . import config
from .wrapper import Wrapper


def _basename(p: str) -> str:
    """Return the lowercase basename of a path, robustly."""
    try:
        return Path(p).name.lower()
    except Exception:
        return os.path.basename(p).lower()


def _detect_shell_argv() -> List[str]:
    """
    Return argv list for a *clean* interactive shell.
    """
    shell = os.environ.get("ENVSTACK_SHELL", config.SHELL)

    if os.name == "nt":
        # Prefer COMSPEC if it looks like cmd.exe; otherwise allow pwsh/powershell.
        comspec = os.environ.get("COMSPEC", "cmd.exe")

        # If user explicitly asked for pwsh/powershell, honor it.
        base = _basename(shell)
        if base in ("pwsh", "pwsh.exe"):
            return [shell, "-NoExit", "-NoProfile"]
        if base in ("powershell", "powershell.exe"):
            return [shell, "-NoExit", "-NoProfile"]

        # Otherwise use cmd.exe, with /K to keep it open.
        # (Even if config.SHELL returned "cmd", use COMSPEC so we get the real path.)
        return [comspec, "/K"]

    # POSIX shells
    base = _basename(shell)

    # bash: skip /etc/profile, ~/.bash_profile, ~/.bashrc, but stay interactive
    if base == "bash":
        return [shell, "--noprofile", "--norc", "-i"]

    # zsh: -f skips zshrcs; -i for interactive
    if base == "zsh":
        return [shell, "-f", "-i"]

    # tcsh/csh: -f skips rc; interactive by default when attached to a tty
    if base in ("tcsh", "csh"):
        return [shell, "-f"]

    # fish: --no-config skips config.fish; interactive by default
    if base == "fish":
        return [shell, "--no-config"]

    # Fallback: try interactive flag if common; otherwise just exec the shell
    # (Most shells become interactive when connected to a tty anyway.)
    return [shell, "-i"]


class EnvshellWrapper(Wrapper):
    """A wrapper that spawns an interactive shell with the environment set."""

    def __init__(self, *args, **kwargs):
        super(EnvshellWrapper, self).__init__(*args, **kwargs)
        self.shell = False  # exec the shell directly

    def executable(self):
        """
        Kept for interface compatibility. The actual argv is produced in
        get_subprocess_command().
        """
        return ""

    def get_subprocess_command(self, env):
        """
        Override to return argv list for subprocess.Popen(..., shell=False).
        """
        return _detect_shell_argv()
