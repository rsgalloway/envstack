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
Contains cryptography classes and functions.
"""

import base64
import binascii
import os
import secrets
from base64 import b64decode, b64encode

import cryptography.exceptions
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from envstack.logger import log


class Base64Encryptor(object):
    """Encrypt and decrypt secrets using base64 encoding."""

    def __init__(self):
        super().__init__()

    def encrypt(self, data: str):
        """Encrypt a secret using base64 encoding."""
        return b64encode(str(data).encode()).decode()

    def decrypt(self, data: str):
        """Decrypt a secret using base64 encoding."""
        try:
            return b64decode(data).decode()
        except UnicodeDecodeError as e:
            log.debug("invalid base64 encoding: %s", e)
            return data


class FernetEncryptor(object):
    """Encrypt and decrypt secrets using Fernet symmetric encryption."""

    KEY_VAR_NAME = "ENVSTACK_FERNET_KEY"

    def __init__(self, key: str = None, env: dict = os.environ):
        if key:
            self.key = Fernet(key)
        else:
            self.key = self.get_key(env)

    def get_key(self, env: dict = os.environ):
        """Load or generate the encryption key and store in ${ENVSTACK_FERNET_KEY}.

        By default, this function looks for base64 key in `env`. If not found,
        it generates a new 256-bit key and stores it in os.environ.

        :param env: The environment to look for a key.
        :return: encryption key.
        """
        key = env.get(self.KEY_VAR_NAME)
        if key:
            return Fernet(key)
        else:
            key = Fernet.generate_key()
            # load_environ iterates over env, so we can't modify it in the loop:
            # RuntimeError: dictionary changed size during iteration
            # env[var_name] = b64encode(key).decode()
            os.environ[self.KEY_VAR_NAME] = key.decode()
            log.info(f"set {self.KEY_VAR_NAME}: {key.decode()}")
            return Fernet(key)

    def encrypt(self, data: str):
        """Encrypt a secret using Fernet.

        :param data: The secret to encrypt.
        :return: Base64-encoded binary blob.
        """
        results = ""
        if not data:
            return results
        try:
            results = self.key.encrypt(str(data).encode()).decode()
        except InvalidToken:
            log.error("invalid encryption key")
        except ValueError as e:
            log.error("invalid value: %s", data)
        except Exception as e:
            log.error("unhandled error: %s", e)
        finally:
            return results

    def decrypt(self, data: str):
        """Decrypt a secret using Fernet.

        :param data: Base64-encoded binary blob.
        :return: The decrypted secret.
        """
        results = ""
        if not data:
            return results
        try:
            results = self.key.decrypt(str(data).encode()).decode()
        except InvalidToken:
            log.error("invalid encryption key")
        except ValueError as e:
            log.error("invalid value: %s", data)
        except Exception as e:
            log.error("unhandled error: %s", e)
        finally:
            return results


class AESGCMEncryptor(object):
    """Encrypt and decrypt secrets using AES-GCM symmetric encryption."""

    KEY_VAR_NAME = "ENVSTACK_SYMMETRIC_KEY"

    def __init__(self, key: str = None, env: dict = os.environ):
        if key:
            self.key = key
        else:
            self.key = self.get_key(env)

    def get_key(self, env: dict = os.environ):
        """Load or generate the encryption key and store in ${ENVSTACK_SYMMETRIC_KEY}.

        By default, this function looks for base64 key in `env`. If not found,
        it generates a new 256-bit key and stores it in os.environ.

        :param env: The environment to use.
        :return: 256-bit encryption key.
        """
        key = env.get(self.KEY_VAR_NAME)
        if key:
            try:
                return b64decode(key)
            except binascii.Error as e:
                raise ValueError("invalid base64 encoding: %s" % e)
        else:
            key = secrets.token_bytes(32)  # 32 bytes = 256 bits
            # load_environ iterates over env, so we can't modify it in the loop:
            # RuntimeError: dictionary changed size during iteration
            # env[var_name] = b64encode(key).decode()
            os.environ[self.KEY_VAR_NAME] = b64encode(key).decode()
            log.info(f"set {self.KEY_VAR_NAME}: {b64encode(key).decode()}")
            return key

    def encrypt_data(self, secret: str):
        """Encrypt a secret using AES-GCM.

        :param secret: The secret to encrypt.
        :param key: The encryption key.
        :return: Dictionary containing nonce, ciphertext, and tag.
        """
        nonce = os.urandom(12)  # GCM requires a 12-byte nonce
        cipher = Cipher(algorithms.AES(self.key), modes.GCM(nonce))
        encryptor = cipher.encryptor()
        padded_data = pad_data(secret)
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()
        return {
            "nonce": b64encode(nonce).decode(),
            "ciphertext": b64encode(ciphertext).decode(),
            "tag": b64encode(encryptor.tag).decode(),
        }

    def decrypt_data(self, encrypted_data: dict):
        """Decrypt a secret using AES-GCM.

        :param encrypted_data: Dictionary containing nonce, ciphertext, and tag.
        :param key: The encryption key.
        :returns: The decrypted secret.
        """
        nonce = b64decode(encrypted_data["nonce"])
        ciphertext = b64decode(encrypted_data["ciphertext"])
        tag = b64decode(encrypted_data["tag"])
        cipher = Cipher(algorithms.AES(self.key), modes.GCM(nonce, tag))
        decryptor = cipher.decryptor()
        padded_data = decryptor.update(ciphertext) + decryptor.finalize()
        return unpad_data(padded_data)

    def encrypt(self, data: str):
        """Convenience function to encrypt a secret using AES-GCM.

        :param data: The data to encrypt.
        :returns: Base64-encoded binary blob.
        """
        results = ""
        if not data:
            return results
        try:
            encrypted_data = self.encrypt_data(data)
            results = compact_store(encrypted_data)
        except binascii.Error as e:
            log.error("invalid base64 encoding: %s", e)
        except cryptography.exceptions.InvalidTag as e:
            log.error("invalid encryption key")
        except ValueError as e:
            log.error("invalid value: %s", data)
        except Exception as e:
            log.error("unhandled error: %s", e)
        finally:
            return results

    def decrypt(self, data: str):
        """Convenience function to decrypt a secret using AES-GCM.

        :param data: Base64-encoded binary blob.
        :returns: The decrypted secret.
        """
        results = ""
        if not data:
            return results
        try:
            encrypted_data = compact_load(data)
            decrypted = self.decrypt_data(encrypted_data)
            results = decrypted.decode()
        except binascii.Error as e:
            log.error("invalid base64 encoding: %s", e)
        except cryptography.exceptions.InvalidTag as e:
            log.error("invalid encryption key")
        except ValueError as e:
            log.error("invalid value: %s", data)
        except Exception as e:
            log.error("unhandled error: %s", e)
        finally:
            return results


def pad_data(data: str):
    """Pad data to be block-aligned for AES encryption.

    :param data: The data to pad.
    :returns: The padded data.
    """
    padder = padding.PKCS7(algorithms.AES.block_size).padder()
    return padder.update(str(data).encode()) + padder.finalize()


def unpad_data(data: dict):
    """Unpad data after decryption.

    :param data: The data to unpad.
    :returns: The unpadded data.
    """
    unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
    return unpadder.update(data) + unpadder.finalize()


def compact_store(encrypted_data: dict):
    """Combine nonce, ciphertext, and tag into a single binary blob.

    :param encrypted_data: Dictionary containing nonce, ciphertext, and tag.
    :returns: Base64-encoded binary blob.
    """
    # convert all parts to binary (bytes) if they are in base64
    nonce = base64.b64decode(encrypted_data["nonce"])
    ciphertext = base64.b64decode(encrypted_data["ciphertext"])
    tag = base64.b64decode(encrypted_data["tag"])

    # concatenate and encode to base64 for storage
    return base64.b64encode(nonce + ciphertext + tag).decode()


def compact_load(compact_data: str):
    """Separate nonce, ciphertext, and tag from a compact binary blob.

    :param compact_data: Base64-encoded binary blob.
    :returns: Dictionary containing nonce, ciphertext, and tag.
    """
    # decode the base64-encoded string
    binary_data = base64.b64decode(compact_data)

    # extract parts:
    # - nonce (12 bytes)
    # - ciphertext (remaining bytes - 16 bytes)
    # - tag (16 bytes)
    nonce = binary_data[:12]
    tag = binary_data[-16:]
    ciphertext = binary_data[12:-16]

    # return the parts in Base64 format for compatibility with the encrypt/
    # decrypt functions
    return {
        "nonce": base64.b64encode(nonce).decode(),
        "ciphertext": base64.b64encode(ciphertext).decode(),
        "tag": base64.b64encode(tag).decode(),
    }
