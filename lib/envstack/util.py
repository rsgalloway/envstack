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

__doc__ = """
Contains common utility functions and classes.
"""

import functools
import glob
import os
import re
import sys
import time
from ast import literal_eval
from collections import OrderedDict

import yaml

from envstack import config
from envstack.exceptions import CyclicalReference
from envstack.node import AESGCMNode, Base64Node, EncryptedNode, FernetNode

# default memoization cache timeout in seconds
CACHE_TIMEOUT = 5

# value for unresolvable variables
null = ""

# regular expression pattern for matching windows drive letters
# TODO: support lowercase drive letters (issue #53)
drive_letter_pattern = re.compile(r"(?P<sep>[:;])?(?P<drive>[A-Z]:[/\\])")

# regular expression pattern for bash-like variable expansion
variable_pattern = re.compile(
    r"\$\{([a-zA-Z_][a-zA-Z0-9_]*)(?::([-=?])((?:\$\{[^}]+\}|[^}])*))?\}"
)


def cache(func):
    """Function decorator to memoize return data."""

    cache_dict = {}

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        key = (args, tuple(kwargs.items()))
        if key in cache_dict:
            result, timestamp = cache_dict[key]
            if time.time() - timestamp <= CACHE_TIMEOUT:
                return result
        result = func(*args, **kwargs)
        cache_dict[key] = (result, time.time())
        return result

    return wrapper


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

    Decoding encoded environments can be tricky. For example, it must account
    for path templates that include curly braces, e.g. path templates string
    like this must be preserved:

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
    :returns: The deduplicated list.
    """
    return list(OrderedDict.fromkeys(lst))


def split_posix_paths(path_str: str):
    """
    Splits a path string using the posix path separator.

    :param path_str: The input path string.
    :returns: The split path list.
    """
    return [p.strip() for p in path_str.split(":") if p.strip()]


def split_windows_paths(path_str: str):
    """
    Splits a windows-style path string that may contain a mix of colon and
    semicolon delimiters, while preserving drive letter patterns. Drive letters
    must be uppercase.

    Example:
      Input:  "C:\\Program Files\\Python:D:/path2:E:/path3:/usr/local/bin"
      Output: ['C:\\Program Files\\Python', 'D:/path2', 'E:/path3', '/usr/local/bin']

    :param path_str: The input path string.
    :returns: The split path list.
    """
    result = []
    tokens = [p.strip() for p in path_str.split(";") if p.strip()]

    for token in tokens:
        # token is windows-style, insert a marker before drive letters
        # TODO: support lowercase drive letters
        if re.match(r"^[A-Z]:[/\\]", token) or "\\" in token:
            modified = drive_letter_pattern.sub(lambda m: "|" + m.group("drive"), token)
            # split on the marker, then on colons that are not in drive-letters
            result += [
                p
                for part in modified.split("|")
                for p in re.split(
                    r"(?<![A-Z]):", part
                )  # capture colons not in drive letters
                if p
            ]
        else:
            result += split_posix_paths(token)

    return result


def split_paths(path_str: str, platform: str = config.PLATFORM):
    """
    Splits a path string using the platform-specific path separator.

    :param path_str: The input path string.
    :param platform: The platform to use.
    :returns: The split path list.
    """
    if platform == "windows":
        return split_windows_paths(path_str)
    else:
        return split_posix_paths(path_str)


def dedupe_paths(path_str: str, platform: str = config.PLATFORM):
    """
    Deduplicates paths from a colon-separated string.

    :param path_str: The input path string.
    :platform: The platform to use.
    :returns: The deduplicated path string.
    """
    deduped = dedupe_list(split_paths(path_str, platform))
    joiner = ";" if platform == "windows" else ":"
    return joiner.join(deduped)


def detect_path(s: str):
    """
    Returns True if the given string looks like a filesystem path,
    and False if it appears to be a URL or not a path.

    This heuristic checks:
      - That the string does not start with a URL scheme
      - Windows drive letters or UNC paths
      - POSIX absolute paths (starting with '/')
      - Relative paths if they contain path separators or a file extension marker.

    Note: Some valid file names (like "README") may be ambiguous.

    :param s: The input string.
    :returns: True if the string looks like a filesystem path.
    """
    s = s.strip()
    if not s:
        return False

    # exclude URL-like strings (scheme://...)
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", s):
        return False

    # windows: drive-letter (absolute or relative) or UNC path
    if re.match(r"^[a-zA-Z]:", s) or s.startswith(r"\\\\"):
        return True

    # posix: absolute path starting with "/"
    if s.startswith("/"):
        return True

    # check for delimiter-separated paths
    if ";" in s or (":" in s and s.count(":") > 1):
        return True

    # check if the string contains a directory separator
    if "/" in s or r"\\" in s:
        return True

    # check if the string has a dot (likely indicating a file extension)
    # if re.search(r"(?<!^)\.", s):
    #     return True

    return False


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
    c = lambda v: str(v)  # noqa: E731
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


def evaluate_modifiers(expression: str, environ: dict = os.environ, parent: dict = {}):
    """
    Evaluates Bash-like variable expansion modifiers in a string, resolves
    custom node types, and evaluates lists and dictionaries.

    Supported modifiers:
       - values like "world" (no substitution)
       - ${VAR} for direct substitution (empty string if unset)
       - ${VAR:=default} to set and use a default value if unset
       - ${VAR:?error message} to raise an error if the variable is unset

    :param expression: The bash-like string to evaluate.
    :param environ: The environment dictionary to use for variable substitution.
    :param parent: The parent environment dictionary to use for variable substitution.
    :return: The resulting evaluated string with all substitutions applied.
    :raises CyclicalReference: If a cyclical reference is detected.
    :raises ValueError: If a variable is undefined and has the :? syntax with an
        error message.
    """

    def sanitize_value(value):
        """Sanitize the value before returning it."""
        # HACK: remove trailing curly braces if they exist
        if type(value) is str and value.endswith("}") and not value.startswith("${"):
            return value.rstrip("}")
        # sanitize and de-dupe path-like values
        elif type(value) is str and detect_path(value):
            return dedupe_paths(value)
        return value

    def substitute_variable(match):
        """Substitute a variable match with its value."""
        var_name = match.group(1)
        operator = match.group(2)
        argument = match.group(3)
        parent_value = parent.get(var_name, null)
        override = os.getenv(var_name, parent_value)
        value = str(environ.get(var_name, parent_value))
        varstr = "${%s}" % var_name

        # check for self-referential values, e.g. FOO: ${FOO}
        is_recursive = value and varstr in value
        if is_recursive and override:
            value = value.replace(varstr, override)
        else:
            value = value.replace(varstr, null)

        # ${VAR:=default} or ${VAR:-default}
        if operator in ("=", "-"):
            # get value from os.environ first
            if override:
                value = override
            # then from the included (parent) environment
            elif parent_value:
                value = parent_value
            # then look for a value in this environment
            elif variable_pattern.search(value):
                value = evaluate_modifiers(argument, environ, parent)
            # finally, use the default value
            else:
                value = value or argument

        # ${VAR:?error message}
        elif operator == "?":
            if not value:
                error_message = argument if argument else f"{var_name} is not set"
                raise ValueError(error_message)

        # handle recursive references
        elif variable_pattern.search(value):
            value = evaluate_modifiers(value, environ, parent)

        # handle simple ${VAR} substitution
        elif operator is None:
            value = value or override

        return value

    try:
        # substitute all matches in the expression
        result = variable_pattern.sub(substitute_variable, expression)

        # evaluate any remaining modifiers, eg. ${VAR:=${FOO:=bar}}
        if variable_pattern.search(result):
            result = evaluate_modifiers(result, environ)

    # detect recursion errors, cycles are not errors
    except RecursionError:
        result = null
        # TODO: remove in next version (cycles are not errors)
        raise CyclicalReference(f"Cyclical reference detected in {expression}")

    # evaluate other data types
    # TODO: find a better way to evaluate other data types
    except TypeError:
        if isinstance(expression, AESGCMNode):
            result = expression.resolve(env=environ)
        elif isinstance(expression, Base64Node):
            result = expression.resolve(env=environ)
        elif isinstance(expression, EncryptedNode):
            result = expression.resolve(env=environ)
        elif isinstance(expression, FernetNode):
            result = expression.resolve(env=environ)
        elif isinstance(expression, list):
            result = [(evaluate_modifiers(v, environ)) for v in expression]
        elif isinstance(expression, dict):
            result = {
                k: (evaluate_modifiers(v, environ)) for k, v in expression.items()
            }
        else:
            result = expression

    return sanitize_value(result)


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
        eval_func = literal_eval
    except ImportError:
        # warning: security issue
        eval_func = eval

    if type(value) is str:
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
    paths = get_paths_from_var("ENVPATH")
    stacks = set()

    for path in paths:
        env_files = glob.glob(os.path.join(path, "*.env"))
        for env_file in env_files:
            file_name = os.path.basename(env_file)
            stack_name = os.path.splitext(file_name)[0]
            stacks.add(stack_name)

    return sorted(list(stacks))


def findenv(var_name: str):
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
    required_keys = {"all", "darwin", "linux", "windows"}

    try:
        with open(file_path, "r") as stream:
            data = yaml.safe_load(stream.read())
            # data = yaml.load(stream.read(), Loader=CustomLoader)
        if not isinstance(data, dict):
            raise yaml.YAMLError("invalid data structure")
        missing_keys = required_keys - data.keys()
        if missing_keys:
            raise yaml.YAMLError(f"missing keys: {', '.join(sorted(missing_keys))}")
        return data
    except OSError as e:
        print(e)
    except yaml.YAMLError as e:
        if hasattr(e, "problem_mark") and e.problem_mark:
            mark = e.problem_mark
            print(f'  File "{file_path}" line {mark.line + 1}, column {mark.column}:')
        print_error(file_path, e)
        if hasattr(e, "problem") and e.problem:
            print(f"SyntaxError: {e.problem}")
        else:
            print(f'  File "{file_path}":')
            print(f"SyntaxError: {e}")

    return {}


def unquote_strings(file_path: str):
    """
    Unquotes all the single quote strings in a given file.

    :param file_path: Path to the file.
    """
    with open(file_path, "r") as file:
        content = file.read()

    updated_content = re.sub(r"'([^']*)'", r"\1", content)

    with open(file_path, "w") as file:
        file.write(updated_content)


def dump_yaml(file_path: str, data: dict, unquote: bool = True):
    """
    Dumps a dictionary to a YAML file with custom formatting:

    - unquotes single quoted strings
    - partitions platform data
    - adds a shebang line to make the file executable
    - adds an include line if it exists in the data

    :param file_path: Path to the output YAML file.
    :param data: The dictionary to dump.
    :param unquote: Unquote single quoted strings.
    """
    from envstack.node import CustomDumper, yaml

    partitioned_data = partition_platform_data(data)

    # write the platform partidioned data add shebang
    with open(file_path, "w") as file:
        file.write("#!/usr/bin/env envstack\n")
        if data.get("include"):
            file.write(f"include: {data['include']}\n")
        else:
            file.write("include: []\n")
        if "include" in partitioned_data:
            del partitioned_data["include"]
        yaml.dump(
            partitioned_data,
            file,
            Dumper=CustomDumper,
            sort_keys=True,
            default_flow_style=False,
        )

    if os.path.exists(file_path):
        # unquote the merge keys because yaml doesn't like them quoted
        if unquote:
            unquote_strings(file_path)

        # make the env stack file executable
        try:
            os.chmod(file_path, 0o755)
        except Exception:
            pass


def partition_platform_data(data: dict):
    """
    Given a data dictionary with keys 'all', 'darwin', 'linux', 'windows',
    this function finds which key-value pairs are common across all platforms,
    and which are unique to each platform. Platform-specific values go in their
    respective dicts.

    :param data: dictionary to partition.
    :returns: platform partitioned dictionary.
    """
    # ensure "all" key is present
    if "all" not in data:
        data["all"] = dict((k, v) for k, v in data.items() if k != "include")

    # platforms of interest (darwin, linux, windows)
    platforms = ["darwin", "linux", "windows"]

    # get the union of keys from all platforms
    all_platform_keys = set()
    for p in platforms:
        all_platform_keys |= data.get(p, {}).keys()

    # determine which keys are common to all platforms
    common_keys = []
    for key in all_platform_keys:
        if all(key in data[p] for p in platforms):
            # get first value for comparison later
            first_value = data[platforms[0]][key]
            # call it common if all platforms have the same value
            if all(data[p][key] == first_value for p in platforms):
                common_keys.append(key)

    # build a new all dict for common items
    new_all = {"<<": "*all"}  # avoids syntax errors when no vars are present
    for k in common_keys:
        if k in data["all"]:
            new_all[k] = data["all"][k]
        else:
            new_all[k] = data[platforms[0]][k]

    # keep in all anything that is platform-agnostic
    for k, v in data["all"].items():
        if k not in all_platform_keys:
            new_all[k] = v

    # build dicts for each platform with only platform‑specific keys
    new_platform_dicts = {}
    for p in platforms:
        new_platform_dicts[p] = {"<<": "*all"}
        for k, v in data.get(p, {}).items():
            if k not in common_keys:
                new_platform_dicts[p][k] = v

    # combine with platform-specific dicts
    new_data = {"all": new_all}
    for p in platforms:
        new_data[p] = new_platform_dicts[p]

    # ensure include is present
    if data.get("include"):
        new_data["include"] = data["include"]
    else:
        new_data["include"] = []

    return new_data
