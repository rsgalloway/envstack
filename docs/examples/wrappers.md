# Wrappers

Wrappers are executable scripts that launch a command inside a known envstack
environment. They are useful when you want a stable CLI entrypoint without
asking users to remember the right stack name every time.

## Why use a wrapper

- A tool always starts with the expected environment active
- Stack-selection details stay inside the launcher
- Environment variables can be resolved before building the final command
- Small bootstrap scripts become easy to distribute and reuse

## Example: `bin/hello`

The repository includes an example wrapper at
[`bin/hello`](https://github.com/rsgalloway/envstack/blob/master/bin/hello)
and a companion stack file at
[`examples/wrappers/hello.env`](https://github.com/rsgalloway/envstack/blob/master/examples/wrappers/hello.env).

The stack file:

```yaml
#!/usr/bin/env envstack
include: [default]
all: &all
  HELLO: world
  LOG_LEVEL: ${LOG_LEVEL:=INFO}
darwin:
  <<: *all
  PYEXE: /usr/local/bin/python3
linux:
  <<: *all
  PYEXE: /usr/bin/python
windows:
  <<: *all
  PYEXE: C:\Python39\python.exe
```

The wrapper:

```python
#!/usr/bin/env python3

import sys

from envstack.wrapper import Wrapper


class HelloWrapper(Wrapper):
    """A simple wrapper that prints the value of an environment variable."""

    def __init__(self, *args, **kwargs):
        super(HelloWrapper, self).__init__(*args, **kwargs)
        self.shell = True

    def executable(self):
        """Return the executable to run."""
        return "/usr/bin/python -c 'import os,sys;print(os.getenv(sys.argv[1]))'"


def main():
    """Run the wrapper in the 'hello' env stack."""
    hello = HelloWrapper("hello", sys.argv[1:])
    return hello.launch()


if __name__ == "__main__":
    sys.exit(main())
```

Running it:

```bash
$ hello HELLO
world
```

The wrapper code never hard-codes `HELLO=world`. It loads the `hello` stack,
resolves it, and launches the subprocess with those values in its environment.

## How the pattern works

1. The wrapper subclasses `envstack.wrapper.Wrapper`.
2. It names the stack to load, here `hello`.
3. `launch()` resolves that stack and builds a subprocess environment.
4. The wrapped command runs with those env vars already applied.

This makes wrappers a good fit for tool launchers, bootstrap scripts, and
small command shims around shared environments.

## Wrapping other executables

The same pattern works for far more than a demo `hello` command. In practice,
you can wrap almost any executable so it always runs inside a composed
environment stack.

Common use cases:

- DCC launchers such as `nuke`, `maya`, or `houdini`
- Project tools that need a specific `PATH`, `PYTHONPATH`, or license setup
- Build and render commands that should inherit a known deployment root
- Internal CLIs that should run with stack-selected config by default

At the command line, the simplest form is already:

```bash
envstack dev -- python -m pytest
envstack project -- nuke
envstack showA -- /usr/local/bin/custom-tool --flag value
```

If you want a stable executable entrypoint instead of asking users to prefix
every command with `envstack`, create a wrapper script around that executable.

For an argv-style executable, the underlying `Wrapper` base class can return a
resolved path such as `${TOOL_ROOT}/bin/tool`, and the subprocess inherits the
fully resolved stack environment before launch.

For example:

```python
import sys

from envstack.wrapper import Wrapper


class ToolWrapper(Wrapper):
    def executable(self):
        return "${TOOL_ROOT}/bin/tool"


if __name__ == "__main__":
    sys.exit(ToolWrapper("project", sys.argv[1:]).launch())
```

That is the main value of wrappers: any executable can be made to feel
"pre-configured" by binding it to a named environment stack.

## Related files

- [`examples/wrappers/hello.env`](https://github.com/rsgalloway/envstack/blob/master/examples/wrappers/hello.env)
- [`lib/envstack/wrapper.py`](https://github.com/rsgalloway/envstack/blob/master/lib/envstack/wrapper.py)
