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
Contains custom yaml constructor classes and functions.
"""

import hashlib
import os
import string
from base64 import b64decode, b64encode

import yaml


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

    @classmethod
    def from_yaml(cls, loader, node):
        return cls(node.value)

    @classmethod
    def to_yaml(cls, dumper, data):
        return dumper.represent_scalar(cls.yaml_tag, data.value)


class Base64Node(BaseNode):
    """Base64 encoded string node."""

    yaml_tag = "!base64"

    @classmethod
    def from_yaml(cls, loader, node):
        return cls(node.value)

    @classmethod
    def to_yaml(cls, dumper, data):
        encoded = b64encode(data.value.encode())
        return dumper.represent_scalar(cls.yaml_tag, encoded.decode(), style=None)

    def resolve(self):
        """Returns decoded value."""
        return b64decode(self.value).decode()


class MD5Node(BaseNode):
    """MD5 hash node."""

    yaml_tag = "!md5"

    @classmethod
    def from_yaml(cls, loader, node):
        return cls(node.value)

    @classmethod
    def to_yaml(cls, dumper, data):
        md5_hash = hashlib.md5(data.value.encode()).hexdigest()
        return dumper.represent_scalar(cls.yaml_tag, md5_hash)


class EncryptedNode(BaseNode):
    """Default encrypted string node using AES-GCM."""

    yaml_tag = "!encrypt"

    @classmethod
    def from_yaml(cls, loader, node):
        return cls(node.value)

    @classmethod
    def to_yaml(cls, dumper, data):
        from envstack.encrypt import encrypt

        return dumper.represent_scalar(cls.yaml_tag, encrypt(data.value))

    def resolve(self, env: dict = os.environ):
        """Decrypt the value using the environment."""
        from envstack.encrypt import decrypt

        return decrypt(self.value, env=env)


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
                else:
                    mapping[key] = Template(value)
            except Exception as e:
                raise yaml.constructor.ConstructorError(
                    None, None, f"Error parsing template: {e}", node.start_mark
                )
        return mapping


class CustomDumper(yaml.SafeDumper):
    """
    Custom Dumper class to handle anchors and references.
    """

    def __init__(self, *args, **kwargs):
        super(CustomDumper, self).__init__(*args, **kwargs)
        self.depth = 0
        self.basekey = None
        self.newanchors = {}

    def anchor_node(self, node: yaml.Node):
        self.depth += 1
        if self.depth == 2:
            assert isinstance(node, yaml.ScalarNode), (
                "yaml node not a string: %s" % node
            )
            self.basekey = str(node.value)
            node.value = self.basekey
        if self.depth == 3:
            assert self.basekey, "could not find base key for value: %s" % node
            self.newanchors[node] = self.basekey
        super(CustomDumper, self).anchor_node(node)
        if self.newanchors:
            self.anchors.update(self.newanchors)
            self.newanchors.clear()

    def represent_list(self, data):
        return super().represent_list(data, flow_style=True)


# add custom constructors and representers
yaml.SafeLoader.add_constructor(Base64Node.yaml_tag, Base64Node.from_yaml)
yaml.SafeDumper.add_representer(Base64Node, Base64Node.to_yaml)
yaml.SafeLoader.add_constructor(EncryptedNode.yaml_tag, EncryptedNode.from_yaml)
yaml.SafeDumper.add_representer(EncryptedNode, EncryptedNode.to_yaml)
yaml.SafeLoader.add_constructor(MD5Node.yaml_tag, MD5Node.from_yaml)
yaml.SafeDumper.add_representer(MD5Node, MD5Node.to_yaml)


if __name__ == "__main__":
    import os
    from pprint import pprint

    from envstack.env import Source

    default_env = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "env", "secrets.env")
    )
    test_env = "/var/tmp/test.env"

    s1 = Source(default_env)
    d = s1.load()
    print(f"# {default_env}")
    pprint(d)

    # make some updates
    s1.data["linux"]["ROOT"] = "/var/tmp"
    s1.data["all"]["KEY"] = Base64Node("this is a secret")
    s1.data["all"]["MD5"] = MD5Node("this is hashed")

    s1.write(test_env)
    s2 = Source(test_env)
    d = s2.load()
    print(f"# {test_env}")
    pprint(d)
