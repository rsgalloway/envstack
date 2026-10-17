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
    platform=config.PLATFORM,
):
    """
    Evaluates Bash-like variable expansion modifiers.

    - ${VAR}              → empty string if unset
    - ${VAR:=default}     → if unset/empty, set to default and use it
    - ${VAR:-default}     → if unset/empty, use default (do not set)
    - ${VAR:?message}     → error if unset/empty

    :param expression: The string to evaluate.
    :param environ: The environment variables to use for substitution.
    :param parent: Parent environment variables to use for substitution.
    :param resolving: A set of currently resolving variables to prevent cycles.
    :param reference: Optional lookup for references in a layered environment.
    :param platform: Platform used to split, deduplicate, and join path values.
    :returns: The evaluated string with variables substituted.
    :raises ValueError: If a variable is not set and a message is provided.
    """
    if resolving is None:
        resolving = set()

    def sanitize_value(value):
        """Normalize path lists and remove unmatched trailing expansion braces."""
        if isinstance(value, str) and value.endswith("}") and not value.startswith("${"):
            # trim a dangling '}' when there's no matching '{'
            if value.count("{") == 0 and value.count("}") == 1:
                return value.rstrip("}")
            return value
        elif isinstance(value, str) and util.detect_path(value):
            return util.dedupe_paths(value, platform=platform)
        return value

    def is_template(s: str) -> bool:
        """Return whether a string contains a supported variable expansion."""
        return isinstance(s, str) and bool(variable_pattern.search(s))

    def non_empty(s: str) -> bool:
        """Return whether the value is a string with at least one character."""
        return isinstance(s, str) and s != ""

    def is_literal(s: str) -> bool:
        """Return whether a nonempty string contains no variable expansions."""
        return isinstance(s, str) and s != "" and not is_template(s)

    def substitute_variable(match):
        """Expand one matched reference using the supplied lookup or mappings."""
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
                default = evaluate_modifiers(
                    argument or "", environ, parent, resolving, reference, platform
                )
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
                    eff = evaluate_modifiers(
                        current, environ, parent, resolving, reference, platform
                    )
                else:
                    eff = current or ""

                # 3) if effective value is non-empty, do NOT take default
                if non_empty(eff):
                    return str(eff)

                # 4) unset or null,  use default (and assign for :=)
                default = evaluate_modifiers(
                    argument or "", environ, parent, resolving, reference, platform
                )
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
                    evaluate_modifiers(current, environ, parent, resolving, reference, platform)
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
                    return str(
                        evaluate_modifiers(current, environ, parent, resolving, reference, platform)
                    )
                # current is unset/empty, use parent/os if present, else empty
                return str(override or "")

            # simple ${VAR}
            else:
                value = current or override or ""
                if variable_pattern.search(value):
                    value = evaluate_modifiers(
                        value, environ, parent, resolving, reference, platform
                    )
                return str(value)

        finally:
            resolving.discard(var_name)

    try:
        if isinstance(expression, (int, float, bool)):
            expression = str(expression)

        result = variable_pattern.sub(substitute_variable, expression)

        if variable_pattern.search(result):
            result = evaluate_modifiers(result, environ, parent, resolving, reference, platform)

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
                evaluate_modifiers(v, environ, parent, reference=reference, platform=platform)
                for v in expression
            ]
        elif isinstance(expression, dict):
            result = {
                k: evaluate_modifiers(v, environ, parent, reference=reference, platform=platform)
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
    """Resolve a loaded environment without modifying its source definitions.

    Decrypt values and collect definition history before evaluating references.
    Source history follows the platform selected when the environment was loaded.

    :param env: An Env instance with source history, or a plain variable mapping.
    :returns: A new Env containing resolved values with supported types restored.
    """
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
    resolved.platform = env.platform
    resolver = _StackResolver(env_copy, definitions, platform=env.platform)
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

    def __init__(self, environ, definitions, platform=config.PLATFORM):
        """Initialize dependency tracking and default-assignment scopes.

        :param environ: The final variable mapping used for expression evaluation.
        :param definitions: Variable names mapped to definitions in load order,
            from earliest to latest.
        :param platform: Platform used for path normalization.
        """
        self.environ = environ
        self.platform = platform
        self.definitions = definitions
        self.active = []
        self.limits = {}
        self.assigned = {}
        self.local_assigned = {}

    def resolve(self, key, index=None):
        """Evaluate a definition, falling back through history to break cycles.

        Ordinary dependencies use their final definitions. Recursive dependencies
        use earlier definitions where available, then the process environment.
        Self-default assignments are discarded when their definition completes.

        :param key: The variable to resolve.
        :param index: Definition index, or None for the latest allowed definition.
            A negative index selects the assignment or shell fallback.
        :returns: The expanded value before final type conversion.
        """
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
                    nested = _StackResolver(self.environ, self.definitions, platform=self.platform)
                    nested.limits = dict(self.limits, **{variable: position - 1})
                    nested.assigned = self.assigned
                    return nested.resolve(key)
            return os.getenv(key, "")
        self.active.append(frame)
        try:
            return evaluate_modifiers(
                history[index], self.environ, reference=self.reference, platform=self.platform
            )
        finally:
            self.active.pop()
            self.local_assigned.pop(frame, None)

    def reference(self, key, operator, argument):
        """Resolve one reference and apply its optional expansion modifier.

        Assignments from := remain available to subsequent references. A
        self-assignment stays local to the active definition so it cannot shadow
        the variable's complete final value in other definitions.

        :param key: The referenced variable name.
        :param operator: "=", "-", "?", or None for a plain reference.
        :param argument: The fallback expression or required-value error message.
        :returns: The referenced value or evaluated fallback.
        :raises ValueError: If a required value is unset or empty.
        """
        # A self-default belongs to the active definition. Keep it available
        # within that definition, but do not let it shadow the final value
        # when another variable refers to this one after resolution.
        frame = next((frame for frame in reversed(self.active) if frame[0] == key), None)
        assignments = self.local_assigned.setdefault(frame, {}) if frame else self.assigned
        if key in assignments:
            value = assignments[key]
        elif key in self.assigned:
            value = self.assigned[key]
        else:
            value = self.resolve(key)
        if operator in ("=", "-"):
            # resolve() already applies stack precedence and shell fallback.
            # An explicit empty value therefore takes the requested default.
            if not value:
                value = evaluate_modifiers(
                    argument or "", self.environ, reference=self.reference, platform=self.platform
                )
                if operator == "=":
                    assignments[key] = value
            return value
        if operator == "?" and not value:
            raise ValueError(argument or f"{key} is not set")
        return value
