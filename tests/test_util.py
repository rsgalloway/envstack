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
Contains unit tests for the util.py module.
"""

import unittest
from envstack.util import evaluate_modifiers, get_stack_name


class TestEvaluateModifiers(unittest.TestCase):
    def test_no_substitution(self):
        expression = "world"
        result = evaluate_modifiers(expression)
        self.assertEqual(result, "world")

    def test_direct_substitution(self):
        expression = "${VAR}"
        environ = {"VAR": "hello"}
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, "hello")

    def test_default_value(self):
        expression = "${VAR:=default}"
        environ = {"VAR": "hello"}
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, "hello")

        expression = "${VAR:=default}"
        environ = {}
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, "default")

    def test_error_message(self):
        expression = "${VAR:?error message}"
        environ = {"VAR": "hello"}
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, "hello")

        expression = "${VAR:?error message}"
        environ = {}
        with self.assertRaises(ValueError):
            evaluate_modifiers(expression, environ)

    def test_multiple_substitutions(self):
        expression = "${VAR}/${FOO:=default}/${BAR:?error message}"
        environ = {"VAR": "hello", "BAR": "world"}
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, "hello/default/world")


class TestEvaluateModifiers(unittest.TestCase):
    def test_get_stack_name_string(self):
        name = "stack_name"
        result = get_stack_name(name)
        self.assertEqual(result, "stack_name")

    def test_get_stack_name_tuple(self):
        name = ("namespace", "stack_name")
        result = get_stack_name(name)
        self.assertEqual(result, "stack_name")

    def test_get_stack_name_list(self):
        name = ["namespace", "stack_name"]
        result = get_stack_name(name)
        self.assertEqual(result, "stack_name")

    def test_get_stack_name_empty(self):
        name = []
        result = get_stack_name(name)
        self.assertEqual(result, "")

    def test_get_stack_name_invalid_type(self):
        name = 123
        with self.assertRaises(ValueError):
            get_stack_name(name)


if __name__ == "__main__":
    unittest.main()
