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
Contains unit tests for the node.py module.
"""

import os
import shutil
import sys
import tempfile
import unittest
from base64 import b64encode
from hashlib import md5

import yaml

from envstack.encrypt import AESGCMEncryptor, FernetEncryptor
from envstack.env import Source
from envstack.node import (
    Base64Node,
    CustomDumper,
    CustomLoader,
    EncryptedNode,
    FernetNode,
    MD5Node,
    Template,
)

# path to env stack file directory
envpath = os.path.join(os.path.dirname(__file__), "..", "env")


class TestBase64Node(unittest.TestCase):
    def test_from_yaml(self):
        """test the base64 from_yaml method"""
        node = Base64Node.from_yaml(None, yaml.ScalarNode("tag", "value"))
        self.assertEqual(node.value, "value")

    def test_to_yaml(self):
        """test the base64 to_yaml method"""
        node = Base64Node("value")
        dumper = CustomDumper(None)
        result = node.to_yaml(dumper, node)
        expected_value = b64encode("value".encode()).decode()
        self.assertIsInstance(result, yaml.ScalarNode)
        self.assertEqual(result.tag, Base64Node.yaml_tag)
        self.assertEqual(result.value, expected_value)

    def test_resolve(self):
        """test the base64 resolve method"""
        value = b64encode("value".encode()).decode()
        node = Base64Node(value)
        self.assertEqual(node.value, value)
        result = node.resolve()
        self.assertEqual(result, "value")


class TestMD5Node(unittest.TestCase):
    def test_from_yaml(self):
        """test the MD5 from_yaml method"""
        node = MD5Node.from_yaml(None, yaml.ScalarNode("tag", "value"))
        self.assertEqual(node.value, "value")

    def test_to_yaml(self):
        """test the MD5 to_yaml method"""
        node = MD5Node("value")
        dumper = CustomDumper(None)
        result = node.to_yaml(dumper, node)
        expected_value = md5("value".encode()).hexdigest()
        self.assertIsInstance(result, yaml.ScalarNode)
        self.assertEqual(result.tag, MD5Node.yaml_tag)
        self.assertEqual(result.value, expected_value)


class TestEncryptedNode(unittest.TestCase):
    def test_from_yaml(self):
        """test the EncryptedNode from_yaml method"""
        node = EncryptedNode.from_yaml(None, yaml.ScalarNode("tag", "value"))
        self.assertEqual(node.value, "value")

    def test_to_yaml(self):
        """test the EncryptedNode to_yaml method"""
        node = EncryptedNode("value")
        dumper = CustomDumper(None)
        result = node.to_yaml(dumper, node)
        self.assertIsInstance(result, yaml.ScalarNode)
        self.assertEqual(result.tag, EncryptedNode.yaml_tag)

    def test_resolve_fail(self):
        """test the EncryptedNode resolve method with different keys"""
        key1 = AESGCMEncryptor.generate_key()
        os.environ[AESGCMEncryptor.KEY_VAR_NAME] = key1
        value = "super_secret_password"
        encrypted = AESGCMEncryptor().encrypt(value)
        node = EncryptedNode.from_yaml(
            None, yaml.ScalarNode(EncryptedNode.yaml_tag, encrypted)
        )
        key2 = AESGCMEncryptor.generate_key()
        os.environ[AESGCMEncryptor.KEY_VAR_NAME] = key2
        resolved = node.resolve()
        self.assertEqual(resolved, encrypted)

    def test_resolve_invalid_key(self):
        """test the EncryptedNode resolve method with an invalid key"""
        os.environ[AESGCMEncryptor.KEY_VAR_NAME] = "invalid"
        value = "super_secret_password"
        with self.assertRaises(ValueError):
            AESGCMEncryptor().encrypt(value)

    def test_resolve_success(self):
        """test the EncryptedNode resolve method with a valid key"""
        key = AESGCMEncryptor.generate_key()
        os.environ[AESGCMEncryptor.KEY_VAR_NAME] = key
        value = "super_secret_password"
        encrypted = AESGCMEncryptor().encrypt(value)
        node = EncryptedNode.from_yaml(
            None, yaml.ScalarNode(EncryptedNode.yaml_tag, encrypted)
        )
        self.assertEqual(node.value, encrypted)
        resolved = node.resolve()
        self.assertEqual(resolved, value)


class TestTemplate(unittest.TestCase):
    def test_init(self):
        """test the Template __init__ method"""
        template = Template("value")
        self.assertEqual(template.value, "value")

    def test_repr(self):
        """test the Template __repr__ method"""
        template = Template("value")
        result = repr(template)
        self.assertEqual(result, "Template(value=value)")

    def test_str(self):
        """test the Template __str__ method"""
        template = Template("value")
        result = str(template)
        self.assertEqual(result, "value")


class TestCustomLoader(unittest.TestCase):
    def test_construct_mapping(self):
        """test the CustomLoader construct_mapping method"""
        envfile = os.path.join(envpath, "test.env")
        loader = CustomLoader(open(envfile, "r"))
        node = yaml.MappingNode("tag", [])
        mapping = loader.construct_mapping(node)
        self.assertIsInstance(mapping, dict)


class TestCustomDumper(unittest.TestCase):
    def test_init(self):
        """test the CustomDumper __init__ method"""
        dumper = CustomDumper(None)
        self.assertEqual(dumper.depth, 0)
        self.assertIsNone(dumper.basekey)
        self.assertEqual(dumper.newanchors, {})

    def test_anchor_node(self):
        """test the CustomDumper anchor_node method"""
        dumper = CustomDumper(None)
        node = yaml.ScalarNode("tag", "value")
        dumper.anchor_node(node)
        self.assertEqual(dumper.depth, 1)
        self.assertEqual(dumper.basekey, None)
        self.assertEqual(dumper.newanchors, {})

        dumper.depth = 1
        dumper.anchor_node(node)
        self.assertEqual(dumper.depth, 2)
        self.assertEqual(dumper.basekey, "value")
        self.assertEqual(dumper.newanchors, {})

        dumper.depth = 2
        dumper.anchor_node(node)
        self.assertEqual(dumper.depth, 3)
        self.assertEqual(dumper.basekey, "value")

    def test_represent_list(self):
        """test the CustomDumper represent_list method"""
        dumper = CustomDumper(None)
        data = [1, 2, 3]
        result = dumper.represent_list(data)
        self.assertIsInstance(result, yaml.SequenceNode)
        self.assertFalse(result.flow_style)


class TestSecretsEnv(unittest.TestCase):
    """Test the secrets.env file"""

    def setUp(self):
        """set up the test environment"""
        self.root = tempfile.mkdtemp()
        os.environ[AESGCMEncryptor.KEY_VAR_NAME] = (
            "jHLNsFrhs9JsjuPkNhYX5ubwLpId2ZSxcFXAkHyMjOU="
        )
        os.environ[FernetEncryptor.KEY_VAR_NAME] = (
            "v4-Ry7uKSOBEXMDv9x_crBBpi0eo2WCYNAIlSB1t4VE="
        )

    def tearDown(self):
        """tear down the test environment"""
        shutil.rmtree(self.root)
        del os.environ[AESGCMEncryptor.KEY_VAR_NAME]
        del os.environ[FernetEncryptor.KEY_VAR_NAME]

    def test_encrypted_nodes(self):
        """test loading and dumping encrypted nodes"""
        envfile = os.path.join(envpath, "secrets.env")
        testfile1 = os.path.join(self.root, "test1.env")
        testfile2 = os.path.join(self.root, "test2.env")
        root = {
            "linux": "/mnt/pipe",
            "win32": "X:/pipe",
            "darwin": "/Volumes/pipe",
        }.get(sys.platform)

        # load the stack file and verify the encrypted values
        s1 = Source(envfile)
        d1 = s1.load()
        self.assertTrue(isinstance(d1["KEY"], Base64Node))
        self.assertTrue(isinstance(d1["SECRET"], EncryptedNode))
        self.assertTrue(isinstance(d1["PASSWORD"], FernetNode))
        self.assertNotEqual(d1["KEY"].value, None)
        self.assertNotEqual(d1["SECRET"].value, None)
        self.assertNotEqual(d1["PASSWORD"].value, None)
        self.assertEqual(d1["KEY"].resolve(), "This is encrypted")
        self.assertEqual(d1["SECRET"].resolve(), "my_super_secret_password")
        self.assertEqual(d1["PASSWORD"].resolve(), "password")
        s1.write(testfile1)

        # duplicating the stack file should preserve the encrypted values
        s2 = Source(testfile1)
        d2 = s2.load()
        self.assertTrue(isinstance(d2["KEY"], Base64Node))
        self.assertTrue(isinstance(d2["SECRET"], EncryptedNode))
        self.assertTrue(isinstance(d2["PASSWORD"], FernetNode))
        self.assertEqual(d1["KEY"].value, d2["KEY"].value)
        self.assertEqual(d1["SECRET"].value, d2["SECRET"].value)
        self.assertEqual(d1["PASSWORD"].value, d2["PASSWORD"].value)

        # make some modifications
        updated_value_key = "this is a secret"
        updated_value_md5 = "this is hashed"
        updated_value_secret = "super_secret_password"
        updated_value_password = "other_password"
        s1.data["all"]["KEY"] = Base64Node(updated_value_key)
        s1.data["all"]["MD5"] = MD5Node(updated_value_md5)
        s1.data["all"]["SECRET"] = EncryptedNode(updated_value_secret)
        s1.data["all"]["PASSWORD"] = FernetNode(updated_value_password)
        s1.data["darwin"]["ROOT"] = root
        s1.data["linux"]["ROOT"] = root
        s1.data["windows"]["ROOT"] = root
        s1.write(testfile2)

        # verify the values were updated
        s3 = Source(testfile2)
        d3 = s3.load()
        self.assertEqual(d3["ROOT"], root)
        self.assertTrue(isinstance(d3["KEY"], Base64Node))
        self.assertTrue(isinstance(d3["MD5"], MD5Node))
        self.assertTrue(isinstance(d3["SECRET"], EncryptedNode))
        self.assertTrue(isinstance(d3["PASSWORD"], FernetNode))
        self.assertNotEqual(d3["KEY"].value, updated_value_key)
        self.assertNotEqual(d3["MD5"].value, updated_value_md5)
        self.assertNotEqual(d3["SECRET"].value, updated_value_secret)
        self.assertNotEqual(d3["PASSWORD"].value, updated_value_password)
        self.assertEqual(d3["KEY"].resolve(), updated_value_key)
        self.assertEqual(d3["MD5"].resolve(), d3["MD5"].value)  # cannot unhash
        self.assertEqual(d3["SECRET"].resolve(), updated_value_secret)
        self.assertEqual(d3["PASSWORD"].resolve(), updated_value_password)


if __name__ == "__main__":
    unittest.main()
