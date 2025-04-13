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
Contains pathing classes and functions.
"""

import os
import re

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

# name of the path templates environment
TEMPLATES_ENV_NAME = "templates"

# environment variable that defines platform root
TEMPLATES_ENV_ROOT = "ROOT"


class Path(str):
    """Subclass of `str` with some platform agnostic pathing support.

    For example, getting a named template, applying fields and converting to
    a platform specific path, where 'NUKESCRIPT' and 'windows' are defined in
    the TEMPLATES_ENV_NAME env: ::

        >>> t = get_template('NUKESCRIPT')
        >>> p = t.apply_fields(show='bunny',
                               sequence='abc',
                               shot='0100',
                               ask='comp',
                               version=1)
        >>> p.toPlatform('windows')
        '//projects/bunny/abc/0100/comp/nuke/bunny_abc_0100_comp.1.nk'
    """

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

    def toPlatform(self, platform: str = config.PLATFORM):
        """Converts path to platform.

        :param platform: name of platform to convert to.
        :returns: converted path.
        """
        if platform == self.platform:
            return str(self)
        fromRoot = get_template_environ(self.platform).get(TEMPLATES_ENV_ROOT)
        toRoot = get_template_environ(platform).get(TEMPLATES_ENV_ROOT)
        if not fromRoot or not toRoot:
            print("root value undefined for platform {}".format(platform))
            return
        return re.sub(r"^{}".format(fromRoot), toRoot, self.path)

    def toString(self):
        """Returns this path as a string."""
        return str(self)

    def scope(self):
        """Returns the scope for this path."""
        return os.path.dirname(str(self))


class Template(object):
    """Path Template class. ::

        >>> t = Template('/projects/{show}/{sequence}/{shot}/{task}')
        >>> p = t.apply_fields(show='bunny',
                               sequence='abc',
                               shot='010',
                               task='comp')
        >>> p.path
        '/projects/bunny/abc/010/comp'
        >>> t.get_fields('/projects/test/xyz/020/lighting')
        {'task': 'lighting', 'sequence': 'xyz', 'shot': '020', 'show': 'test'}

    With padded version numbers: ::

        >>> t = Template('/show/{show}/pub/{asset}/v{version:03d}')
        >>> p = t.apply_fields(show='foo', asset='bar', version=3)
        >>> p.path
        '/show/foo/pub/bar/v003'
    """

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
        :returns: resolved path as string.
        :raises: MissingFieldError.
        """
        formats = self.get_formats()

        def cast(k, v):
            fmt = formats.get(k, str)
            try:
                return fmt(v)
            except ValueError:
                raise Exception("{0} must be {1}".format(k, fmt.__name__))

        # reclass values based on field format in template
        formatted = dict((k, cast(k, v)) for k, v in fields.items())

        try:
            return Path(self.path_format.format(**formatted))

        except KeyError as err:
            raise MissingFieldError(err)  # noqa F405

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
        """Gets key/value pairs from path that map to template path.

        :param path: file system path as string.
        :returns: dict of key/value pairs.
        """
        # conform path and template slashes
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
                        index = tokens[i + 1 :].index(tokens[i])  # noqa F405
                        tokens[i + 1 + index] = back_ref
                except ValueError:
                    pass

        pattern = "".join(tokens)
        matches = re.match(pattern, path)
        # TODO: log/print info about what makes the path invalid
        # for example, {show} appears twice in template, but has
        # two different values in the path:
        # template: /projects/{show}/{shot}/{show}_{desc}.ext
        # filepath: /projects/bunny/tst001/bigbuck_cam.ext
        #                     ^^^^^        ^^^^^^^
        if not matches:
            raise InvalidPath(path)  # noqa F405

        # reclass values based on field format in template
        formats = self.get_formats()

        def cast(k, v):
            return formats.get(k, str)(v)

        return {k: cast(k, matches.group(k)) for k in keywords}


def extract_fields(filepath: str, template: Template):
    """Convenience function that extracts template fields from
    a given filepath for a given template name. For example: ::

        >>> envstack.extract_fields('/projects/bunny/vsr/vsr0100/comp/test.nk',
                                'TASKDIR')
        {'task': 'comp', 'sequence': 'vsr', 'shot': 'vsr0100', 'show': 'bunny'}

    :param filepath: path to file.
    :param template: Template instance, or name of template.
    :returns: dictionary of template fields.
    """
    try:
        p = Path(filepath)
        if isinstance(template, str):
            template = get_template(template, scope=p.scope())
        return template.get_fields(filepath)

    # path does not match template format
    except InvalidPath:  # noqa F405
        logger.log.debug(
            "path does not match template: {0} {1}".format(template, filepath)
        )
        return {}

    # unhandled errors
    except Exception as err:
        logger.log.debug("error extracting fields: {}".format(err))
        return {}


def get_scope(filepath: str):
    """Convenience function that returns the scope of a given filepath.

    :param filepath: filepath.
    :returns: scope of the filepath.
    """
    return Path(filepath).scope()


def get_template_environ(platform: str = config.PLATFORM, scope: str = None):
    """Returns default template Env instance defined by the value
    config.TEMPLATES_ENV_NAME.

    :param platform: optional platform name.
    :param scope: environment scope (default: cwd).
    :returns: Env instance.
    """
    from .env import load_environ

    return load_environ(TEMPLATES_ENV_NAME, platform=platform, scope=scope)


def get_template(name: str, platform: str = config.PLATFORM, scope: str = None):
    """Returns a Template instance for a given name. Template paths are
    defined by default in the env file set on config.TEMPLATES_ENV_NAME.

    For example, using 'NUKESCRIPT' as defined: ::

        >>> t = get_template('NUKESCRIPT')
        >>> t.apply_fields(show='bunny',
                           sequence='abc',
                           shot='0100',
                           task='comp',
                           version=1)
        <Path '/projects/bunny/abc/0100/comp/nuke/bunny_abc_0100_comp.1.nk'>

    :param name: name of template.
    :param platform: optional platform name.
    :param scope: environment scope (default: cwd).
    :returns: Template instance.
    """
    env = get_template_environ(platform, scope=scope)
    template = env.get(name)
    if not template:
        raise TemplateNotFound(name)  # noqa F405
    return Template(template)


def match_template(path: str, platform: str = config.PLATFORM, scope: str = None):
    """Returns a Template that matches a given `path`.

    :path: path to match Template.
    :param platform: optional platform name.
    :param scope: environment scope (default: cwd).
    :raises: ValueError if `path` matches multiple templates.
    :returns: matching Template or None.
    """
    env = get_template_environ(platform, scope=scope)

    # returns number of folders in a path
    numdirs = lambda p: str(p).replace("\\", "/").count("/")  # noqa E731

    # sort templates by number of folders
    ordered = sorted(env, key=lambda k: numdirs(env[k]), reverse=True)

    # stores the return value
    template = None

    # return first matching template or raise ValueError
    for name in ordered:
        try:
            path_format = env[name]
            template_test = Template(path_format)

            if template_test.get_fields(path):
                if template is None:
                    template = template_test

                elif numdirs(path_format) == numdirs(template.path_format):
                    raise ValueError("path matches more than one template")

        except InvalidPath:  # noqa F405
            continue

    return template
