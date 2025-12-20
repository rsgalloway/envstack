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
import re
import sys
import traceback
from typing import List

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


class StoreOnce(argparse.Action):
    """Custom argparse action to ensure an option is only set once."""

    def __call__(self, parser, namespace, values, option_string=None):
        # if we've already seen this option once, bail
        if getattr(namespace, f"__seen_{self.dest}", False):
            aliases = "/".join(self.option_strings)
            parser.error(f"{aliases} specified more than once.")
        setattr(namespace, f"__seen_{self.dest}", True)
        setattr(namespace, self.dest, values)


def _parse_env_lines(lines):
    """Parse lines of environment variables from an iterable.

    :param lines: An iterable of lines, such as a file or stdin.
    :return: A dictionary of environment variables.
    """
    ENV_LINE_RE = re.compile(
        r"""
        ^\s*
        (?:export\s+)?
        (?P<key>(?:<<|[A-Za-z_][A-Za-z0-9_]*))
        \s*
        (?P<op>[:=])
        \s*
        (?P<val>.*)
        \s*$
        """,
        re.VERBOSE,
    )

    def parse_line(line: str):
        m = ENV_LINE_RE.match(line)
        if not m:
            return None
        key = m.group("key")
        val = m.group("val")
        # strip matching quotes only if present
        if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
            val = val[1:-1]
        return key, val

    data = {}
    for raw in lines:
        k, v = parse_line(raw.strip())
        data[k] = v
    return data


def _parse_keyvals(items: dict):
    """Parse a list of key=value pairs.

    :param items: A list of strings in the form "key=value" or "key:value".
    :return: A dictionary mapping keys to values.
    """
    out = {}
    for kv in items:
        if ":" in kv:
            k, v = kv.split(":", 1)
        elif "=" in kv:
            k, v = kv.split("=", 1)
        else:
            k, v = kv, ""
        out[k] = v
    return out


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
        help="the environment stacks to use",
    )
    parser.add_argument(
        "-b",
        "--bare",
        action="store_true",
        help="create a bare environment",
    )
    parser.add_argument(
        "--shell",
        action="store_true",
        help="drop into a shell with the environment loaded",
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
        "-d",
        "--depth",
        type=int,
        default=0,
        help="depth of environment stack to bake (default: 0 = flatten)",
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
        action=StoreOnce,
        metavar="KEY=VALUE",
        help="overlay KEY=VALUE pairs to envstack environments",
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
        action=StoreOnce,
        metavar="VAR",
        help="resolve environment variables",
    )
    parser.add_argument(
        "-t",
        "--trace",
        nargs="*",
        action=StoreOnce,
        metavar="VAR",
        help="trace where environment variables are being set",
    )
    parser.add_argument(
        "--sources",
        action="store_true",
        help="list the env stack file sources",
    )
    export_group.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="print the value of an environment variable only (no key)",
    )

    args = parser.parse_args(args_before_dash)

    return args, args_after_dash


def envshell(namespace: List[str] = None):
    """Run a shell in the given environment stack."""
    from .envshell import EnvshellWrapper

    print("\U0001F680 Launching envshell... CTRL+D to exit")

    name = (namespace or [config.DEFAULT_NAMESPACE])[:]
    envshell = EnvshellWrapper(name)
    return envshell.launch()


def whichenv():
    """Entry point for the whichenv command line tool. Finds {VAR}s."""
    from .util import findenv

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

        elif args.shell:
            return envshell(args.namespace)

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

        elif args.clear:
            from envstack.env import clear

            print(clear(args.namespace, shell=config.SHELL))

        elif args.export and args.resolve is None and args.set is None:
            print(export(args.namespace, shell=config.SHELL, encrypt=args.encrypt))

        elif args.set is not None and args.resolve is None:
            force_stdin = args.set == [] or args.set == ["-"]
            using_pipe = args.set == [] and not sys.stdin.isatty()

            # load the environment if not in bare mode
            if args.bare:
                env = Env()
            else:
                env = load_environ(args.namespace, platform=args.platform)

            # interactive mode
            if force_stdin and sys.stdin.isatty():
                print(
                    "Enter ENV:VAR or ENV=VAR pairs. Press Ctrl+D or Ctrl+C to finish:",
                    file=sys.stderr,
                )
                lines = []
                try:
                    while True:
                        lines.append(input() + "\n")
                except (EOFError, KeyboardInterrupt):
                    pass
                data = _parse_env_lines(lines)
                if not data:
                    return 0
            # pipe stdin (or '-' with non-tty stdin)
            elif force_stdin or using_pipe:
                data = _parse_env_lines(sys.stdin)
                if not data:
                    raise ValueError("no KEY=VALUE pairs found on stdin")
            # explicit args path
            else:
                data = _parse_keyvals(args.set)

            # encrypt the new data only
            if args.encrypt:
                data = encrypt_environ(data)

            # update the environment with the new data
            env.update(data)

            if args.export:
                print(export_env_to_shell(env))
            elif args.out:
                env.write(args.out, depth=args.depth)
            else:
                for key, val in env.items():
                    if args.quiet:
                        if len(env) > 1:
                            print("error: --quiet requires exactly one KEY")
                            return 2
                        else:
                            print(val)
                    else:
                        print(f"{key}={val}")

        elif args.out and args.resolve is None:
            bake_environ(
                args.namespace,
                filename=args.out,
                depth=args.depth,
                encrypt=args.encrypt,
            )

        elif args.resolve is not None:
            if args.depth:
                print("error: --depth is not valid with --resolve")
                return 2
            resolved = resolve_environ(
                load_environ(args.namespace, platform=args.platform)
            )
            if args.set:
                resolved.update(_parse_keyvals(args.set))
            if args.encrypt:
                resolved = encrypt_environ(resolved)
            if args.out:
                if len(args.resolve) == 0:
                    resolved.write(args.out, depth=0)
                else:
                    keys = args.resolve or resolved.keys()
                    if args.set:
                        keys = set(keys).union(_parse_keyvals(args.set).keys())
                    env = Env({key: resolved[key] for key in keys})
                    env.write(args.out, depth=0)
            elif args.export:
                if len(args.resolve) == 0:
                    print(export_env_to_shell(resolved, shell=config.SHELL))
                else:
                    keys = args.resolve or resolved.keys()
                    if args.set:
                        keys = set(keys).union(_parse_keyvals(args.set).keys())
                    env = Env({key: resolved[key] for key in keys})
                    print(export_env_to_shell(env, shell=config.SHELL))
            else:
                keys = args.resolve or resolved.keys()
                if args.set:
                    keys = set(keys).union(_parse_keyvals(args.set).keys())
                for key in sorted(str(k) for k in keys):
                    val = resolved.get(key)
                    if key in resolved:
                        if args.quiet:
                            if len(keys) > 1:
                                print("error: --quiet requires exactly one KEY")
                                return 2
                            else:
                                print(val)
                        else:
                            print(f"{key}={val}")

        elif args.trace is not None:
            if len(args.trace) == 0:
                args.trace = load_environ(args.namespace).keys()
            for trace in args.trace:
                path = trace_var(*args.namespace, var=trace)
                if path:
                    if args.quiet:
                        if len(args.trace) > 1:
                            print("error: --quiet requires exactly one KEY")
                            return 2
                        else:
                            print(path)
                    else:
                        print("{0}={1}".format(trace, path))

        elif args.sources:
            env = load_environ(args.namespace, platform=args.platform)
            for source in env.sources:
                print(source.path)

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
