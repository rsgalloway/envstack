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
Contains functions and classes for processing scoped .env files.
"""

import os
import re
import string
from pathlib import Path

from envstack import config, logger, path, util
from envstack.exceptions import *

# value delimiter pattern (splits values by colons or semicolons)
delimiter_pattern = re.compile("(?![^{]*})[;:]+")

# stores cached file data in memory
load_file_cache = {}

# value for unresolvable variables
null = ""

# stores the original environment
SAVED_ENVIRONMENT = None


class EnvVar(string.Template, str):
    """A string class for supporting $-substitutions, e.g.: ::

    >>> v = EnvVar('$FOO:${BAR}')
    >>> v.substitute(FOO='foo', BAR='bar')
    'foo:bar'
    """

    def __init__(self, template=null):
        super(EnvVar, self).__init__(template)

    def __eq__(self, other):
        if isinstance(other, EnvVar):
            return self.template == other.template
        return self.template == other

    def __iter__(self):
        return iter(self.parts())

    def __getitem__(self, key):
        return EnvVar(self.value().__getitem__(key))

    def __setitem__(self, key, value):
        v = self.value()
        v.__setitem__(key, value)
        self.template = v

    def append(self, value):
        """If value is a list, append object to the end of the list.

        :param value: value to append
        """
        v = self.value()
        v.append(value)
        self.template = v

    def extend(self, iterable):
        """If value is a list, extend list by appending elements from the iterable.

        :param iterable: an iterable object
        :returns: extended value
        """
        v = self.value()
        v.extend(iterable)
        self.template = v

    def expand(self, env=None, recursive=False):
        """Returns expanded value of this var as new EnvVar instance.

        :env: Env instance object or key/value dict
        :returns: expanded EnvVar instance
        """
        env = env or os.environ

        try:
            val = EnvVar(self.safe_substitute(env, **os.environ))
        except RuntimeError as err:
            if "maximum recursion depth exceeded" in str(err):
                raise CyclicalReference(self.template)
            else:
                raise InvalidSyntax(err)
        except Exception:
            val = EnvVar(self.template)

        if recursive:
            if type(val.value()) == list:
                ret = []
                for v in val.value():
                    ret.append(EnvVar(v).expand(env, recursive))
                return ret

            elif type(val.value()) == dict:
                ret = {}
                for k, v in val.value().items():
                    ret[k] = EnvVar(v).expand(env, recursive)
                return ret

            elif val.parts():
                return val.expand(env, recursive=False)

            else:
                return val

        else:
            return val

    def get(self, key, default=None):
        """EnvVar.get(k[,d]) -> EnvVar[k] if k in EnvVar and EnvVar[k]
        is a dict, else d.
        """
        try:
            return self[key]
        except (KeyError, TypeError):
            return default

    def items(self):
        """Returns list of (key, value) pairs as 2-tuples if
        the value of this EnvVar is a dict.
        """
        template = safe_eval(self.template)
        if not isinstance(template, dict):
            raise TypeError(type(template), template)
        return [(k, EnvVar(v).value()) for k, v in template.items()]

    def keys(self):
        """Returns EnvVar.keys() if the value of this EnvVar is a dict."""
        if not isinstance(self.template, dict):
            raise TypeError
        return self.template.keys()

    def parts(self):
        """Returns a list of delimited parts, e.g. if a value is delimited by a colon
        (or semicolon on windows), e.g. ::

        >>> v = EnvVar('$FOO:${BAR}/bin')
        >>> v.parts()
        ['$FOO', '${BAR}/bin']
        """
        if self.template:
            if type(self.template) in (
                str,
                bytes,
            ):
                return delimiter_pattern.split(self.template)
            return self.template
        return []

    def value(self):
        """Returns EnvVar value."""
        return safe_eval(self.template)

    def vars(self):
        """Returns a list of embedded, named variables, e.g.: ::

        >>> v = EnvVar('$FOO:${BAR}/bin')
        >>> v.vars()
        ['FOO', 'BAR']
        """
        matches = super(EnvVar, self).pattern.findall(str(self.template))
        return [key for match in matches for key in match if key]


class Env(dict):
    """Dict subclass that auto-expands embedded variables.

    >>> env = envstack.Env({
    ...     'BAR': '$FOO',
    ...     'BAZ': '$BAR'
    ... })
    >>> env['BAR']
    None
    >>> env.update({'FOO': 'bar'})
    >>> env['BAZ']
    bar
    >>> env.get('BAZ', resolved=False)
    '$BAR'
    """

    def __init__(self, *args, **kwargs):
        super(Env, self).__init__(*args, **kwargs)
        self.scope = os.getcwd()

    def __getitem__(self, key):
        """Returns expanded value of key."""
        if key not in self.keys():
            raise KeyError(key)
        try:
            value = self.__get(key)
            if key in value.vars():
                return value
            return value.expand(self).value()
        except CyclicalReference:
            return value
        except InvalidSyntax:
            return EnvVar()

    def __get(self, key, default=null):
        """Returns unexpanded values of key. Same as dict.get(k[,d]) where k is the
        key, and d is a default value."""
        return EnvVar(super(Env, self).get(key, default))

    def copy(self):
        """Returns a copy of this Env."""
        return Env(super(Env, self).copy())

    def get(self, key, default=null, resolved=True):
        """Returns expanded or raw unexpanded value of key, or a given default value.

        :param key: return value of this key
        :param default: default value if key not present
        :param resolved: return expanded values
        """
        if key not in self:
            return default
        value = self.__get(key, default)
        if key in value.vars():
            return value
        if resolved:
            try:
                return value.expand(self).value()
            except CyclicalReference:
                return value
            except InvalidSyntax:
                return EnvVar()
        return value

    def get_raw(self, key):
        """Returns raw, unexpanded value of key, or None."""
        return self.get(key, resolved=False).template

    def merge(self, env):
        """Merges another env into this one, i.e. env[k] will replace self[k].

        :param env: env to merge into this one
        """
        for k, v in env.items():
            self[k] = v

    def set_namespace(self, name):
        """Stores the namespace for this environment.

        :param name: namespace
        """
        self.namespace = name

    def set_scope(self, path):
        """Stores the scope for this environment.

        :param path: path of scope
        """
        self.scope = path


class Scope(path.Path):
    """Scope class."""

    def __init__(self, path=None):
        """
        :param path: scope path (default is CWD)
        """
        self.path = path or os.getcwd()


class Source(object):
    """envstack .env source file."""

    def __init__(self, path):
        """
        :param path: path to .env file
        """
        self.path = path
        self.__data = {}

    def __eq__(self, other):
        if not isinstance(other, Source):
            return False
        return self.path == other.path

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.__repr__())

    def __repr__(self):
        return f'<Source "{self.path}">'

    def __str__(self):
        return self.path

    def exists(self):
        """Returns True if the .env file exists"""
        return os.path.exists(self.path)

    def includes(self):
        """Returns list of included environments, defined in
        .env files above the "all:" statment as:

            include: [name1, name2, ... nameN]
        """
        if not self.__data:
            self.load()
        return self.__data.get("include", [])

    def length(self):
        """Returns the char length of the path"""
        return len(self.path)

    def load(self, platform=config.PLATFORM):
        """Reads .env from .path, and returns an Env class object"""
        if self.path and not self.__data:
            self.__data = load_file(self.path)
        return self.__data.get(platform, self.__data.get("all", {}))


def clear_file_cache():
    """Clears global file memory cache."""
    global load_file_cache
    load_file_cache = {}


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


def get_sources(*names: str, scope: str = None):
    """
    Find .env files recursively based on includes, avoiding cyclic dependencies.

    Args:
        *names (str): A variable-length list of .env file names to search for.
        scope (str): A filesystem path defining the scope to walk up to.
                     Defaults to the current working directory.

    Returns:
        List[Path]: A list of resolved `.env` file paths in the order they are loaded.
    """
    clear_file_cache()

    # set default scope to the current working directory
    scope = Path(scope or os.getcwd()).resolve()

    loaded_files = []
    sources = []
    loading_stack = set()

    def _walk_to_scope(current_path):
        """Generate directories from the current path up to the scope."""
        paths = []
        while current_path != scope.parent:
            paths.append(current_path)
            if current_path == scope:
                break
            current_path = current_path.parent
        return [str(p) for p in paths]

    # construct search paths from $ENVPATH and current scope
    envpath = os.environ.get("ENVPATH", "")
    envpath_dirs = [Path(p).resolve() for p in envpath.split(":") if p.strip()]
    scope_dirs = _walk_to_scope(scope)
    envpath_dirs.reverse()
    search_paths = envpath_dirs + scope_dirs

    def _find_files(file_basename):
        if not file_basename.endswith(".env"):
            file_basename += ".env"
        found_files = []
        for directory in search_paths:
            potential_file = Path(directory) / file_basename
            if potential_file.exists():
                found_files.append(potential_file)
        if not found_files and not config.IGNORE_MISSING:
            raise FileNotFoundError(f"{file_basename} not found in ENVPATH or scope.")
        return found_files

    def _load_file(file_basename):
        file_paths = _find_files(file_basename)

        # process each file independently
        for file_path in file_paths:
            if file_path in loaded_files:
                continue

            if file_basename in loading_stack:
                raise ValueError(f"Cyclic dependency detected in {file_basename}")

            source = Source(file_path)
            loading_stack.add(file_basename)

            # parse included files recursively
            for include_basename in source.includes():
                _load_file(include_basename)

            # add current file to the loaded list after processing includes
            loaded_files.append(file_path)
            sources.append(source)
            loading_stack.remove(file_basename)

    # process each stack in the list
    for name in names:
        if not name.endswith(".env"):
            name += ".env"
        _load_file(name)

    return sources


def expandvars(var, env=None, recursive=False):
    """Expands variables in a given string for a given environment,
    e.g.: if env = {'ROOT':'/projects'}

        >>> envstack.expandvars('$ROOT/a/b/c', env)
        /projects/a/b/c

    :param var: a string with embedded variables.
    :param env: Env (defaults to default environ).
    :param recursive: revursively expand values.
    :returns: expanded value from values in env.
    """
    var = EnvVar(var).expand(env, recursive=recursive)
    return util.evaluate_modifiers(var, os.environ)


def clear(
    name=config.DEFAULT_NAMESPACE,
    shell=config.SHELL,
    scope=None,
):
    """Returns shell commands that can be sourced to unset or restore env stack
    environment variables. Should only be run after a previous export:

        $ source <(envstack --export)
        $ source <(envstack --clear)

    List of shell names: bash, sh, tcsh, cmd, pwsh
    (see output of config.detect_shell()).

    :param name: stack namespace.
    :param shell: name of shell (default: current shell).
    :param scope: environment scope (default: cwd).
    :returns: shell commands as string.
    """
    env = load_environ(name, scope=scope)
    export_vars = dict(env.items())
    export_list = list()

    # vars that should never be unset
    restricted_vars = ["PATH", "PS1", "PWD", "PROMPT", "DEFAULT_ENV_DIR"]

    for key in export_vars:
        if key not in os.environ:
            continue
        old_key = f"_ES_OLD_{key}"
        old_val = os.environ.get(old_key)
        if shell in ["bash", "sh", "zsh"]:
            if old_val:
                export_list.append("export %s=%s" % (key, old_val))
                export_list.append("unset %s" % (old_key))
            elif key not in restricted_vars:
                export_list.append(f"unset {key}")
        elif shell == "tcsh":
            if old_val:
                export_list.append(f"setenv {key} {old_val}")
                export_list.append(f"unsetenv {old_key}")
            elif key not in restricted_vars:
                export_list.append(f"unsetenv {key}")
        elif shell == "cmd":
            if old_val:
                export_list.append(f"set {key}={old_val}")
                export_list.append(f"set {old_key}=")
            elif key not in restricted_vars:
                export_list.append(f"set {key}=")
        elif shell == "pwsh":
            if old_val:
                export_list.append(f"$env:{key}='{old_val}'")
                export_list.append(f"Remove-Item Env:{old_key}")
            elif key not in restricted_vars:
                export_list.append(f"Remove-Item Env:{key}")
        elif shell == "unknown":
            raise Exception("unknown shell")

    export_list.sort()
    exp = "\n".join(export_list)

    return exp


def export(
    name=config.DEFAULT_NAMESPACE,
    shell=config.SHELL,
    scope=None,
):
    """Returns shell set env commands that can be sourced to set env stack
    environment variables.

    List of shell names: bash, sh, tcsh, cmd, pwsh
    (see output of config.detect_shell()).

    :param name: stack namespace.
    :param shell: name of shell (default: current shell).
    :param scope: environment scope (default: cwd).
    :returns: shell commands as string.
    """
    env = load_environ(name, scope=scope)
    export_vars = dict(env.items())
    export_list = list()

    for key, val in export_vars.items():
        val = expandvars(val, env, recursive=False)
        old_key = f"_ES_OLD_{key}"
        old_val = os.environ.get(key)
        if key == "PATH" and not val:
            logger.log.warning("PATH is empty")
            continue
        if shell in ["bash", "sh", "zsh"]:
            export_list.append(f"export {key}={val}")
            if old_val:
                export_list.append(f"export {old_key}={old_val}")
        elif shell == "tcsh":
            export_list.append(f'setenv {key}:"{val}"')
            if old_val:
                export_list.append(f'setenv {old_key}:"{old_val}"')
        elif shell == "cmd":
            export_list.append(f'set {key}="{val}"')
            if old_val:
                export_list.append(f'set {old_key}="{old_val}"')
        elif shell == "pwsh":
            export_list.append(f'$env:{key}="{val}"')
            if old_val:
                export_list.append(f'$env:{old_key}="{old_val}"')
        elif shell == "unknown":
            raise Exception("unknown shell")

    export_list.sort()
    exp = "\n".join(export_list)

    return exp


def save():
    """Saves the current environment for later restoration."""
    global SAVED_ENVIRONMENT
    if not SAVED_ENVIRONMENT:
        SAVED_ENVIRONMENT = dict(os.environ.copy())
        return SAVED_ENVIRONMENT


def revert():
    """Reverts the environment to the saved environment. Updates sys.path using
    paths found in PYTHONPATH.

    Initialize the default environment stack:
    >>> envstack.init()

    Revert to the previous environment:
    >>> envstack.revert()
    """
    global SAVED_ENVIRONMENT
    if SAVED_ENVIRONMENT is None:
        return

    # clear current sys.path values
    util.clear_sys_path()

    # restore the original environment
    os.environ.clear()
    os.environ.update(SAVED_ENVIRONMENT)

    # restore sys.path from PYTHONPATH
    util.load_sys_path()

    SAVED_ENVIRONMENT = None


def init(*name):
    """Initializes the environment from a given stack namespace. Environments
    propogate downwards with subsequent calls to init().

    Updates sys.path using paths found in PYTHONPATH.

    Initialize the default environment stack:
    >>> envstack.init()

    Initialize the 'dev' environment stack (inherits from previous call):
    >>> envstack.init('dev')

    Initialize both 'dev' and 'test', in that order:
    >>> envstack.init('dev', 'test')

    Revert to the original environment:
    >>> envstack.revert()

    :param *name: list of stack namespaces.
    """
    # save environment to restore later using envstack.revert()
    save()

    # clear old sys.path values
    util.clear_sys_path()

    # load the stack and update the environment
    env = load_environ(name)
    os.environ.update(encode(env))

    # update sys.path from PYTHONPATH
    util.load_sys_path()


def load_environ(
    name=config.DEFAULT_NAMESPACE,
    sources=None,
    platform=config.PLATFORM,
    scope=None,
):
    """Loads env stack data for a given name. Adds "STACK" key to environment,
    and sets the value to `name`.

    To load an environment for a given namespace, where the scope is the current
    working directory (cwd):

        >>> env = load_environ(name)

    To reload the same namespace for a different scope (different cwd):

        >>> env = load_environ(name, scope="/path/to/scope")

    :param name: namespace (basename of env files).
    :param sources: list of env files (optional).
    :param platform: name of platform (linux, darwin, windows).
    :param scope: environment scope (default: cwd).
    :returns: dict of environment variables.
    """
    if type(name) == str:
        name = [name]

    sources = get_sources(*name)

    # create the environment to be returned
    env = Env()
    env.set_namespace(name)
    if scope:
        env.set_scope(scope)

    # load env files first
    for source in sources:
        env.update(source.load(platform=platform))

    # add the current env stack name to the environment
    if not env.get("STACK"):
        env["STACK"] = name[-1] if isinstance(name, list) else name

    return env


def load_file(path: str):
    """Reads a given .env file and returns data as dict.

    :param path: path to envstack env file
    :returns: loaded yaml data as dict
    """

    if path in load_file_cache:
        return load_file_cache[path]

    data = {}

    if not os.path.exists(path):
        return data

    import yaml

    with open(path) as stream:
        try:
            data.update(yaml.safe_load(stream))
        except (TypeError, yaml.YAMLError) as exc:
            logger.log.error(exc)
            raise InvalidSource(path)
        except yaml.parser.ParserError as err:
            logger.log.error(err)
            raise InvalidSource(path)

    load_file_cache[path] = data

    return data


def merge(env, other, strict=False, platform=config.PLATFORM):
    """Merges values from other into env. For example, to merge values from
    the local environment into an env instance:

        >>> merge(env, os.environ)

    To merge values from env into the local environment:

        >>> merge(os.environ, env)

    :param env: source env
    :param other: env to merge
    :param strict: value from env takes precedence (default: False)
    :param platform: name of platform (linux, darwin, windows)
    :returns: merged env
    """
    merged = env.copy()
    for key, value in merged.items():
        varstr = "${%s}" % key
        # replace variables in other with values from env
        if key in other:
            # replace variables in value with values from other
            if varstr in str(value):
                value = re.sub(
                    r"\${(\w+)}",
                    lambda match: other.get(match.group(1), match.group(0)),
                    value,
                )
            elif not strict:
                value = other.get(key)
        else:
            value = str(value).replace(varstr, "")
        # replace colons with semicolons on windows
        if platform == "windows":
            result = re.sub(r"(?<!\b[A-Za-z]):", ";", str(value))
            value = result.rstrip(";")
        merged[key] = value
    return merged


def safe_eval(value):
    """
    Returns template value preserving original class. Useful for preserving
    nested values in wrappers. For example, a value of "1.0" returns 1.0, and a
    value of "['a', 'b']" returns ['a', 'b'].

    :param value: value to evaluate
    :returns: evaluated value
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


def trace_var(*name: str, var: str = None, scope: str = None):
    """Traces where a var is getting set for a given name.

    :param name: name of tool or executable
    :param var: environment variable to trace
    :param scope: environment scope (default: cwd)
    :returns: source path
    """
    sources = get_sources(*name, scope=scope)
    sources.reverse()
    for source in sources:
        data = load_file(source.path)
        env = data.get(config.PLATFORM, data.get("all", {}))
        if var in env:
            return source.path
        elif os.getenv(var):
            return "local environment"


# default stack environment
environ = load_environ(name=config.DEFAULT_NAMESPACE)


def getenv(key, default=None):
    """Replaces os.getenv, where the environment includes envstack
    declared variables.

    Get an environment variable, return None if it doesn't exist.
    The optional second argument can specify an alternate default.
    """
    return environ.get(key, default)
