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

# value delimiter pattern (splits values by os.pathsep)
delimiter_pattern = re.compile("(?![^{]*})[;:]+")

# stores cached file data in memory
load_file_cache = {}

# stores environment when calling envstack.save()
saved_environ = None


class EnvVar(string.Template, str):
    """A string class for supporting $-substitutions, e.g.: ::

    >>> v = EnvVar('$FOO:${BAR}')
    >>> v.substitute(FOO='foo', BAR='bar')
    'foo:bar'
    """

    def __init__(self, template: str = util.null):
        super(EnvVar, self).__init__(template)

    def __eq__(self, other):
        if isinstance(other, EnvVar):
            return self.template == other.template
        return self.template == other

    def __iter__(self):
        return iter(self.parts())

    def __getitem__(self, key: str):
        return EnvVar(self.value().__getitem__(key))

    def __setitem__(self, key: str, value: str):
        v = self.value()
        v.__setitem__(key, value)
        self.template = v

    def append(self, value: str):
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

    def expand(self, env: dict = os.environ, recursive: bool = True):
        """Returns expanded value of this var as new EnvVar instance.

        :env: Env instance object or key/value dict.
        :returns: expanded EnvVar instance.
        """
        try:
            val = EnvVar(self.safe_substitute(env))
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
        return self.template  # util.safe_eval(self.template)

    def vars(self):
        """Returns a list of embedded, named variables, e.g.: ::

        >>> v = EnvVar('$FOO:${BAR}/bin')
        >>> v.vars()
        ['FOO', 'BAR']
        """
        matches = super(EnvVar, self).pattern.findall(str(self.template))
        return [key for match in matches for key in match if key]


class Env(dict):
    """Dictionary subclass for managing environments.

    >>> env = Env({"BAR": "${FOO}", "FOO": "foo"})
    >>> resolve_environ(env)
    {'BAR': 'foo', 'FOO': 'foo'}
    """

    def __init__(self, *args, **kwargs):
        super(Env, self).__init__(*args, **kwargs)
        self.scope = os.getcwd()

    def copy(self):
        """Returns a copy of this Env."""
        return Env(super(Env, self).copy())

    def merge(self, env: dict):
        """Merges another env into this one, i.e. env[k] will replace self[k].

        :param env: env to merge into this one.
        """
        for k, v in env.items():
            self[k] = v

    def set_namespace(self, name: str):
        """Stores the namespace for this environment.

        :param name: namespace.
        """
        self.namespace = name

    def set_scope(self, path: str):
        """Stores the scope for this environment.

        :param path: path of scope.
        """
        self.scope = path


class Scope(path.Path):
    """Scope class."""

    def __init__(self, path: str = None):
        """
        :param path: scope path (default is CWD)
        """
        self.path = path or os.getcwd()


class Source(object):
    """envstack .env source file."""

    def __init__(self, path):
        """
        :param path: path to .env file.
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
    """Clears global file cache."""
    global load_file_cache
    load_file_cache = {}


def get_sources(
    *names, scope: str = None, ignore_missing: bool = config.IGNORE_MISSING
):
    """
    Returns a list of Source objects for a given list of .env basenames.

    :param names: list of .env file names to search for.
    :param scope: filesystem path defining the scope to walk up to.
    :raises TemplateNotFound: if a file is not found in ENVPATH or scope.
    :returns: list of Source objects.
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
        if not found_files and not ignore_missing:
            raise TemplateNotFound(f"{file_basename} not found in ENVPATH or scope.")
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


def expandvars(var: str, env: Env = None, recursive: bool = False):
    """Expands variables in a given string for a given environment,
    e.g.: if env = {'ROOT':'/projects'}

        >>> envstack.expandvars('$ROOT/a/b/c', env)
        /projects/a/b/c

    :param var: a string with embedded variables.
    :param env: Env (defaults to default environ).
    :param recursive: revursively expand values.
    :returns: expanded value from values in env.
    """
    if not env:
        env = Env()
    var = EnvVar(var).expand(env, recursive=recursive)
    return util.evaluate_modifiers(var, os.environ)


def clear(
    name: str = config.DEFAULT_NAMESPACE,
    shell: str = config.SHELL,
    scope: str = None,
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
    export_list = list()
    restricted = ["PATH", "PS1", "PWD", "PROMPT"]

    for key in env:
        if key not in os.environ:
            continue
        old_key = f"_ES_OLD_{key}"
        old_val = os.environ.get(old_key)
        if shell in ["bash", "sh", "zsh"]:
            if old_val:
                export_list.append("export %s=%s" % (key, old_val))
                export_list.append("unset %s" % (old_key))
            elif key not in restricted:
                export_list.append(f"unset {key}")
        elif shell == "tcsh":
            if old_val:
                export_list.append(f"setenv {key} {old_val}")
                export_list.append(f"unsetenv {old_key}")
            elif key not in restricted:
                export_list.append(f"unsetenv {key}")
        elif shell == "cmd":
            if old_val:
                export_list.append(f"set {key}={old_val}")
                export_list.append(f"set {old_key}=")
            elif key not in restricted:
                export_list.append(f"set {key}=")
        elif shell == "pwsh":
            if old_val:
                export_list.append(f"$env:{key}='{old_val}'")
                export_list.append(f"Remove-Item Env:{old_key}")
            elif key not in restricted:
                export_list.append(f"Remove-Item Env:{key}")
        elif shell == "unknown":
            raise Exception("unknown shell")

    export_list.sort()
    exp = "\n".join(export_list)

    return exp


def export(
    name: str = config.DEFAULT_NAMESPACE,
    shell: str = config.SHELL,
    scope: str = None,
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

    # resolve environment variables
    resolved_env = resolve_environ(load_environ(name, scope=scope))

    # track the environment variables to export
    export_list = list()

    for key, val in resolved_env.items():
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

    global saved_environ

    if not saved_environ:
        saved_environ = dict(os.environ.copy())
        return saved_environ


def revert():
    """Reverts the environment to the saved environment. Updates sys.path using
    paths found in PYTHONPATH.

    Initialize the default environment stack:

        >>> envstack.init()

    Revert to the previous environment:

        >>> envstack.revert()
    """

    global saved_environ

    if saved_environ is None:
        return

    # clear current sys.path values
    util.clear_sys_path()

    # restore the original environment
    os.environ.clear()
    os.environ.update(saved_environ)

    # restore sys.path from PYTHONPATH
    util.load_sys_path()

    saved_environ = None


def init(*name, ignore_missing: bool = config.IGNORE_MISSING):
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
    :param ignore_missing: ignore missing .env files.
    """

    # save environment to restore later using envstack.revert()
    save()

    # clear old sys.path values
    util.clear_sys_path()

    # load the stack and update the environment
    env = resolve_environ(load_environ(name, ignore_missing=ignore_missing))
    os.environ.update(util.encode(env))

    # update sys.path from PYTHONPATH
    util.load_sys_path()


def resolve_environ(env: dict):
    """Resolves all variables in a given unresolved environment, returning a
    new environment dict.

    :param env: unresolved environment.
    :returns: resolved environment.
    """
    resolved = Env()

    for key, value in env.items():
        evaluated_value = util.evaluate_modifiers(value, env)
        resolved[key] = evaluated_value

    return resolved


def load_environ(
    name: str = config.DEFAULT_NAMESPACE,
    sources: list = None,
    platform: str = config.PLATFORM,
    scope: str = None,
    ignore_missing: bool = config.IGNORE_MISSING,
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
    :param ignore_missing: ignore missing .env files.
    :returns: dict of environment variables.
    """
    if type(name) == str:
        name = [name]

    if not name:
        name = [config.DEFAULT_NAMESPACE]

    # get the sources for the given stack(s)
    sources = get_sources(*name, scope=scope, ignore_missing=ignore_missing)

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
        env["STACK"] = util.get_stack_name(name)

    return env


def load_file(path: str):
    """Reads a given .env file and returns data as dict.

    :param path: path to envstack env file.
    :returns: loaded yaml data as dict.
    """

    global load_file_cache

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


def trace_var(*name, var: str = None, scope: str = None):
    """Traces where a var is getting set for a given name.

    :param name: name of tool or executable.
    :param var: environment variable to trace.
    :param scope: environment scope (default: cwd).
    :returns: source path.
    """

    # get the sources for the given stack(s)
    sources = get_sources(*name, scope=scope, ignore_missing=True)
    sources.reverse()

    # check for the variable in the env files
    for source in sources:
        data = load_file(source.path)
        env = data.get(config.PLATFORM, data.get("all", {}))
        if var in env:
            return source.path
        elif os.getenv(var):
            return "local environment"
