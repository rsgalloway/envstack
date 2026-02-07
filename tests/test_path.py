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
Contains unit tests for the path.py module.
"""

import unittest
from unittest.mock import patch

from envstack.exceptions import MissingFieldError, TemplateNotFound
from envstack.path import Path, Template, extract_fields, get_template, match_template


def _fake_env(**kvs):
    """Helper to build a resolved env mapping for path tests."""
    return dict(kvs)


class TestTemplate(unittest.TestCase):
    def test_get_keywords(self):
        """Ensures get_keywords returns the correct list of keywords from the
        template string."""
        t = Template("/mnt/projects/{show}/{seq}/{shot}")
        self.assertEqual(t.get_keywords(), ["show", "seq", "shot"])

    def test_apply_fields_success(self):
        """Ensures apply_fields can successfully apply all required fields to
        produce a"""
        t = Template("/mnt/projects/{show}/{seq}/{shot}")
        p = t.apply_fields(show="demo", seq="aa", shot="010")
        self.assertEqual(str(p), "/mnt/projects/demo/aa/010")

    def test_apply_fields_missing_raises(self):
        """Ensures apply_fields raises MissingFieldError if any keywords in the
        template"""
        t = Template("/mnt/projects/{show}/{seq}/{shot}")
        with self.assertRaises(MissingFieldError):
            t.apply_fields(show="demo", seq="aa")  # missing shot

    def test_get_fields_success(self):
        """Ensures get_fields can extract fields from a path that matches the
        template."""
        t = Template("/mnt/projects/{show}/{seq}/{shot}")
        fields = t.get_fields("/mnt/projects/demo/aa/010")
        self.assertEqual(fields, {"show": "demo", "seq": "aa", "shot": "010"})


class TestGetTemplate(unittest.TestCase):
    def test_get_template_expands_envvars_then_fields(self):
        """Ensures ${ROOT} is expanded from the resolved env before applying
        {seq}/{shot}."""
        env = _fake_env(
            ROOT="/mnt/pipe",
            NUKESCRIPT="${ROOT}/projects/{seq}/{shot}/comp/{seq}_{shot}.{version}.nk",
        )

        with patch("envstack.path._load_resolved_stack", return_value=env):
            t = get_template("NUKESCRIPT", stack="fps", scope="/tmp")
            p = t.apply_fields(seq="aa", shot="010", version="0001")
            self.assertEqual(
                str(p),
                "/mnt/pipe/projects/aa/010/comp/aa_010.0001.nk",
            )

    def test_get_template_missing_raises(self):
        """Ensures get_template raises TemplateNotFound if the template name is
        not found in the resolved env."""
        env = _fake_env(ROOT="/mnt/pipe")
        with patch("envstack.path._load_resolved_stack", return_value=env):
            with self.assertRaises(TemplateNotFound):
                get_template("DOES_NOT_EXIST", stack="fps", scope="/tmp")

    def test_get_template_can_disable_envvar_expansion(self):
        """Ensures get_template can return a template with unexpanded envvars
        when expand_envvars=False."""
        env = _fake_env(
            ROOT="/mnt/pipe",
            SEQDIR="${ROOT}/projects/{seq}",
        )
        with patch("envstack.path._load_resolved_stack", return_value=env):
            t = get_template("SEQDIR", stack="fps", scope="/tmp", expand_envvars=False)
            # should preserve ${ROOT} literally
            p = t.apply_fields(seq="aa")
            self.assertEqual(str(p), "${ROOT}/projects/aa")


class TestMatchTemplate(unittest.TestCase):
    def test_match_template_picks_most_specific(self):
        """Ensures that if multiple templates match a path, the one with more
        keywords is preferred."""
        env = _fake_env(
            ROOT="/mnt/pipe",
            SEQDIR="${ROOT}/projects/{seq}",
            SHOTDIR="${ROOT}/projects/{seq}/{shot}",
        )
        with patch("envstack.path._load_resolved_stack", return_value=env):
            t = match_template("/mnt/pipe/projects/aa/010", stack="fps", scope="/tmp")
            self.assertIsNotNone(t)
            self.assertEqual(str(t), "/mnt/pipe/projects/{seq}/{shot}")

    def test_match_template_picks_no_expansion(self):
        """Ensures match_template can match against templates with unexpanded envvars."""
        env = _fake_env(
            ROOT="/mnt/pipe",
            SEQDIR="${ROOT}/projects/{seq}",
        )
        with patch("envstack.path._load_resolved_stack", return_value=env):
            t = match_template(
                "${ROOT}/projects/aa", stack="fps", scope="/tmp", expand_envvars=False
            )
            self.assertIsNotNone(t)
            self.assertEqual(str(t), "${ROOT}/projects/{seq}")

    def test_match_template_none_when_no_match(self):
        """Ensures match_template returns None if no templates match the path."""
        env = _fake_env(
            ROOT="/mnt/pipe",
            SEQDIR="${ROOT}/projects/{seq}",
        )
        with patch("envstack.path._load_resolved_stack", return_value=env):
            t = match_template("/some/other/path", stack="fps", scope="/tmp")
            self.assertEqual(t, None)


class TestExtractFields(unittest.TestCase):
    def test_extract_fields_with_template_name(self):
        env = _fake_env(
            ROOT="/mnt/pipe",
            SHOTDIR="${ROOT}/projects/{seq}/{shot}",
        )
        with patch("envstack.path._load_resolved_stack", return_value=env):
            fields = extract_fields(
                "/mnt/pipe/projects/aa/010",
                "SHOTDIR",
                stack="fps",
            )
            self.assertEqual(fields, {"seq": "aa", "shot": "010"})


class TestPathToPlatform(unittest.TestCase):
    def test_to_platform_rewrites_root(self):
        """
        Ensures Path.to_platform uses per-platform ROOT loaded from the same stack.
        """
        env_linux = _fake_env(ROOT="/mnt/pipe")
        env_windows = _fake_env(ROOT="//tools/pipe")

        def _fake_load(stack, platform, scope):
            if platform in ("windows", "win32"):
                return env_windows
            return env_linux

        with patch("envstack.path._load_resolved_stack", side_effect=_fake_load):
            p = Path("/mnt/pipe/projects/aa/010", platform="linux")
            out = p.to_platform(platform="windows", stack="fps", scope="/tmp")
            self.assertEqual(out, "//tools/pipe/projects/aa/010")


if __name__ == "__main__":
    unittest.main()
