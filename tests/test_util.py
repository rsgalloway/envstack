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

import os
import unittest

from envstack import config
from envstack.exceptions import CyclicalReference
from envstack.util import encode, evaluate_modifiers, get_stack_name, safe_eval


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

    def test_default_value_empty_env(self):
        expression = "${VAR:=default}"
        environ = {}
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, "default")

    def test_default_value_with_default_args(self):
        expression = "${HELLO:=world}"
        result = evaluate_modifiers(expression)
        self.assertEqual(result, os.getenv("HELLO", "world"))

    def test_error_message(self):
        expression = "${VAR:?error message}"
        environ = {"VAR": "hello"}
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, "hello")

    def test_error_message_raise(self):
        expression = "${VAR:?error message}"
        environ = {}
        with self.assertRaises(ValueError):
            evaluate_modifiers(expression, environ)

    def test_cyclical_reference_error(self):
        expression = "${VAR}"
        environ = {"VAR": "${FOO}", "FOO": "${BAR}", "BAR": "${VAR}"}
        with self.assertRaises(CyclicalReference):
            evaluate_modifiers(expression, environ)

    def test_multiple_substitutions(self):
        expression = "${VAR}/${FOO:=foobar}/${BAR:?error message}"
        environ = {"VAR": "hello", "BAR": "world"}
        result = evaluate_modifiers(expression, environ)
        self.assertEqual(result, "hello/foobar/world")


class TestUtils(unittest.TestCase):
    def test_encode(self):
        env = {
            "VAR1": "value1",
            "VAR2": 1,
            "VAR3": 4.5,
        }
        encoded_env = encode(env)
        expected_encoded_env = {
            "VAR1": "value1",
            "VAR2": "1",
            "VAR3": "4.5",
        }
        self.assertEqual(encoded_env, expected_encoded_env)

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
        self.assertEqual(result, config.DEFAULT_NAMESPACE)

    def test_get_stack_name_invalid_type(self):
        name = 123
        with self.assertRaises(ValueError):
            get_stack_name(name)


class TestSafeEval(unittest.TestCase):
    def test_safe_eval_string(self):
        value = "hello"
        result = safe_eval(value)
        self.assertEqual(result, "hello")

    def test_safe_eval_integer(self):
        value = "123"
        result = safe_eval(value)
        self.assertEqual(result, 123)

    def test_safe_eval_float(self):
        value = "3.14"
        result = safe_eval(value)
        self.assertEqual(result, 3.14)

    def test_safe_eval_list(self):
        value = "['a', 'b', 'c']"
        result = safe_eval(value)
        self.assertEqual(result, ["a", "b", "c"])

    def test_safe_eval_dict(self):
        value = "{'key': 'value'}"
        result = safe_eval(value)
        self.assertEqual(result, {"key": "value"})

    def test_safe_eval_invalid_value(self):
        value = "invalid"
        result = safe_eval(value)
        self.assertEqual(result, "invalid")


class TestIssue18(unittest.TestCase):
    def test_non_cyclical_reference_error_1(self):
        expression = "${FOO}"
        environ = {"FOO": "${FOO}"}
        self.assertEqual(evaluate_modifiers(expression, environ), "")

    def test_non_cyclical_reference_error_2(self):
        expression = "${FOO}"
        environ = {"FOO": "foo:${FOO}"}
        self.assertEqual(evaluate_modifiers(expression, environ), "foo:")

    def test_non_cyclical_reference_error_3(self):
        expression = "${FOO}"
        environ = {"FOO": "bar/${FOO}"}
        self.assertEqual(evaluate_modifiers(expression, environ), "bar/")

    def test_cyclical_reference_error_1(self):
        expression = "${VAR}"
        environ = {"VAR": "${FOO}", "FOO": "${BAR}", "BAR": "${VAR}"}
        with self.assertRaises(CyclicalReference):
            evaluate_modifiers(expression, environ)

    def test_cyclical_reference_error_2(self):
        expression = "${FOO}"
        environ = {"FOO": "${BAR}", "BAR": "${FOO}"}
        with self.assertRaises(CyclicalReference):
            evaluate_modifiers(expression, environ)


if __name__ == "__main__":
    unittest.main()
