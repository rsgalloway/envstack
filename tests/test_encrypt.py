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
Contains unit tests for the encrypt.py module.
"""

import unittest
from unittest.mock import patch

from envstack.encrypt import (
    AESGCMEncryptor,
    Base64Encryptor,
    FernetEncryptor,
)


class TestBase64Encryptor(unittest.TestCase):
    def setUp(self):
        self.encryptor = Base64Encryptor()

    def test_encrypt(self):
        """Test encrypting data using Base64Encryptor"""
        data = "my_secret"
        encrypted_data = self.encryptor.encrypt(data)
        self.assertIsInstance(encrypted_data, str)

    def test_decrypt(self):
        """Test decrypting data using Base64Encryptor"""
        data = "bXlfc2VjcmV0"
        decrypted_data = self.encryptor.decrypt(data)
        self.assertEqual(decrypted_data, "my_secret")


class TestAESGCMEncryptor(unittest.TestCase):
    def setUp(self):
        key = AESGCMEncryptor.generate_key()
        self.encryptor = AESGCMEncryptor(key=key)

    def test_encrypt_data(self):
        """Test encrypt_data"""
        data = "my_secret"
        encrypted_data = self.encryptor.encrypt_data(data)
        self.assertTrue(self.encryptor.key is not None)
        self.assertIsInstance(encrypted_data, dict)
        self.assertIn("nonce", encrypted_data)
        self.assertIn("ciphertext", encrypted_data)
        self.assertIn("tag", encrypted_data)

    def test_decrypt_data(self):
        """Test encrypt_data and decrypt_data"""
        data = "my_secret"
        self.assertTrue(self.encryptor.key is not None)
        encrypted_data = self.encryptor.encrypt_data(data)
        decrypted_data = self.encryptor.decrypt_data(encrypted_data)
        self.assertEqual(decrypted_data, b"my_secret")

    def test_encrypt_decrypt(self):
        """Test encrypting and decrypting data"""
        data = "my_secret"
        self.assertTrue(self.encryptor.key is not None)
        encrypted_data = self.encryptor.encrypt(data)
        decrypted_data = self.encryptor.decrypt(encrypted_data)
        self.assertEqual(decrypted_data, data)


class TestFernetEncryptor(unittest.TestCase):
    def setUp(self):
        key = FernetEncryptor.generate_key()
        self.encryptor = FernetEncryptor(key=key)

    def test_encrypt(self):
        """Test encrypting data using FernetEncryptor"""
        data = "my_secret"
        self.assertTrue(self.encryptor.key is not None)
        encrypted_data = self.encryptor.encrypt(data)
        self.assertIsInstance(encrypted_data, str)

    def test_decrypt(self):
        """Test encrypting and decrypting data"""
        data = "my_secret"
        self.assertTrue(self.encryptor.key is not None)
        encrypted_data = self.encryptor.encrypt(data)
        decrypted_data = self.encryptor.decrypt(encrypted_data)
        self.assertEqual(decrypted_data, "my_secret")


if __name__ == "__main__":
    unittest.main()
