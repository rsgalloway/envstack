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

import os
import shutil

from setuptools import find_packages, setup
from setuptools.command.install import install

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, "README.md")) as f:
    long_description = f.read()


class PostInstallCommand(install):
    """Custom post-installation for copying stack.env."""

    def install_default_stack(self):
        """Copy the default stack.env file to the default location."""
        from envstack.config import DEFAULT_ENV_DIR

        if not os.path.isdir(DEFAULT_ENV_DIR):
            os.makedirs(DEFAULT_ENV_DIR)

        source = os.path.join(os.path.dirname(__file__), "stack.env")
        destination = os.path.join(DEFAULT_ENV_DIR, "stack.env")

        if os.path.exists(source):
            print(f"Copying {source} to {destination}")
            shutil.copy(source, destination)
        else:
            print(f"{source} not found)")

    def run(self):
        """Run the default install and copy the default stack.env file."""
        install.run(self)

        try:
            self.install_default_stack()
        except Exception as e:
            print(f"Error copying stack.env: {e}")


setup(
    name="envstack",
    version="0.4.2",
    description="Stacked environment variable management system.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Ryan Galloway",
    author_email="ryan@rsgalloway.com",
    url="http://github.com/rsgalloway/envstack",
    package_dir={"": "lib"},
    packages=find_packages("lib"),
    entry_points={
        "console_scripts": [
            "envstack = envstack.cli:main",
        ],
    },
    install_requires=[
        "PyYAML>=5.1.2",
        "siteconf>=0.1.7",
    ],
    data_files=[(".", ["stack.env"])],
    cmdclass={"install": PostInstallCommand},
    zip_safe=False,
)
