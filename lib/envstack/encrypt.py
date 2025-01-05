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
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from envstack.logger import log

# environment variable to store the encryption key
KEY_VAR_NAME = "SYMMETRIC_KEY"


def get_encryption_key(var_name: str = KEY_VAR_NAME, env: dict = os.environ):
    """
    Load or generate the encryption key. Store in environment variable.
    By default, this function looks for base64 key in the ${SYMMETRIC_KEY}
    environment variable. If not found, generates a new 256-bit key and stores
    it in the environment.

    :param var_name: The environment variable to use for the key.
    :param env: The environment to use.
    :return: 256-bit encryption key.
    """
    key_env = env.get(var_name)
    if key_env:
        return b64decode(key_env)
    else:
        key = secrets.token_bytes(32)  # 32 bytes = 256 bits
        # load_environ iterates over env, so we can't modify it in the loop:
        # RuntimeError: dictionary changed size during iteration
        # env[var_name] = b64encode(key).decode()
        os.environ[var_name] = b64encode(key).decode()
        log.info(f"set {var_name}: {b64encode(key).decode()}")
        return key


def encrypt_data(secret: str, key: str):
    """Encrypt a secret using AES-GCM.

    :param secret: The secret to encrypt.
    :param key: The encryption key.
    :return: Dictionary containing nonce, ciphertext, and tag.
    """
    nonce = os.urandom(12)  # GCM requires a 12-byte nonce
    cipher = Cipher(algorithms.AES(key), modes.GCM(nonce))
    encryptor = cipher.encryptor()
    padded_data = pad_data(secret)
    ciphertext = encryptor.update(padded_data) + encryptor.finalize()
    return {
        "nonce": b64encode(nonce).decode(),
        "ciphertext": b64encode(ciphertext).decode(),
        "tag": b64encode(encryptor.tag).decode(),
    }


def decrypt_data(encrypted_data: dict, key: str):
    """Decrypt a secret using AES-GCM.

    :param encrypted_data: Dictionary containing nonce, ciphertext, and tag.
    :param key: The encryption key.
    :returns: The decrypted secret.
    """
    nonce = b64decode(encrypted_data["nonce"])
    ciphertext = b64decode(encrypted_data["ciphertext"])
    tag = b64decode(encrypted_data["tag"])
    cipher = Cipher(algorithms.AES(key), modes.GCM(nonce, tag))
    decryptor = cipher.decryptor()
    padded_data = decryptor.update(ciphertext) + decryptor.finalize()
    return unpad_data(padded_data)


def pad_data(data: dict):
    """Pad data to be block-aligned for AES encryption.

    :param data: The data to pad.
    :returns: The padded data.
    """
    padder = padding.PKCS7(algorithms.AES.block_size).padder()
    return padder.update(data.encode()) + padder.finalize()


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


def encrypt(secret: str):
    """Convenience function to encrypt a secret using AES-GCM.

    :param secret: The secret to encrypt.
    :returns: Base64-encoded binary blob.
    """

    results = ""

    try:
        key = get_encryption_key()
        encrypted_data = encrypt_data(secret, key)
        results = compact_store(encrypted_data)
    except binascii.Error as e:
        log.error("invalid base64 encoding: %s", e)
    except cryptography.exceptions.InvalidTag as e:
        log.error("invalid encryption key")
    except Exception as e:
        log.error("unhandled exception: %s", e)
    finally:
        return results


def decrypt(data: str, env: dict = os.environ):
    """Convenience function to decrypt a secret using AES-GCM.

    :param data: Base64-encoded binary blob.
    :env: The environment to use for the encryption key.
    :returns: The decrypted secret.
    """

    results = ""

    try:
        key = get_encryption_key(env=env)
        encrypted_data = compact_load(data)
        decrypted = decrypt_data(encrypted_data, key)
        results = decrypted.decode()
    except binascii.Error as e:
        log.error("invalid base64 encoding: %s", e)
    except cryptography.exceptions.InvalidTag as e:
        log.error("invalid encryption key")
    except Exception as e:
        log.error("unhandled exception: %s", e)
    finally:
        return results
