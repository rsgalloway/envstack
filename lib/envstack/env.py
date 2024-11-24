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
import sys

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


def _build_sources(
    name=config.DEFAULT_NAMESPACE,
    scope=None,
    includes=True,
    default=config.DEFAULT_NAMESPACE,
):
    sources = []

    # list of included .env files
    include_sources = []

    # scope, or root, of env tree
    path = scope or os.getcwd()
    scope = Scope(scope)
    level, levels = 0, len(scope.levels())

    # the namespaced and default .env file names
    named_env = f"{name}.env"
    default_env = f"{default}.env"

    def add_source(path):
        """Adds a source to the list of sources."""
        if not os.path.exists(path):
            return
        if not sources or (sources[0].path != path):
            this_source = Source(path)
            sources.insert(0, this_source)
            return this_source

    def add_includes(src):
        """Adds included sources to the list of sources and includes."""
        included = [f"{i}.env" for i in src.includes()]
        for include_env in included:
            include_file = os.path.join(config.DEFAULT_ENV_DIR, include_env)
            if include_env not in include_sources:
                include_sources.append(include_env)
            add_source(include_file)

    # walk up the directory tree looking for .env files
    while level < levels:
        named_file = os.path.join(path, named_env)
        src = add_source(named_file)
        if src and includes:
            add_includes(src)

        # look for a default .env file in this scope
        default_file = os.path.join(path, default_env)
        add_source(default_file)

        path = os.path.dirname(path)
        if not path:
            continue

        level += 1

    # look for default include .env files (and their includes)
    for include_source in include_sources:
        default_inc_src = add_source(
            os.path.join(config.DEFAULT_ENV_DIR, include_source)
        )
        if default_inc_src and includes:
            add_includes(default_inc_src)

    # check for default .env file
    default_src = add_source(os.path.join(config.DEFAULT_ENV_DIR, named_env))

    # add included sources
    if default_src and includes:
        add_includes(default_src)

    # check for global default .env file
    global_default = os.path.join(config.DEFAULT_ENV_DIR, default_env)
    add_source(global_default)

    return sources


def build_sources(
    name=config.DEFAULT_NAMESPACE,
    scope=None,
    includes=True,
    default=config.DEFAULT_NAMESPACE,
):
    """Builds the list of env source files for a given name. Where the source
    is in the list of sources depends on its position in the directory tree.
    Lower scope sources will override higher scope sources, with the default
    source at the lowest scope position:

        $DEFAULT_ENV_DIR/stack.env
        /stack.env
        /show/stack.env
        /show/seq/stack.env
        /show/seq/shot/stack.env
        /show/seq/shot/task/stack.env

    :param name: list of .env file basenames.
    :param scope: environment scope (default: cwd).
    :param includes: add sources specified in includes.
    :param default: name of default environment namespace.
    :returns: list of source files sorted by scope.
    """

    sources = []

    if type(name) == str:
        namespaces = [name]
    else:
        namespaces = name

    for namespace in namespaces:
        named_sources = _build_sources(
            name=namespace,
            scope=scope,
            includes=includes,
            default=default,
        )
        if named_sources:
            sources.extend(named_sources)

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
    env = env or environ
    return EnvVar(var).expand(env, recursive=recursive)


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
    if "ENVSTACK" not in os.environ:
        logger.log.info("Environment is already clear")
        return ""

    env = load_environ(name, environ=None, scope=scope)
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
    """Saves the current environment."""
    global SAVED_ENVIRONMENT
    if not SAVED_ENVIRONMENT:
        SAVED_ENVIRONMENT = dict(os.environ.copy())
        return SAVED_ENVIRONMENT


def revert():
    """Reverts the environment to the saved environment."""
    global SAVED_ENVIRONMENT
    if SAVED_ENVIRONMENT is None:
        return
    os.environ.clear()
    os.environ.update(SAVED_ENVIRONMENT)


def init(name=config.DEFAULT_NAMESPACE):
    """Initializes the environment from a given stack namespace. Environments
    propogate downwards with subsequent calls to init().

    Updates sys.path using paths found in PYTHONPATH.

    Initialize the default environment:
    >>> envstack.init()

    Initialize the dev environment (inherits previous):
    >>> envstack.init('dev')

    Revert to the original environment:
    >>> envstack.revert()

    :param name: stack namespace (default: 'stack').
    :param reset: clear existing values first (default: False).
    """
    # save environment to restore later using envstack.revert()
    save()

    # clear old sys.path values
    for path in util.get_paths_from_var("PYTHONPATH"):
        if path and path in sys.path:
            sys.path.remove(path)

    # load the stack and update the environment
    env = load_environ(name)
    os.environ.update(encode(env))

    # update sys.path from PYTHONPATH
    for path in util.get_paths_from_var("PYTHONPATH"):
        if path and path not in sys.path:
            sys.path.insert(0, path)


def load_environ(
    name=config.DEFAULT_NAMESPACE,
    sources=None,
    environ=os.environ,
    platform=config.PLATFORM,
    scope=None,
    includes=True,
):
    """Loads env data for a given name.

    To load an environment for a given namespace, where the scope is the current
    working directory (cwd):

        >>> env = load_environ(name)

    To reload the same namespace for a different scope (different cwd):

        >>> env = load_environ(name, scope="/path/to/scope")

    :param name: namespace (basename of env files).
    :param sources: list of env files (optional).
    :param environ: merge with this environment (optional).
    :param platform: name of platform (linux, darwin, windows).
    :param scope: environment scope (default: cwd).
    :param includes: merge included namespaces.
    :returns: dict of environment variables.
    """
    # build list of sources from namespace(s) and scope
    if not sources:
        sources = build_sources(name, scope=scope, includes=includes)

    # create the environment as an Env instance
    env = Env()
    env.set_namespace(name)
    if scope:
        env.set_scope(scope)

    # load env files first
    for source in sources:
        env.update(source.load(platform=platform))

    # store the name of the environment stack
    env["ENVSTACK"] = env.get("ENVSTACK", "".join(name))

    # merge values from given environment
    if environ:
        return merge(env, environ, platform=platform)

    return env


def load_file(path):
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


def trace_var(name, var, scope=None):
    """Traces where a var is getting set for a given name.

    :param name: name of tool or executable
    :param var: environment variable to trace
    :param scope: environment scope (default: cwd)
    :returns: source path
    """
    if var in os.environ:
        return "local environment"
    sources = build_sources(name, scope=scope)
    sources.reverse()
    for source in sources:
        data = load_file(source.path)
        env = data.get(config.PLATFORM, data.get("all", {}))
        if var in env:
            return source.path


# default stack environment
environ = load_environ(environ=os.environ)


def getenv(key, default=None):
    """Replaces os.getenv, where the environment includes envstack
    declared variables.

    Get an environment variable, return None if it doesn't exist.
    The optional second argument can specify an alternate default.
    """
    return environ.get(key, default)
