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
Contains command line interface for envstack.
"""

import os
import sys
import pprint
import traceback

from envstack import __version__
from envstack import config
from envstack.env import expandvars, load_environ, trace_var


def parse_args():
    """Command line argument parser."""

    import argparse

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"envstack {__version__}",
    )
    parser.add_argument(
        "namespace",
        metavar="NAMESPACE",
        nargs="?",
        default=config.DEFAULT_NAMESPACE,
        help="the namespace to use",
    )
    parser.add_argument(
        "-p",
        "--platform",
        default=config.PLATFORM,
        metavar="PLATFORM",
        help="specify the platform to resolve variables for",
    )
    parser.add_argument(
        "-r",
        "--resolve",
        metavar="VAR",
        help="resolve an environment variable",
    )
    parser.add_argument(
        "-t",
        "--trace",
        metavar="VAR",
        help="trace where a variable is getting set",
    )

    args = parser.parse_args()

    return args, parser


def main():
    """Main thread."""
    args, _ = parse_args()

    try:
        if args.resolve:
            env = load_environ(
                args.namespace, environ=os.environ, platform=args.platform
            )
            var = env.get(args.resolve)
            print(pprint.pformat(expandvars(var, env, recursive=True)))
        elif args.trace:
            path = trace_var(args.namespace, args.trace)
            print("{0}: {1}".format(args.trace, path))
        else:
            env = load_environ(args.namespace, platform=args.platform, includes=True)
            for k, v in env.items():
                print(f"{k} {pprint.pformat(v)}")

    except KeyboardInterrupt:
        print("Stopping...")
        return 2

    except Exception:
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
