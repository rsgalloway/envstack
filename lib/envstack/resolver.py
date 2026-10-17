#!/usr/bin/env python3
#
# Copyright (c) 2024-2026, Ryan Galloway (ryan@rsgalloway.com)
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

"""Variable expansion and late-bound stack resolution."""

import os
import re

from envstack import config, util
from envstack.node import AESGCMNode, Base64Node, EncryptedNode, FernetNode

# regular expression pattern for bash-like variable expansion
variable_pattern = re.compile(r"\$\{([a-zA-Z_][a-zA-Z0-9_]*)(?::([-=?])((?:\$\{[^}]+\}|[^}])*))?\}")


def evaluate_modifiers(
    expression: str,
    environ: dict = os.environ,
    parent: dict = {},
    resolving: set = None,
    reference=None,
):
    """
    Evaluates Bash-like variable expansion modifiers.

    - ${VAR}              → empty string if unset
    - ${VAR:=default}     → if unset/null, set to default and use it
    - ${VAR:-default}     → if unset/null, use default (do not set)
    - ${VAR:?message}     → error if unset/null

    :param expression: The string to evaluate.
    :param environ: The environment variables to use for substitution.
    :param parent: Parent environment variables to use for substitution.
    :param resolving: A set of currently resolving variables to prevent cycles.
    :param reference: Optional lookup for references in a layered environment.
    :returns: The evaluated string with variables substituted.
    :raises ValueError: If a variable is not set and a message is provided.
    """
    if resolving is None:
        resolving = set()

    def sanitize_value(value):
        if isinstance(value, str) and value.endswith("}") and not value.startswith("${"):
            # trim a dangling '}' when there's no matching '{'
            if value.count("{") == 0 and value.count("}") == 1:
                return value.rstrip("}")
            return value
        elif isinstance(value, str) and util.detect_path(value):
            return util.dedupe_paths(value)
        return value

    def is_template(s: str) -> bool:
        # Check if the string is a template variable like ${VAR}
        return isinstance(s, str) and bool(variable_pattern.search(s))

    def non_empty(s: str) -> bool:
        # non-empty string, not just whitespace
        return isinstance(s, str) and s != ""

    def is_literal(s: str) -> bool:
        # non-empty, does not contain ${...}
        return isinstance(s, str) and s != "" and not is_template(s)

    def substitute_variable(match):
        if reference is not None:
            return str(reference(match.group(1), match.group(2), match.group(3)))

        # extract variable name, operator, and argument from the match
        var_name = match.group(1)
        operator = match.group(2)  # '=', '-', '?', or None
        argument = match.group(3)  # may be None
        parent_value = parent.get(var_name, "")
        override = parent.get(var_name, os.getenv(var_name, ""))
        current = str(environ.get(var_name, parent_value or ""))  # current value we have
        # A literal definition, including an empty string, overrides the
        # shell. Only missing values and self-references inherit a value.
        if var_name in environ and not is_template(str(environ[var_name])):
            override = ""
        varstr = "${%s}" % var_name

        # cycle / self-reference guard
        if var_name in resolving:
            if operator in ("=", "-"):
                # if os/parent provides a value, that wins over the default
                if override:
                    return str(override)
                default = evaluate_modifiers(argument or "", environ, parent, resolving, reference)
                if operator == "=":
                    environ[var_name] = default
                return str(default)
            elif operator == "?":
                msg = argument or f"{var_name} is not set"
                raise ValueError(msg)
            else:  # plain ${VAR}
                return str(override or "")

        resolving.add(var_name)
        try:
            # replace literal self-references inside current (best-effort)
            if current and varstr in current:
                current = current.replace(varstr, override or "")

            # defaults branch (:=, :-)
            if operator in ("=", "-"):
                # 1) explicit env/parent wins if non-empty (bash: considered "set")
                if non_empty(override):
                    return str(override)

                # 2) compute the effective value of the current entry
                if is_template(current):
                    eff = evaluate_modifiers(current, environ, parent, resolving, reference)
                else:
                    eff = current or ""

                # 3) if effective value is non-empty, do NOT take default
                if non_empty(eff):
                    return str(eff)

                # 4) unset or null,  use default (and assign for :=)
                default = evaluate_modifiers(argument or "", environ, parent, resolving, reference)
                if operator == "=":
                    environ[var_name] = default
                return str(default)

            # error branch (:?)
            elif operator == "?":
                if not current:
                    msg = argument or f"{var_name} is not set"
                    raise ValueError(msg)
                # resolve if it contains vars
                return (
                    evaluate_modifiers(current, environ, parent, resolving, reference)
                    if variable_pattern.search(current)
                    else current
                )

            elif operator is None:
                # check for command substitution
                if config.ALLOW_COMMANDS and util.cmdsub_pattern.match(str(current)):
                    return str(util.evaluate_command(current))
                if is_literal(current):
                    return current  # file literal wins
                if is_template(current):
                    return str(evaluate_modifiers(current, environ, parent, resolving, reference))
                # current is unset/empty, use parent/os if present, else empty
                return str(override or "")

            # simple ${VAR}
            else:
                value = current or override or ""
                if variable_pattern.search(value):
                    value = evaluate_modifiers(value, environ, parent, resolving, reference)
                return str(value)

        finally:
            resolving.discard(var_name)

    try:
        if isinstance(expression, (int, float, bool)):
            expression = str(expression)

        result = variable_pattern.sub(substitute_variable, expression)

        if variable_pattern.search(result):
            result = evaluate_modifiers(result, environ, parent, resolving, reference)

    except RecursionError:
        # treat cycles as empty string instead of crashing (like bash)
        result = ""

    except TypeError:
        # node/list/dict handlers
        if isinstance(expression, AESGCMNode):
            result = expression.resolve(env=environ)
        elif isinstance(expression, Base64Node):
            result = expression.resolve(env=environ)
        elif isinstance(expression, EncryptedNode):
            result = expression.resolve(env=environ)
        elif isinstance(expression, FernetNode):
            result = expression.resolve(env=environ)
        elif isinstance(expression, list):
            result = [
                evaluate_modifiers(v, environ, parent, reference=reference) for v in expression
            ]
        elif isinstance(expression, dict):
            result = {
                k: evaluate_modifiers(v, environ, parent, reference=reference)
                for k, v in expression.items()
            }
        else:
            result = expression

    resolved_value = sanitize_value(result)

    # command substitution
    if config.ALLOW_COMMANDS and isinstance(resolved_value, str):
        resolved_value = util.evaluate_command(resolved_value)

    return resolved_value


def resolve_environment(env):
    """Resolve a loaded environment without modifying its source definitions."""
    from envstack.env import Env
    from envstack.node import custom_node_types, get_keys_from_env

    # stores the resolved environment
    resolved = Env()

    if type(env) is not Env:
        env = Env(env)

    # copy env to avoid modifying the original
    env_copy = env.copy()

    # make a copy that contains the encryption keys
    env_keys = env.copy()
    env_keys.update(get_keys_from_env(os.environ))

    # decrypt custom nodes
    for key, value in list(env_copy.items()):
        if type(value) in custom_node_types:
            env_copy[key] = value.resolve(env=env_keys)

    definitions = {}
    seen_source_paths = set()
    for source in env.sources:
        if source.path in seen_source_paths:
            continue
        seen_source_paths.add(source.path)
        for key, value in source.load(platform=env.platform).items():
            if key not in env_copy:
                continue
            if type(value) in custom_node_types:
                value = value.resolve(env=env_keys)
            definitions.setdefault(key, []).append(value)

    # The caller may have edited the loaded environment before resolving it.
    for key, value in env_copy.items():
        history = definitions.setdefault(key, [])
        if not history or history[-1] != value:
            history.append(value)
    resolver = _StackResolver(env_copy, definitions)
    for key in list(env_copy):
        resolved[key] = util.safe_eval(resolver.resolve(key))
    return resolved


class _StackResolver:
    """Resolve dependencies lazily, retaining every definition of each variable.

    References use the final definition unless that would re-enter an active
    definition. A cycle then falls back to a preceding definition, including
    when the cycle passes through an alias. Intermediate results are not cached:
    their values can depend on which definition is currently being resolved.
    """

    def __init__(self, environ, definitions):
        self.environ = environ
        self.definitions = definitions
        self.active = []
        self.limits = {}
        self.assigned = {}

    def resolve(self, key, index=None):
        history = self.definitions.get(key, [])
        if index is None:
            index = self.limits.get(key, len(history) - 1)
        if index < 0:
            return self.assigned.get(key, os.getenv(key, ""))
        frame = (key, index)
        if frame in self.active:
            cycle = self.active[self.active.index(frame) :]
            # Prefer the repeated variable's previous definition. If it is an
            # alias with no history, use the next variable with history.
            for variable, position in cycle:
                if position > 0:
                    nested = _StackResolver(self.environ, self.definitions)
                    nested.limits = dict(self.limits, **{variable: position - 1})
                    nested.assigned = self.assigned
                    return nested.resolve(key)
            return os.getenv(key, "")
        self.active.append(frame)
        try:
            return evaluate_modifiers(history[index], self.environ, reference=self.reference)
        finally:
            self.active.pop()

    def reference(self, key, operator, argument):
        # Assignments affect subsequent references, not source definitions.
        value = self.assigned[key] if key in self.assigned else self.resolve(key)
        if operator in ("=", "-"):
            # resolve() already applies stack precedence and shell fallback.
            # An explicit empty value therefore takes the requested default.
            if not value:
                value = evaluate_modifiers(argument or "", self.environ, reference=self.reference)
                if operator == "=":
                    self.assigned[key] = value
            return value
        if operator == "?" and not value:
            raise ValueError(argument or f"{key} is not set")
        return value
