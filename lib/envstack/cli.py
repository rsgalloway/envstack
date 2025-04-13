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
Command line interface for envstack: stacked environment variable management.
"""

import argparse
import sys
import traceback

from envstack import __version__, config
from envstack.env import (
    bake_environ,
    Env,
    encrypt_environ,
    export_env_to_shell,
    export,
    load_environ,
    resolve_environ,
    trace_var,
)
from envstack.logger import setup_stream_handler
from envstack.wrapper import run_command

setup_stream_handler()


def parse_args():
    """Command line argument parser.

    Returns:
        tuple: (args, command)
    """

    if "--" in sys.argv:
        dash_index = sys.argv.index("--")
        args_after_dash = sys.argv[dash_index + 1 :]  # noqa: E203
        args_before_dash = sys.argv[1:dash_index]
    else:
        args_after_dash = []
        args_before_dash = sys.argv[1:]

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
        metavar="STACK",
        nargs="*",
        default=[config.DEFAULT_NAMESPACE],
        help="the environment stacks to use (default '%s')" % config.DEFAULT_NAMESPACE,
    )
    encrypt_group = parser.add_argument_group("encryption options")
    encrypt_group.add_argument(
        "-e",
        "--encrypt",
        action="store_true",
        help="encrypt environment values",
    )
    encrypt_group.add_argument(
        "--keygen",
        action="store_true",
        help="generate encryption keys",
    )
    parser.add_argument_group(encrypt_group)
    bake_group = parser.add_argument_group("bake options")
    bake_group.add_argument(
        "-o",
        "--out",
        metavar="FILENAME",
        help="save the environment to an env file",
    )
    bake_group.add_argument(
        "--depth",
        type=int,
        default=0,
        help="depth of environment stack to bake",
    )
    parser.add_argument_group(bake_group)
    export_group = parser.add_argument_group("export options")
    export_group.add_argument(
        "--clear",
        action="store_true",
        help="generate unset commands for %s" % config.SHELL,
    )
    export_group.add_argument(
        "--export",
        action="store_true",
        help="generate export commands for %s" % config.SHELL,
    )
    parser.add_argument_group(export_group)
    parser.add_argument(
        "-p",
        "--platform",
        default=config.PLATFORM,
        metavar="PLATFORM",
        help="platform to resolve variables for (linux, darwin, windows)",
    )
    parser.add_argument(
        "-s",
        "--set",
        nargs="*",
        metavar="VAR:VALUE",
        help="set a key:value pair in the environment",
    )
    parser.add_argument(
        "--scope",
        metavar="SCOPE",
        help="search scope for environment stack files",
    )
    parser.add_argument(
        "-r",
        "--resolve",
        nargs="*",
        metavar="VAR",
        help="resolve environment variables",
    )
    parser.add_argument(
        "-t",
        "--trace",
        nargs="*",
        metavar="VAR",
        help="trace where environment variables are being set",
    )
    parser.add_argument(
        "--sources",
        action="store_true",
        help="list the env stack file sources",
    )

    args = parser.parse_args(args_before_dash)

    return args, args_after_dash


def whichenv():
    """Entry point for the whichenv command line tool. Finds {VAR}s."""
    from envstack.util import findenv

    if len(sys.argv) != 2:
        print("Usage: whichenv [VAR]")
        return 2

    var_name = sys.argv[1]
    paths = findenv(var_name)
    for path in paths:
        print("{0}: {1}".format(var_name, path))


def main():
    """Main thread."""
    args, command = parse_args()

    try:
        if command:
            return run_command(command, args.namespace)

        elif args.keygen:
            from envstack.encrypt import generate_keys

            data = generate_keys()

            if args.export:
                print(export_env_to_shell(data))
            elif args.out:
                Env(data).write(args.out)
            else:
                for key, value in data.items():
                    print(f"{key}={value}")

        elif args.set:
            data = dict(kv.split(":", 1) for kv in args.set)

            if args.encrypt:
                data = encrypt_environ(data, encrypt=(not args.out))
            if args.export:
                print(export_env_to_shell(data))
            elif args.out:
                Env(data).write(args.out)
            else:
                for key, value in data.items():
                    print(f"{key}={value}")

        elif args.out:
            bake_environ(
                args.namespace,
                filename=args.out,
                depth=args.depth or 0,
                encrypt=args.encrypt,
            )

        elif args.resolve is not None:
            resolved = resolve_environ(
                load_environ(args.namespace, platform=args.platform)
            )
            keys = args.resolve or resolved.keys()
            for key in sorted(str(k) for k in keys):
                val = resolved.get(key)
                print(f"{key}={val}")

        elif args.trace is not None:
            if len(args.trace) == 0:
                args.trace = load_environ(args.namespace).keys()
            for trace in args.trace:
                path = trace_var(*args.namespace, var=trace)
                print("{0}: {1}".format(trace, path))

        elif args.sources:
            env = load_environ(args.namespace, platform=args.platform)
            for source in env.sources:
                print(source.path)

        elif args.clear:
            from envstack.env import clear

            print(clear(args.namespace, config.SHELL))

        elif args.export:
            print(export(args.namespace, config.SHELL))

        else:
            env = load_environ(
                args.namespace, platform=args.platform, encrypt=args.encrypt
            )
            for k, v in sorted(env.items(), key=lambda x: str(x[0])):
                print(f"{k}={v}")

    except KeyboardInterrupt:
        print("Stopping...")
        return 2

    except Exception:
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
