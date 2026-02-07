#!/usr/bin/env python3
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
Contains pathing classes and functions.
"""

import os
import re
from typing import Iterable, Optional, Tuple

from envstack import config, logger
from envstack.exceptions import *  # noqa


# template path field regex: extracts bracketed {keys}
keyword_re = re.compile(r"{(\w*)(?::\d*d)?(?::\d*\.\d*f)?}")

# template path formatting regex
formats_re = re.compile(r"{([\w\:\.\d]*)}")

# template path field backref regex
field_re = re.compile(r"\(\?P\<(.*?)\>\[\^,;\\\/]\*\)")

# template path directory delimiter regex
directory_re = re.compile(r"[^\\/]+|[\\/]")


def _numdirs(p: str) -> int:
    return str(p).replace("\\", "/").count("/")


def _load_resolved_stack(
    stack: str,
    *,
    platform: str = config.PLATFORM,
    scope: Optional[str] = None,
):
    """
    Load + resolve an envstack environment stack.

    NOTE: This intentionally uses envstack's own resolution model rather than
    os.environ as the primary source of truth.
    """
    from .env import load_environ, resolve_environ

    raw = load_environ(stack, platform=platform, scope=scope)
    return resolve_environ(raw)


def _expand_dollar_vars(template: str, env: dict) -> str:
    """
    Expand $VARS / ${VARS} in `template` using the provided `env` mapping.

    Uses envstack.env.EnvVar (string.Template-based) so behavior matches the rest
    of envstack.
    """
    from .env import EnvVar

    # EnvVar.expand() returns either EnvVar, list, or dict depending on input.
    expanded = EnvVar(template).expand(env, recursive=True)

    if isinstance(expanded, list) or isinstance(expanded, dict):
        raise InvalidSyntax(
            f"Path template expansion must resolve to a string, got {type(expanded)}"
        )

    # expanded may already be a string-like EnvVar
    return str(expanded)


def _iter_template_items(env: dict) -> Iterable[Tuple[str, str]]:
    """
    Heuristic filter for "likely path templates" inside an environment.

    We avoid assuming a special namespace and instead scan the stack for values
    that look like templates.
    """
    for k, v in env.items():
        if not isinstance(v, str) or not v:
            continue

        # Must contain at least one format field; otherwise it's not a template.
        if "{" not in v or "}" not in v:
            continue

        # Most path templates contain a separator; keep this loose.
        if "/" not in v and "\\" not in v:
            continue

        yield k, v


class Path(str):
    """Subclass of `str` with some platform agnostic pathing support."""

    SEPARATORS = ["/", "\\"]

    def __init__(self, path, platform: str = config.PLATFORM):
        self.path = path
        self.platform = platform

    def __repr__(self):
        return "<{0} '{1}'>".format(self.__class__.__name__, self.path)

    def __str__(self):
        return str(self.path)

    def basename(self):
        """Returns the final component of the path."""
        return os.path.basename(str(self))

    def dirname(self):
        """Returns the directory component of the path."""
        return os.path.dirname(str(self))

    def levels(self):
        """Returns number of directory levels in the path."""
        tokens = directory_re.findall(self.path)
        return [t for t in tokens if t not in self.SEPARATORS]

    def to_platform(
        self,
        platform: str = config.PLATFORM,
        *,
        stack: str = config.DEFAULT_NAMESPACE,
        scope: Optional[str] = None,
        root_var: str = "ROOT",
    ):
        """
        Converts path root from this Path.platform to `platform` using ROOT values
        from the resolved envstack environment for each platform.

        :param platform: target platform name
        :param stack: envstack stack to load for ROOT values (e.g. 'fps')
        :param scope: scope to resolve stack from (defaults to dirname of this path)
        :param root_var: env var name to treat as platform root (default: ROOT)
        :returns: converted path string
        """
        if platform == self.platform:
            return str(self)

        scope = scope or self.scope()
        try:
            from_env = _load_resolved_stack(stack, platform=self.platform, scope=scope)
            to_env = _load_resolved_stack(stack, platform=platform, scope=scope)
        except Exception as err:
            raise InvalidPath(
                f"Failed to load stack '{stack}' for platform conversion: {err}"
            )

        from_root = from_env.get(root_var)
        to_root = to_env.get(root_var)

        if not from_root or not to_root:
            raise TemplateNotFound(
                f"{root_var} undefined for platform conversion ({self.platform} -> {platform}) "
                f"in stack '{stack}'"
            )

        # Use regex escape in case roots contain special chars (e.g. backslashes)
        return re.sub(r"^{}".format(re.escape(from_root)), to_root, self.path)

    def toString(self):
        """Returns this path as a string."""
        return str(self)

    def scope(self):
        """Returns the scope for this path."""
        return os.path.dirname(str(self))


class Template(object):
    """Path Template class."""

    def __init__(self, path: str):
        assert path, "Template path format cannot be empty"
        self.path_format = str(path)

    def __repr__(self):
        return "<Template '{}'>".format(self.path_format)

    def __str__(self):
        return self.path_format

    def _parse(self, pattern: str):
        tokens = pattern.split(self.path_format)
        keys = []
        for token in tokens[1::2]:
            if token not in keys:
                keys.append(token)
        return keys

    def apply_fields(self, **fields):
        """
        Applies key/value pairs matching template format.

        :param fields: key/values to apply to template.
        :returns: resolved path as Path.
        :raises: MissingFieldError.
        """
        formats = self.get_formats()

        def cast(k, v):
            fmt = formats.get(k, str)
            try:
                return fmt(v)
            except ValueError:
                raise Exception("{0} must be {1}".format(k, fmt.__name__))

        formatted = dict((k, cast(k, v)) for k, v in fields.items())

        try:
            return Path(self.path_format.format(**formatted))
        except KeyError as err:
            raise MissingFieldError(err)  # noqa

    def get_keywords(self):
        """Returns a list of required keywords."""
        return self._parse(keyword_re)

    def get_formats(self):
        """Returns a map of keywords to value classes."""
        matches = self._parse(formats_re)
        results = {}
        for key in matches:
            _type = str
            if ":" in key:
                key, f = key.split(":")
                if "d" in f:
                    _type = int
                elif "f" in f:
                    _type = float
            results[key] = _type
        return results

    def get_fields(self, path: str):
        """Gets key/value pairs from path that map to template path."""
        path = path.replace("\\", "/")
        path_format = self.path_format.replace("\\", "/")

        tokens = keyword_re.split(path_format)
        keywords = tokens[1::2]

        tokens[1::2] = map(r"(?P<{}>[^,;\/]*)".format, keywords)
        tokens[0::2] = map(re.escape, tokens[0::2])

        # look for back references
        for i in range(len(tokens)):
            fm = field_re.match(tokens[i])
            if fm is not None:
                name = fm.group(1)
                back_ref = "(?P={name})".format(name=name)
                try:
                    while True:
                        index = tokens[i + 1 :].index(tokens[i])  # noqa
                        tokens[i + 1 + index] = back_ref
                except ValueError:
                    pass

        pattern = "".join(tokens)
        matches = re.match(pattern, path)
        if not matches:
            raise InvalidPath(path)  # noqa

        formats = self.get_formats()

        def cast(k, v):
            return formats.get(k, str)(v)

        return {k: cast(k, matches.group(k)) for k in keywords}


def extract_fields(
    filepath: str,
    template: Template,
    *,
    stack: str = config.DEFAULT_NAMESPACE,
    platform: str = config.PLATFORM,
):
    """
    Convenience function that extracts template fields from a given filepath for
    a given template instance or template name.

    :param filepath: path to file
    :param template: Template instance or name of template in `stack`
    :param stack: stack namespace to load templates from (default: config.DEFAULT_NAMESPACE)
    :param platform: optional platform name
    :returns: dictionary of template fields
    """
    try:
        p = Path(filepath, platform=platform)
        if isinstance(template, str):
            template = get_template(
                template, stack=stack, platform=platform, scope=p.scope()
            )
        return template.get_fields(filepath)

    except InvalidPath:  # noqa
        logger.log.debug(
            "path does not match template: {0} {1}".format(template, filepath)
        )
        return {}

    except Exception as err:
        logger.log.debug("error extracting fields: {}".format(err))
        return {}


def get_scope(filepath: str):
    """Convenience function that returns the scope of a given filepath."""
    return Path(filepath).scope()


def get_template(
    name: str,
    *,
    stack: str = config.DEFAULT_NAMESPACE,
    platform: str = config.PLATFORM,
    scope: str = None,
    expand_envvars: bool = True,
):
    """
    Returns a Template instance for a given template name located in `stack`.

    - Loads + resolves the envstack environment for `stack`
    - Fetches template string from resolved env
    - Expands $VARS / ${VARS} inside the template string using the resolved env
    - Returns Template(expanded_string)

    :param name: template variable name
    :param stack: envstack stack to load (e.g. 'fps')
    :param platform: platform name
    :param scope: scope (default: cwd via load_environ)
    :param expand_envvars: whether to expand $VARS in the template string
    """
    env = _load_resolved_stack(stack, platform=platform, scope=scope)

    template = env.get(name)
    if not template:
        raise TemplateNotFound(name)  # noqa

    if expand_envvars:
        template = _expand_dollar_vars(template, env)

    return Template(template)


def match_template(
    path: str,
    *,
    stack: str = config.DEFAULT_NAMESPACE,
    platform: str = config.PLATFORM,
    scope: str = None,
    expand_envvars: bool = True,
):
    """
    Returns a Template that matches a given `path`.

    - Loads + resolves `stack`
    - Considers values that look like path templates
    - Orders templates by directory depth (more specific first)
    - Returns first matching template, or raises ValueError if the path matches
      multiple templates of the same depth.

    :raises: ValueError if `path` matches multiple templates at the same depth
    :returns: matching Template or None
    """
    env = _load_resolved_stack(stack, platform=platform, scope=scope)

    items = list(_iter_template_items(env))
    items.sort(key=lambda kv: _numdirs(kv[1]), reverse=True)

    matched = None
    matched_depth = None

    for name, path_format in items:
        try:
            if expand_envvars:
                path_format_expanded = _expand_dollar_vars(path_format, env)
            else:
                path_format_expanded = path_format

            template_test = Template(path_format_expanded)

            if template_test.get_fields(path):
                depth = _numdirs(template_test.path_format)
                if matched is None:
                    matched = template_test
                    matched_depth = depth
                elif depth == matched_depth:
                    raise ValueError("path matches more than one template")

        except InvalidPath:  # noqa
            continue

    return matched
