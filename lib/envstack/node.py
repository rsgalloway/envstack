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
Contains custom yaml constructor classes and functions.
"""

import hashlib
import os
import re
import string

import yaml

from envstack import util
from envstack.encrypt import AESGCMEncryptor, Base64Encryptor, FernetEncryptor


class Template(string.Template, str):
    def __init__(self, value):
        super().__init__(value)
        self.value = value

    def __repr__(self):
        return f"Template(value={self.value})"


class BaseNode(yaml.YAMLObject):
    """Base class for custom yaml nodes."""

    yaml_tag = None

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f"{self.__class__.__name__}('{self.value}')"

    def __str__(self):
        return str(self.value)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.value == other.value
        return False

    @classmethod
    def from_yaml(cls, loader: object, node: yaml.Node):
        return cls(node.value)

    @classmethod
    def to_yaml(cls, dumper: object, node: yaml.Node):
        return dumper.represent_scalar(cls.yaml_tag, node.value)

    def resolve(self, env: dict = os.environ):
        """Returns the decoded value."""
        return self.value


class Base64Node(BaseNode):
    """Base64 encoded string node."""

    yaml_tag = "!base64"

    def __init__(self, value):
        super().__init__(value)
        self.original_value = None

    @classmethod
    def from_yaml(cls, loader: object, node: yaml.Node):
        """Returns a new Base64Node instance."""
        node = cls(node.value)
        node.original_value = node.value
        return node

    @classmethod
    def to_yaml(cls, dumper: object, node: yaml.Node):
        """Encrypts the value before writing to yaml."""
        if node.value == node.original_value:
            encrypted = node.value
        elif isinstance(node.value, cls):
            encrypted = str(node.value)
        else:
            encrypted = Base64Encryptor().encrypt(node.value)
        return dumper.represent_scalar(cls.yaml_tag, encrypted)

    def resolve(self, env: dict = os.environ):
        """Returns base64 decoded value."""
        return Base64Encryptor().decrypt(self.value)


class MD5Node(BaseNode):
    """MD5 hash node."""

    yaml_tag = "!md5"

    @classmethod
    def from_yaml(cls, loader: object, node: yaml.Node):
        """Returns a new MD5Node instance."""
        return cls(node.value)

    @classmethod
    def to_yaml(cls, dumper: object, node: yaml.Node):
        """Encrypts the value before writing to yaml."""
        md5_hash = hashlib.md5(node.value.encode()).hexdigest()
        return dumper.represent_scalar(cls.yaml_tag, md5_hash)


class EncryptedNode(BaseNode):
    """Default encryption node. Supports multiple encryption schemes.
    Favors AES-GCM, then Fernet, then base64."""

    yaml_tag = "!encrypt"

    def __init__(self, value):
        super().__init__(value)
        self.original_value = None

    @classmethod
    def encryptor(cls, env: dict = os.environ):
        """Returns the encryptor class based on the environment."""
        if env.get(AESGCMEncryptor.KEY_VAR_NAME):
            return AESGCMEncryptor(env=env)
        elif env.get(FernetEncryptor.KEY_VAR_NAME):
            return FernetEncryptor(env=env)
        else:
            return Base64Encryptor()

    @classmethod
    def from_yaml(cls, loader: object, node: yaml.Node):
        """Returns a new EncryptedNode instance."""
        node = cls(node.value)
        node.original_value = node.value
        return node

    @classmethod
    def to_yaml(cls, dumper: object, node: yaml.Node):
        """Encrypts the value before writing (do not double encrypt)."""
        if node.value == node.original_value:
            encrypted = node.value
        elif isinstance(node.value, cls):
            encrypted = str(node.value)
        else:
            encrypted = cls.encryptor().encrypt(node.value)
        return dumper.represent_scalar(cls.yaml_tag, encrypted)

    def resolve(self, env: dict = os.environ):
        """Returns the decrypted original value, preserving original type.

        :param env: environment with encryption keys.
        :return: decrypted value.
        """
        try:
            value = self.encryptor(env=env).decrypt(self.value)
        except Exception:
            value = self.value
        return util.safe_eval(value)


class AESGCMNode(BaseNode):
    """Default encrypted node using AES-GCM."""

    yaml_tag = "!aesgcm"

    def __init__(self, value):
        super().__init__(value)
        self.original_value = None

    @classmethod
    def from_yaml(cls, loader: object, node: yaml.Node):
        """Returns a new AESGCMNode instance."""
        node = cls(node.value)
        node.original_value = node.value
        return node

    @classmethod
    def to_yaml(cls, dumper: object, node: yaml.Node):
        """Encrypts the value before writing to yaml."""
        if node.value == node.original_value:
            encrypted = node.value
        elif isinstance(node.value, cls):
            encrypted = str(node.value)
        else:
            encrypted = AESGCMEncryptor().encrypt(node.value)
        return dumper.represent_scalar(cls.yaml_tag, encrypted)

    def resolve(self, env: dict = os.environ):
        """Returns the decrypted value."""
        return AESGCMEncryptor(env=env).decrypt(self.value)


class FernetNode(BaseNode):
    """Default encrypted node using Fernet."""

    yaml_tag = "!fernet"

    def __init__(self, value):
        super().__init__(value)
        self.original_value = None

    @classmethod
    def from_yaml(cls, loader: object, node: yaml.Node):
        """Returns a new FernetNode instance."""
        node = cls(node.value)
        node.original_value = node.value
        return node

    @classmethod
    def to_yaml(cls, dumper: object, node: yaml.Node):
        """Encrypts the value before writing to yaml."""
        if node.value == node.original_value:
            encrypted = node.value
        elif isinstance(node.value, cls):
            encrypted = str(node.value)
        else:
            encrypted = FernetEncryptor().encrypt(node.value)
        return dumper.represent_scalar(cls.yaml_tag, encrypted)

    def resolve(self, env: dict = os.environ):
        """Returns the decrypted value."""
        return FernetEncryptor(env=env).decrypt(self.value)


class CustomLoader(yaml.SafeLoader):
    required_keys = {"include", "all", "darwin", "linux", "windows"}

    def construct_mapping(self, node: yaml.Node, deep: bool = False):
        mapping = super().construct_mapping(node, deep=deep)
        for key, value in mapping.items():
            if key in self.required_keys:
                continue
            try:
                if node.tag == Base64Node.yaml_tag:
                    mapping[key] = Base64Node(value)
                elif node.tag == EncryptedNode.yaml_tag:
                    mapping[key] = EncryptedNode(value)
                elif node.tag == AESGCMNode.yaml_tag:
                    mapping[key] = AESGCMNode(value)
                elif node.tag == FernetNode.yaml_tag:
                    mapping[key] = FernetNode(value)
                elif node.tag == MD5Node.yaml_tag:
                    mapping[key] = MD5Node(value)
                else:
                    mapping[key] = Template(value)
            except Exception as e:
                raise yaml.constructor.ConstructorError(
                    None, None, f"Error parsing template: {e}", node.start_mark
                )
        return mapping


class CustomDumper(yaml.SafeDumper):
    """
    Custom Dumper class to handle anchors, references and flow style for nested
    mappings.
    """

    def __init__(self, *args, **kwargs):
        super(CustomDumper, self).__init__(*args, **kwargs)
        self.depth = 0
        self.basekey = None
        self.newanchors = {}

    def anchor_node(self, node: yaml.Node):
        """Anchor the node and set the basekey for the node."""
        # increase depth on entering anchor_node
        self.depth += 1

        # set basekey for the node
        if self.depth == 2:
            assert isinstance(node, yaml.ScalarNode), (
                "yaml node not a string: %s" % node
            )
            self.basekey = str(node.value)
            node.value = self.basekey

        # set anchor for the node
        if self.depth == 3:
            assert self.basekey, "could not find base key for value: %s" % node
            self.newanchors[node] = self.basekey

        super(CustomDumper, self).anchor_node(node)
        if self.newanchors:
            self.anchors.update(self.newanchors)
            self.newanchors.clear()

    def quote_vars(self, node: yaml.Node):
        """Quote variables in the node value."""
        if isinstance(node, yaml.ScalarNode):
            if re.match(r"\$\{[A-Za-z_][A-Za-z0-9_]*\}", node.value):
                node.style = '"%s"' % node.value

    def represent_data(self, data: dict):
        """Represent data and set flow_style for nested mappings."""
        # increase depth on entering represent_data
        self.depth += 1
        node = super().represent_data(data)
        self.depth -= 1

        # use flow style for nested mappings
        if isinstance(node, yaml.MappingNode) and self.depth >= 2:
            node.flow_style = True
            for _, value in node.value:
                self.quote_vars(value)
        elif isinstance(node, yaml.SequenceNode) and self.depth >= 2:
            node.flow_style = True
            for element in node.value:
                self.quote_vars(element)

        return node


def get_keys_from_env(env: dict = os.environ):
    """Return encryption keys from the environment.

    :param env: Environment dictionary.
    """
    keys = {}
    for key in [AESGCMEncryptor.KEY_VAR_NAME, FernetEncryptor.KEY_VAR_NAME]:
        if key in env:
            keys[key] = env[key]
    return keys


def add_custom_node_type(node_type: BaseNode):
    """Add custom node type to yaml. Node type must be a subclass of BaseNode,
    with local implementation of from_yaml and to_yaml methods, and definition
    of yaml_tag.

    :param node_type: Custom node class.
    """

    try:
        yaml.SafeLoader.add_constructor(node_type.yaml_tag, node_type.from_yaml)
        yaml.SafeDumper.add_representer(node_type, node_type.to_yaml)
    except Exception as e:
        print(f"error adding custom node type {node_type}: {e}")


# add custom constructors and representers
custom_node_types = [
    Base64Node,
    EncryptedNode,
    AESGCMNode,
    FernetNode,
    MD5Node,
]
for node in custom_node_types:
    add_custom_node_type(node)
