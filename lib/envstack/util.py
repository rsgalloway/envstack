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
Contains common utility functions and classes.
"""

import os
import re
import sys

# regex pattern to find variables like ${VAR}, ${VAR:=default}, ${VAR:?message}
variable_pattern = re.compile(r"\$\{([a-zA-Z_][a-zA-Z0-9_]*)(?::([=?])(.*?))?\}")


def clear_sys_path(var="PYTHONPATH"):
    """
    Remove paths from sys.path that are in the given environment variable.

    :param var: The environment variable to remove paths from.
    """
    for path in get_paths_from_var(var):
        if path and path in sys.path:
            sys.path.remove(path)


def load_sys_path(var="PYTHONPATH", pathsep=os.pathsep, reverse=True):
    """
    Add paths from the given environment variable to sys.path.

    :param var: The environment variable to add paths from.
    :param pathsep: The path separator to use.
    :param reverse: Reverse the order of the paths.
    """
    for path in get_paths_from_var(var, pathsep, reverse):
        if path and path not in sys.path:
            sys.path.insert(0, path)


def dict_diff(dict1, dict2):
    """
    Compare two dictionaries and return their differences.

    :param dict1: First dictionary.
    :param dict2: Second dictionary.
    :returns: diff dict: 'added', 'removed', 'changed', and 'unchanged'.
    """
    added = {k: dict2[k] for k in dict2 if k not in dict1}
    removed = {k: dict1[k] for k in dict1 if k not in dict2}
    changed = {
        k: (dict1[k], dict2[k]) for k in dict1 if k in dict2 and dict1[k] != dict2[k]
    }
    unchanged = {k: dict1[k] for k in dict1 if k in dict2 and dict1[k] == dict2[k]}

    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "unchanged": unchanged,
    }


def get_paths_from_var(var="PYTHONPATH", pathsep=os.pathsep, reverse=True):
    """Returns a list of paths from a given pathsep separated environment
    variable.

    :param var: The environment variable to get paths from.
    :param pathsep: The path separator to use.
    :param reverse: Reverse the order of the paths.
    :returns: A list of paths.
    """

    paths = []
    value = os.environ.get(var)

    if value:
        paths = value.split(pathsep)

        if reverse:
            paths.reverse()

    return paths


def evaluate_modifiers(expression, environ=os.environ):
    """
    Evaluates Bash-like variable expansion modifiers.

    Supports:
    - value like "world" (no substitution)
    - ${VAR} for direct substitution (empty string if unset)
    - ${VAR:=default} to set and use a default value if unset
    - ${VAR:?error message} to raise an error if the variable is unset or null

    :param expression: The Bash-like string, e.g.,
        "${VAR:=default}/path", "${VAR}/path", or "${VAR:?error message}"
    :return: The resulting evaluated string with all substitutions applied.
    :raises ValueError: If a variable is undefined and has the :? syntax with an
        error message.
    """

    def substitute_variable(match):
        var_name = match.group(1)
        operator = match.group(2)
        default = match.group(3)
        value = environ.get(var_name)

        if operator == "=":
            if value is None:
                value = default
                # os.environ[var_name] = value
        elif operator == "?":
            if value is None:
                error_message = default if default else f"{var_name} is not set"
                raise ValueError(f"{var_name}: {error_message}")
        elif operator is None:
            value = value or ""

        return value

    return variable_pattern.sub(substitute_variable, str(expression))
