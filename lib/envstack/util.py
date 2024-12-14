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

from envstack import config
from envstack.exceptions import CyclicalReference
from collections import OrderedDict

# value for unresolvable variables
null = ""

# regular expression pattern for Bash-like variable expansion
variable_pattern = re.compile(
    r"\$\{([a-zA-Z_][a-zA-Z0-9_]*)(?::([=?])(\$\{[a-zA-Z_][a-zA-Z0-9_]*\}|[^}]*))?\}"
)


def clear_sys_path(var: str = "PYTHONPATH"):
    """
    Remove paths from sys.path that are in the given environment variable.

    :param var: The environment variable to remove paths from.
    """
    for path in get_paths_from_var(var):
        if path and path in sys.path:
            sys.path.remove(path)


def decode_value(value: str):
    """Returns a decoded value that's been encoded by a wrapper.

    Decoding encoded environments can be tricky. For example, it must account for path
    templates that include curly braces, e.g. path templates string like this must be
    preserved:

        '/path/with/{variable}'

    :param value: wrapper encoded env value.
    :returns: decoded value.
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


def dedupe_list(lst: list):
    """
    Deduplicates a list while preserving the original order. Useful for
    deduplicating paths.

    :param lst: The list to deduplicate.
    :return: The deduplicated list.
    """
    return list(OrderedDict.fromkeys(lst))


def dict_diff(dict1: dict, dict2: dict):
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


def encode(env: dict):
    """Returns environment as a dict with str encoded key/values for passing to
    wrapper subprocesses.

    :param env: `Env` instance or os.environ.
    :param resolved: fully resolve values (default=True).
    :returns: dict with bytestring key/values.
    """
    c = lambda v: str(v)
    return dict((c(k), c(v)) for k, v in env.items())


def get_paths_from_var(
    var: str = "PYTHONPATH", pathsep: str = os.pathsep, reverse: bool = True
):
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


def get_stack_name(name: str = config.DEFAULT_NAMESPACE):
    """
    Returns the stack name as a string. The stack name is always the last
    element in the stack list or the basename of the envstack file.

    :param name: The input name, can be a string, tuple, or list.
    :return: The stack name as a string.
    """
    if isinstance(name, (tuple, list)):
        name = str(name[-1]) if name else config.DEFAULT_NAMESPACE
    if isinstance(name, str):
        return os.path.splitext(os.path.basename(name))[0]
    else:
        raise ValueError("Invalid input type. Expected string, tuple, or list.")


def evaluate_modifiers(expression: str, environ: dict = os.environ):
    """
    Evaluates Bash-like variable expansion modifiers.

    Supports:
    - values like "world" (no substitution)
    - ${VAR} for direct substitution (empty string if unset)
    - ${VAR:=default} to set and use a default value if unset
    - ${VAR:?error message} to raise an error if the variable is unset or null

    :param expression: The Bash-like string, e.g.,
        "${VAR:=default}/path", "${VAR}/path", or "${VAR:?error message}"
    :return: The resulting evaluated string with all substitutions applied.
    :raises CyclicalReference: If a cyclical reference is detected.
    :raises ValueError: If a variable is undefined and has the :? syntax with an
        error message.
    """

    def substitute_variable(match):
        """Substitute a variable match with its value."""
        var_name = match.group(1)
        operator = match.group(2)
        argument = match.group(3)
        override = os.getenv(var_name, null)
        value = environ.get(var_name, override)
        varstr = "${%s}" % var_name

        # check for self-referential values
        is_recursive = value and varstr in value

        # handle recursive references
        if is_recursive and override:
            value = value.replace(varstr, override)
        else:
            value = value.replace(varstr, "")

        if operator == "=":
            if override:
                value = override
            elif variable_pattern.search(value) or value is None:
                value = evaluate_modifiers(argument, environ)
            else:
                value = value or argument
        elif operator == "?":
            if not value:
                error_message = argument if argument else f"{var_name} is not set"
                raise ValueError(error_message)
        elif variable_pattern.search(value):
            value = evaluate_modifiers(value, environ)
        # handle simple ${VAR} substitution
        elif operator is None:
            value = value or ""

        return value

    try:
        # substitute all matches in the expression
        result = variable_pattern.sub(substitute_variable, expression)

        # dedupe paths and convert to platform-specific path separators
        if ":" in result:
            result = os.pathsep.join(dedupe_list(result.split(":")))

    # detect recursion errors
    except RecursionError:
        raise CyclicalReference(f"Cyclical reference detected in {expression}")

    # evaluate list elements
    except TypeError:
        if isinstance(expression, list):
            result = [
                variable_pattern.sub(substitute_variable, str(v))
                if isinstance(v, str)
                else v
                for v in expression
            ]
        elif isinstance(expression, dict):
            result = {
                k: variable_pattern.sub(substitute_variable, str(v))
                if isinstance(v, str)
                else v
                for k, v in expression.items()
            }
        else:
            result = expression

    return result


def load_sys_path(
    var: str = "PYTHONPATH", pathsep: str = os.pathsep, reverse: bool = True
):
    """
    Add paths from the given environment variable to sys.path.

    :param var: The environment variable to add paths from.
    :param pathsep: The path separator to use.
    :param reverse: Reverse the order of the paths.
    """
    for path in get_paths_from_var(var, pathsep, reverse):
        if path and path not in sys.path:
            sys.path.insert(0, path)


def safe_eval(value: str):
    """
    Returns template value preserving original class. Useful for preserving
    nested values in wrappers. For example, a value of "1.0" returns 1.0, and a
    value of "['a', 'b']" returns ['a', 'b'].

    :param value: value to evaluate.
    :returns: evaluated value.
    """
    try:
        from ast import literal_eval

        eval_func = literal_eval
    except ImportError:
        # warning: security issue
        eval_func = eval

    if type(value) == str:
        try:
            return eval_func(value)
        except Exception:
            try:
                return eval_func(decode_value(value))
            except Exception:
                return value

    return value


def get_stacks():
    """
    Returns a list of all stack names found in the environment paths.
    """
    import glob

    paths = get_paths_from_var("ENVPATH")
    stacks = set()

    for path in paths:
        env_files = glob.glob(os.path.join(path, "*.env"))
        for env_file in env_files:
            file_name = os.path.basename(env_file)
            stack_name = os.path.splitext(file_name)[0]
            stacks.add(stack_name)

    return sorted(list(stacks))


def findenv(var_name):
    """
    Returns a list of paths where the given environment var is set.

    :param var_name: The environment variable to search for.
    :returns: A list of paths where the variable is set.
    """
    from envstack.env import trace_var

    paths = set()

    stacks = get_stacks()

    for stack in stacks:
        path = trace_var(stack, var=var_name)
        if path and os.path.exists(path):
            paths.add(path)

    return sorted(list(paths))


def print_error(file_path: str, e: Exception):
    """
    Prints the problematic line and a few surrounding lines for context.

    :param file_path: Path to the file.
    :param e: The exception.
    """
    try:
        with open(file_path, "r") as file:
            lines = file.readlines()
            if hasattr(e, "problem_mark") and e.problem_mark:
                line_num = e.problem_mark.line - 1
                # problematic line and a few surrounding lines for context
                start = max(0, line_num - 1)
                end = min(len(lines), line_num + 2)
                for i in range(start, end):
                    prefix = ">> " if i == line_num else "   "
                    print(f"{prefix}{i + 1}: {lines[i].rstrip()}")
    except Exception as ex:
        print("read error:", ex)


def validate_yaml(file_path: str):
    """
    Loads a YAML file and prints helpful error hints if invalid.

    :param file_path: Path to the YAML file to validate.
    """
    import yaml

    required_keys = {"all", "darwin", "linux", "windows"}

    try:
        with open(file_path, "r") as stream:
            data = yaml.safe_load(stream.read())

        if not isinstance(data, dict):
            raise yaml.YAMLError("invalid data structure")

        missing_keys = required_keys - data.keys()
        if missing_keys:
            raise yaml.YAMLError(f"missing keys: {', '.join(sorted(missing_keys))}")

        return data

    except yaml.YAMLError as e:
        if hasattr(e, "problem_mark") and e.problem_mark:
            mark = e.problem_mark
            print(f'  File "{file_path}" line {mark.line}, column {mark.column}:')
        print_error(file_path, e)
        if hasattr(e, "problem") and e.problem:
            print(f"SyntaxError: {e.problem}")
        else:
            print(f'  File "{file_path}":')
            print(f"SyntaxError: {e}")

    return {}
