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
Contains unit tests for the encrypt.py module.
"""

import os
import unittest
from unittest.mock import patch

from envstack.encrypt import (
    KEY_VAR_NAME,
    b64encode,
    get_encryption_key,
    encrypt_data,
    decrypt_data,
    pad_data,
    unpad_data,
    compact_store,
    compact_load,
    encrypt,
    decrypt,
)


class TestEncrypt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """set up a test encryption key"""
        cls.key = os.urandom(32)

    def test_get_encryption_key_existing_key(self):
        """test getting an existing encryption key from environment variable"""
        with patch.dict(os.environ, {KEY_VAR_NAME: "VGVzdA=="}):
            key = get_encryption_key()
            self.assertEqual(key, b"Test")

    def test_get_encryption_key_new_key(self):
        """test generating a new encryption key and storing it in environment variable"""
        with patch.dict(os.environ, clear=True):
            key = get_encryption_key()
            self.assertIsInstance(key, bytes)
            self.assertEqual(len(key), 32)
            self.assertEqual(os.environ[KEY_VAR_NAME], b64encode(key).decode())

    def test_encrypt_data(self):
        """test encrypting data"""
        secret = "my_secret"
        encrypted_data = encrypt_data(secret, self.key)
        self.assertIsInstance(encrypted_data, dict)
        self.assertIn("nonce", encrypted_data)
        self.assertIn("ciphertext", encrypted_data)
        self.assertIn("tag", encrypted_data)

    def test_decrypt_data(self):
        """test encrypting and decrypting data"""
        secret = "my_secret"
        encrypted_data = encrypt_data(secret, self.key)
        decrypted_data = decrypt_data(encrypted_data, self.key)
        self.assertEqual(decrypted_data, b"my_secret")

    def test_pad_data(self):
        """test padding data"""
        data = "test"
        padded_data = pad_data(data)
        self.assertIsInstance(padded_data, bytes)

    def test_unpad_data(self):
        """test unpadding data, with valid PKCS7 padding"""
        padded_data = b"test"
        padding_length = 16 - (len(padded_data) % 16)
        padded_data += bytes([padding_length]) * padding_length
        unpadded_data = unpad_data(padded_data)
        self.assertEqual(unpadded_data, b"test")

    def test_compact_store(self):
        """test compacting and storing data"""
        encrypted_data = {
            "nonce": "VGVzdA==",
            "ciphertext": "VGVzdA==",
            "tag": "VGVzdA==",
        }
        compacted_data = compact_store(encrypted_data)
        self.assertIsInstance(compacted_data, str)

    def test_compact_load(self):
        """test loading and separating compacted data"""
        compacted_data = "VGVzdA==VGVzdA==VGVzdA=="
        loaded_data = compact_load(compacted_data)
        self.assertIsInstance(loaded_data, dict)
        self.assertIn("nonce", loaded_data)
        self.assertIn("ciphertext", loaded_data)
        self.assertIn("tag", loaded_data)

    def test_encrypt(self):
        """test encrypting a secret"""
        secret = "my_secret"
        encrypted_secret = encrypt(secret)
        self.assertIsInstance(encrypted_secret, str)

    def test_decrypt(self):
        """test decrypting a secret"""
        encrypted_secret = "VGVzdA==VGVzdA==VGVzdA=="
        decrypted_secret = decrypt(encrypted_secret)
        self.assertIsInstance(decrypted_secret, str)


class TestExamples(unittest.TestCase):
    def test_misc(self):
        """various example usage tests"""
        key = get_encryption_key()

        # encrypt a secret
        secret = "my_super_secret_password"
        encrypted = encrypt_data(secret, key)
        self.assertEqual(type(encrypted), dict)

        # example usage
        compact_data = compact_store(encrypted)
        self.assertEqual(type(compact_data), str)

        reconstructed_data = compact_load(compact_data)
        self.assertEqual(encrypted, reconstructed_data)

        # decrypt using reconstructed data
        decrypted = decrypt_data(reconstructed_data, key)
        self.assertEqual(secret, decrypted.decode())


if __name__ == "__main__":
    unittest.main()
