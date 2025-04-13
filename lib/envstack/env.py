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
Contains functions and classes for processing scoped .env files.
"""

import os
import re
import string
from pathlib import Path

import yaml  # noqa

from envstack import config, logger, path, util
from envstack.exceptions import *  # noqa
from envstack.node import (
    BaseNode,
    EncryptedNode,
    custom_node_types,
    get_keys_from_env,
)

# value delimiter pattern (splits values by os.pathsep)
delimiter_pattern = re.compile("(?![^{]*})[;:]+")

# stores environment when calling envstack.save()
saved_environ = None

# stores seen stack names when getting sources
seen_stacks = set()


class Scope(path.Path):
    """Scope class."""

    def __init__(self, path: str = None):
        """
        :param path: scope path (default is CWD)
        """
        self.path = path or os.getcwd()


class Source(object):
    """envstack .env source file."""

    def __init__(self, path: str = None):
        """
        :param path: path to .env file.
        """
        self.path = path
        self.data = {}

    def __eq__(self, other):
        if not isinstance(other, Source):
            return False
        return self.path == other.path

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.__repr__())

    def __repr__(self):
        return f"<Source '{self.path}'>"

    def __str__(self):
        return str(self.path)

    def exists(self):
        """Returns True if the .env file exists"""
        return os.path.exists(self.path)

    def includes(self):
        """Returns list of included environments, defined in
        .env files above the "all:" statment as:

            include: [name1, name2, ... nameN]
        """
        if not self.data:
            self.load()
        return self.data.get("include", [])

    def length(self):
        """Returns the char length of the path"""
        return len(self.path)

    def load(self, platform=config.PLATFORM):
        """Reads .env from .path, and returns an Env class object"""
        if self.path and not self.data:
            self.data = load_file(self.path)
        return self.data.get(platform, self.data.get("all", {}))

    def namespace(self):
        """Returns the namespace of the source file."""
        return os.path.basename(self.path).split(".")[0]

    def write(self, filepath: str = None):
        """Writes the source data to the .env file."""
        util.dump_yaml(filepath or self.path, self.data)


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
        """If value is a list, extend list by appending elements from the
        iterable.

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
            if "maximum recursion" in str(err):
                raise CyclicalReference(self.template)  # noqa
            else:
                raise InvalidSyntax(err)  # noqa
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
        """Returns a list of delimited parts, e.g. if a value is delimited by a
        colon (or semicolon on windows), for example:

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
        self.sources = []

    def load_source(self, source: Source, platform=config.PLATFORM):
        """Loads environment from a given Source object. Appends to sources
        list.

        :param source: Source object.
        :param platform: name of platform (linux, darwin, windows).
        """
        self.sources.append(source)
        self.update(source.load(platform=platform))

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

    def bake(self, filename: str = None, depth: int = 0, encrypt: bool = False):
        """Bakes an environment with multiple sources into a single environment
        and writes to a new env file.

            >>> env = load_environ(stack_name)
            >>> env.bake("baked.env")

        :param filename: path to save the baked environment.
        :param depth: depth of source files to incldue (default: all).
        :param encrypt: encrypt the values.
        :returns: baked environment.
        """
        # get the sources for the given environment
        sources = self.sources

        # look for encryption keys in the environment
        os.environ.update(get_keys_from_env(self))

        # create a baked source
        baked = Source(filename)

        def get_node_class(value):
            """Returns the node class to use for a given value."""
            if encrypt:
                if type(value) in custom_node_types:
                    return value.__class__
                else:
                    return EncryptedNode
            return value.__class__

        # merge the sources into the outfile
        for source in sources[-depth:]:
            for key, value in source.data.items():
                if isinstance(value, dict):
                    for k, v in value.items():
                        node_class = get_node_class(v)
                        baked.data.setdefault(key, {})[k] = node_class(v)
                else:
                    node_class = get_node_class(value)
                    baked.data[key] = node_class(value)

        # clear includes if environment stack is fully baked
        if depth <= 0:
            baked.data["include"] = []

        # write the baked environment to the file
        if filename:
            baked.write()

        # create the baked environment from the baked source
        baked_env = Env()
        baked_env.load_source(baked)

        return baked_env

    def write(self, filename: str = None):
        """Writes the environment to an env file.

            >>> env = Env({"FOO": "${BAR}", "BAR": "bar"})
            >>> env.write("foo.env")

        To encrypt values, use EncryptedNode:

            >>> env = Env({"FOO": "${BAR}", "BAR": EncryptedNode("bar")})
            >>> env.write("encrypted.env")

        :param filename: path to save the baked environment.
        :returns: Source object.
        """
        # the environment was loaded from one or more sources
        if self.sources:
            baked = self.bake(filename)
            return baked.sources[0]

        # the environment was created from scratch
        else:
            source = Source(filename)
            for k, v in self.items():
                source.data[k] = v
            source.write()
            return source


@util.cache
def get_sources(
    *names,
    scope: str = None,
    ignore_missing: bool = config.IGNORE_MISSING,
    envpath: str = os.environ.get("ENVPATH", ""),
):
    """
    Returns a list of Source objects for a given list of .env basenames.

    :param names: list of .env file names to search for.
    :param scope: filesystem path defining the scope to walk up to.
    :param ignore_missing: ignore missing .env files.
    :param envpath: colon-separated list of directories to search for .env files
    :raises TemplateNotFound: if a file is not found in ENVPATH or scope.
    :returns: list of Source objects for the given stack names.
    """
    loaded_files = []
    sources = []
    loading_stack = set()

    scope = Path(scope or os.getcwd()).resolve()

    def _walk_to_scope(current_path):
        """Generate directories from the current path up to the scope."""
        paths = []
        while current_path != scope.parent:
            paths.append(current_path)
            if current_path == scope:
                break
            current_path = current_path.parent
        return [str(p) for p in paths]

    # construct search paths from ${ENVPATH} and scope
    envpath_dirs = util.split_paths(envpath)
    scope_dirs = _walk_to_scope(scope)
    envpath_dirs.reverse()
    search_paths = envpath_dirs + scope_dirs

    def _find_files(file_basename):
        """Find .env files in the search paths."""
        if not file_basename.endswith(".env"):
            file_basename += ".env"
        found_files = []
        for directory in search_paths:
            potential_file = Path(directory) / file_basename
            if potential_file.exists() and potential_file not in found_files:
                found_files.append(potential_file)
        if not found_files and not ignore_missing:
            raise TemplateNotFound(  # noqa
                f"{file_basename} not found in ENVPATH or scope."
            )
        return found_files

    def _load_file(file_basename):
        """Recursively load .env files and their includes."""
        seen_stacks.add(os.path.splitext(file_basename)[0])

        # check if we're sourcing a file or a namespace
        if file_basename.endswith(".env") and os.path.exists(file_basename):
            file_paths = [file_basename]
        else:
            file_paths = _find_files(file_basename)

        # process each file independently
        for file_path in file_paths:
            if file_path in loaded_files:
                continue

            if file_basename in loading_stack:
                raise ValueError(f"Cyclic dependency detected in {file_basename}")

            source = Source(file_path)
            if source in sources:
                continue

            loading_stack.add(file_basename)

            # parse included files recursively, don't include if already seen
            for include_basename in source.includes():
                if include_basename in seen_stacks:
                    continue
                _load_file(include_basename)

            # add current file to the loaded list after processing includes
            loaded_files.append(file_path)
            sources.append(source)
            loading_stack.remove(file_basename)

    # process each stack in the list
    for name in names:
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
    # load the envrinment for the given stack and get list of sources
    env = load_environ(name, scope=scope)

    # track the environment variables to export
    export_list = list()

    # restricted environment variables
    restricted = [
        "ENVPATH",
        "LD_LIBRARY_PATH",
        "PATH",
        "PYTHONPATH",
        "PROMPT",
        "PS1",
        "PWD",
    ]

    # get the name of the shell
    shell_name = os.path.basename(shell)

    for key in env:
        if key not in os.environ:
            continue
        old_key = f"_ES_OLD_{key}"
        old_val = os.environ.get(old_key)
        if shell_name in ["bash", "sh", "zsh"]:
            if old_val:
                export_list.append("export %s=%s" % (key, old_val))
                export_list.append("unset %s" % (old_key))
            elif key not in restricted:
                export_list.append(f"unset {key}")
        elif shell_name == "tcsh":
            if old_val:
                export_list.append(f"setenv {key} {old_val}")
                export_list.append(f"unsetenv {old_key}")
            elif key not in restricted:
                export_list.append(f"unsetenv {key}")
        elif shell_name == "cmd":
            if old_val:
                export_list.append(f"set {key}={old_val}")
                export_list.append(f"set {old_key}=")
            elif key not in restricted:
                export_list.append(f"set {key}=")
        elif shell_name == "pwsh":
            if old_val:
                export_list.append(f"$env:{key}='{old_val}'")
                export_list.append(f"Remove-Item Env:{old_key}")
            elif key not in restricted:
                export_list.append(f"Remove-Item Env:{key}")
        elif shell_name == "unknown":
            raise Exception("unknown shell")

    export_list.sort()
    exp = "\n".join(export_list)

    return exp


def export_env_to_shell(env: Env, shell: str = config.SHELL):
    """Returns shell commands that can be sourced to set environment stack
    environment variables.

    Supported shells: bash, sh, tcsh, cmd, pwsh (see config.detect_shell()).

    :param env: environment dict.
    :param shell: name of shell (default: current shell).
    :returns: shell commands as string.
    """

    # track the environment variables to export
    export_list = list()

    # get the name of the shell
    shell_name = os.path.basename(shell)

    # iterate over the environment variables
    for key, val in env.copy().items():
        old_key = f"_ES_OLD_{key}"
        old_val = os.environ.get(key)
        if key == "PATH" and not val:
            logger.log.warning("PATH is empty")
            continue
        if shell_name in ["bash", "sh", "zsh"]:
            export_list.append(f"export {key}={val}")
            if old_val:
                export_list.append(f"export {old_key}={old_val}")
        elif shell_name == "tcsh":
            export_list.append(f'setenv {key}:"{val}"')
            if old_val:
                export_list.append(f'setenv {old_key}:"{old_val}"')
        elif shell_name == "cmd":
            export_list.append(f'set {key}="{val}"')
            if old_val:
                export_list.append(f'set {old_key}="{old_val}"')
        elif shell_name == "pwsh":
            export_list.append(f'$env:{key}="{val}"')
            if old_val:
                export_list.append(f'$env:{old_key}="{old_val}"')
        elif shell_name == "unknown":
            raise Exception("unknown shell")

    export_list.sort()
    exp = "\n".join(export_list)

    return exp


def export(
    name: str = config.DEFAULT_NAMESPACE,
    shell: str = config.SHELL,
    scope: str = None,
):
    """Returns shell commands that can be sourced to set environment stack
    environment variables.

    Supported shells: bash, sh, tcsh, cmd, pwsh (see config.detect_shell()).

    :param name: stack namespace.
    :param shell: name of shell (default: current shell).
    :param scope: environment scope (default: cwd).
    :returns: shell commands as string.
    """
    resolved_env = resolve_environ(load_environ(name, scope=scope))
    return export_env_to_shell(resolved_env, shell)


def save():
    """Caches the current environment for later restoration."""
    global saved_environ

    if not saved_environ:
        saved_environ = dict(os.environ.copy())
        return saved_environ


def revert():
    """Reverts the environment to the last cached version. Updates sys.path
    using paths found in PYTHONPATH.

    Initialize the default environment stack:

        >>> envstack.init()

    Revert to the previous environment:

        >>> envstack.revert()
    """
    global saved_environ
    global seen_stacks

    # clear the seen stacks
    seen_stacks = set()

    # nothing to revert to
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

    # clear old sys.path values from PYTHONPATH
    util.clear_sys_path()

    # load the stack and update the environment
    env = resolve_environ(load_environ(name, ignore_missing=ignore_missing))
    os.environ.update(util.encode(env))

    # update sys.path from resolved PYTHONPATH
    util.load_sys_path()


def bake_environ(
    name: str = config.DEFAULT_NAMESPACE,
    scope: str = None,
    depth: int = 0,
    filename: str = None,
    encrypt: bool = False,
):
    """Bakes one or more environment stacks into a single source .env file.

        $ envstack [STACK] -o <filename>

    :param name: stack namespace.
    :param scope: environment scope (default: cwd).
    :param depth: depth of source files to incldue (default: all).
    :param filename: path to save the baked environment.
    :param encrypt: encrypt the values.
    :returns: baked environment.
    """
    return load_environ(name, scope=scope).bake(filename, depth, encrypt)


def encrypt_environ(
    env: dict, node_class: BaseNode = EncryptedNode, encrypt: bool = True
):
    """Encrypts all values in a given environment, returning a new environment.
    Looks for encryption keys in the environment.

    Python:

        >>> env = {"FOO": "bar"}
        >>> env = envstack.encrypt_environ(env)

    Command line:

        $ envstack [STACK] --encrypt

    :param env: environment to encrypt.
    :param node_class: node class to use for encryption.
        Defaults to EncryptedNode, which looks for encryption keys in the
        environment to determine the encryption method.
    :param encrypt: pre-encrypt the values.
    :returns: encrypted environment.
    """
    # stores the encrypted environment
    encrypted_env = Env()

    # copy the environment to avoid modifying the original
    env_copy = env.copy()

    # resolve internal environment and look for keys in os.environ
    resolved_env = resolve_environ(env_copy)
    resolved_env.update(get_keys_from_env(os.environ))

    for k, v in env_copy.items():
        if type(v) not in custom_node_types:
            # TODO: use to_yaml() method to serialize instead?
            node = node_class(v)
            if encrypt:
                node.value = node.encryptor(env=resolved_env).encrypt(str(v))
            encrypted_env[k] = node
        else:
            encrypted_env[k] = v

    return encrypted_env


def resolve_environ(env: Env):
    """Resolves all variables in a given unresolved environment, returning a
    new environment dict.

    :param env: unresolved environment.
    :returns: resolved environment.
    """
    # stores the resolved environment
    resolved = Env()

    if type(env) is not Env:
        env = Env(env)

    # copy env to avoid modifying the original
    env_copy = env.copy()

    # evaluate one source environment at a time
    seen_source_paths = []
    included = Env()
    sources = env.sources[:-1]
    sources.reverse()
    for source in sources:
        if source.path in seen_source_paths:
            continue
        seen_source_paths.append(source.path)
        source_environ = resolve_environ(Env(source.load()))
        for key, value in source_environ.items():
            included[key] = util.evaluate_modifiers(value, environ=source_environ)

    # make a copy that contains the encryption keys
    env_keys = env.copy()
    env_keys.update(get_keys_from_env(os.environ))

    # decrypt custom nodes
    for key, value in env_copy.items():
        if type(value) in custom_node_types:
            env_copy[key] = value.resolve(env=env_keys)

    # resolve environment variables after decrypting custom nodes
    for key, value in env_copy.items():
        resolved[key] = util.evaluate_modifiers(
            value, environ=env_copy, parent=included
        )

    return resolved


# TODO: make 'name' arg a list (*names)
def load_environ(
    name: str = config.DEFAULT_NAMESPACE,
    platform: str = config.PLATFORM,
    scope: str = None,
    ignore_missing: bool = config.IGNORE_MISSING,
    encrypt: bool = False,
):
    """Loads env stack data for a given name. Adds "STACK" key to environment,
    and sets the value to `name`.

    To load an environment for a given namespace, where the scope is the current
    working directory (cwd):

        >>> env = load_environ(name)

    To reload the same namespace for a different scope (different cwd):

        >>> env = load_environ(name, scope="/path/to/scope")

    :param name: list of stack names to load (basename of env files).
    :param platform: name of platform (linux, darwin, windows).
    :param scope: environment scope (default: cwd).
    :param ignore_missing: ignore missing .env files.
    :encrypt: encrypt the values using available encryption methods.
    :returns: dict of environment variables.
    """
    if type(name) is str:
        name = [name]
    if not name:
        name = [config.DEFAULT_NAMESPACE]

    # create the environment to be returned
    env = Env()
    env.set_namespace(name)
    if scope:
        env.set_scope(scope)

    # initial ${ENVPATH} value
    envpath = os.getenv("ENVPATH", os.getcwd())

    # dedupe sources based on paths
    seen_paths = []

    # get and load stack sources in order
    for stack_name in name:
        sources = get_sources(
            stack_name,
            envpath=envpath,
            scope=scope,
            ignore_missing=ignore_missing,
        )
        for source in sources:
            # don't load the same source more than once
            if source.path in seen_paths:
                continue
            env.load_source(source, platform=platform)
            seen_paths.append(source.path)

            # add the stack name to the environment
            if not env.get("STACK"):
                env["STACK"] = util.get_stack_name(name)

        # resolve ${ENVPATH} (don't let it be None)
        # TODO: use expandvars() instead of resolve_environ()
        envpath = resolve_environ(env).get("ENVPATH", envpath) or envpath

    # encrypt the values in the environment last
    if encrypt:
        return encrypt_environ(env)

    return env


@util.cache
def load_file(path: str):
    """Reads a given .env file and returns data as dict. Data is memoized in
    memory for faster access.

    :param path: path to .env file.
    :returns: loaded yaml data as dict.
    """

    if not os.path.exists(path):
        return {}

    return util.validate_yaml(path)


@util.cache
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
