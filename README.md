envstack
========

Environment variable management system.

## Features

The features of Envstack include:

- **Environment stacks:** Envstack allows you to manage environment variables using .env files called environment stacks. These stacks provide a hierarchical and contextual approach to managing variables.

- **Hierarchical structure:** Environment stacks can be combined and have a defined order of priority. Variables defined in higher scope stacks flow from higher scope to lower scope, left to right.

- **Variable expansion modifiers:** Envstack supports bash-like variable expansion modifiers, allowing you to set default values for variables and override them in the environment or by higher scope stacks.

- **Platform-specific variables:** Environment stacks can have platform-specific variables, which always inherit from the default stack. This allows you to define different values for variables based on the platform.

- **Variable references:** Variables in Envstack can reference other variables, allowing for more flexibility and dynamic value assignment.

- **Includes:** Environment stack files can include other namespaced environments, making it easy to reuse and combine different stacks.

- **Python API:** Envstack provides a Python API that allows you to initialize and work with environment stacks programmatically. You can initialize specific stacks, revert to the original environment, and resolve variables.

- **Running commands:** Envstack allows you to run command line executables inside an environment stack, providing a convenient way to execute commands with the desired environment.

- **Wrappers:** Envstack supports wrappers, which are command line executable scripts that automatically run a given command in the environment stack. This allows for easy customization and automation of command execution.

- **Shell integration:** Envstack provides instructions for sourcing the environment stack in your current shell, allowing you to set and clear the environment easily.


## Installation

The easiest way to install:

```bash
$ pip install envstack
```

Alternatively,

```bash
$ git clone https://github.com/rsgalloway/envstack
$ cd envstack
$ python setup.py install
```

#### distman

If installing from source to a network location, you can use
[distman](https://github.com/rsgalloway/distman) to
install envstack using the provided `dist.json` file:

```bash
$ envstack -- distman [-d]
```

Using distman will deploy the targets defined in the `dist.json` file to the
root folder defined by `$DEPLOY_ROOT` (defined in `env/default.env`).

## Quickstart

Envstack looks for .env files in directories specified by `$ENVPATH` and in the
current working directory:

```bash
$ export ENVPATH=./env
```

Define as many paths as you want, and envstack will search for stack file in
order from left to right:

```bash
$ export ENVPATH=/mnt/pipe/dev/env:/mnt/pipe/prod/env
```

In the case above, stack files in `/mnt/pipe/dev/env` will take precedence over those
found in `/mnt/pipe/prod/env`.

Running the `envstack` command will show you the default environment stack,
defined in the default stack file `env/default.env`:

```bash
$ envstack
DEPLOY_ROOT=${ROOT}/${ENV}
ENV=prod
ENVPATH=${DEPLOY_ROOT}/env:${ENVPATH}
HELLO=${HELLO:=world}
LOG_LEVEL=${LOG_LEVEL:=INFO}
PATH=${DEPLOY_ROOT}/bin:${PATH}
PYTHONPATH=${DEPLOY_ROOT}/lib/python:${PYTHONPATH}
ROOT=/mnt/pipe
STACK=default
```

To see stacks, pass the stack name as the first arg. Environment stacks can be
combined, in order of priority (variables defined in stacks flow from higher
scope to lower scope, left to right):

```bash
$ envstack [STACK [STACK ...]]
```

## Setting Values

Envstack uses bash-like variable expansion modifiers. Setting `$VAR` to a fixed
value means `$VAR` will always use that value. Using an expansion modifier
allows you to override the value:

| Value | Description |
|---------------------|-------------|
| value |  'value' |
| ${VAR:-default} | os.environ.get('VAR', 'default') |
| ${VAR:=default} | VAR = VAR or 'default' |
| ${VAR:?error message} | if not VAR: raise ValueError() |

Without the expansion modifier, values are set and do not change (but can be
overridden by lower scope stacks, i.e. a lower scope stack file may override
a higher one). 

If we define `$HELLO` like this:

```yaml
HELLO: world
```

Then the value is set and cannot be modified (except by lower scope stacks):

```bash
$ envstack -- echo {HELLO}
world
$ HELLO=goodbye envstack -- echo {HELLO}
world
```

With an expansion modifier, variables have a default value and can also be
overridden in the environment, or by higher scope stacks:

```yaml
HELLO: ${HELLO:=world}
```

Here we show the default value, and how we can override it in the environment:

```bash
$ envstack -- echo {HELLO}
world
$ HELLO=goodbye envstack -- echo {HELLO}
goodbye
```

## Creating Stacks

To create a new environment stack, create a new namespaced .env file.
For example `thing.env` (the stack namespace is "thing"):

```yaml
all: &default
  FOO: bar
```

To see the resolved environment for the `thing` environment stack, run:

```bash
$ envstack thing
FOO 'bar'
```

Variables can reference other variables defined elsewhere (but cannot be
circular):

```yaml
all: &default
  BAR: $FOO
```

Variables can be platform specific (always inherit from `default`):

```yaml
linux:
  <<: *default
  HELLO: world

windows:
  <<: *default
  HELLO: goodbye
```

Variables can reference other variables:

```yaml
all: &default
  FOO: ${BAR}
  BAR: ${BAZ}
  BAZ: ${BIZ}
  BIZ: ${BIZ:=foo}
```

As you might expect, the above resolves to:

```bash
$ envstack -r
BAR=foo
BAZ=foo
BIZ=foo
FOO=foo
```

#### Includes

Environment stack files can include other namespaced environments (you should
probably always include the default stack):

```yaml
include: [default, test]
```

## Usage

To see the unresolved environment for one or more environment stacks (values are
defined in the stacks from left to right):

```bash
$ envstack [STACK [STACK ...]]
```

To resolve one or more environment vars for a given stack:

```bash
$ envstack [STACK] -r [VAR [VAR ...]]
```

To trace where one or more environment vars is being set:

```bash
$ envstack [STACK] -t [VAR [VAR ...]]
```

To get the list of source files for a given stack:

```bash
$ envstack [STACK] --sources
```

## Python API

To initialize the environment stack in Python, use the `init` function:

```python
>>> envstack.init()
>>> os.getenv("HELLO")
'world'
```

To initialize the "dev" stack:

```python
>>> envstack.init("dev")
>>> os.getenv("ENV")
'dev'
```

To revert the original environment:

```python
>>> envstack.revert()
>>> os.getenv("HELLO")
>>> 
```

Alternatively, `envstack.getenv` can be a drop-in replacement for `os.getenv`
for the default environment stack:

```python
>>> envstack.getenv("HELLO")
'world'
```

Creating and resolving environments:

```python
>>> from envstack.env import Env
>>> env = Env({"BAR": "${FOO}", "FOO": "foo"})
>>> resolve_environ(env)
{'BAR': 'foo', 'FOO': 'foo'}
```

## Running Commands

To run any command line executable inside of an environment stack, where
`[COMMAND]` is the command to run:

```bash
$ envstack [STACK] -- [COMMAND]
```

For example:

```bash 
$ envstack -- echo {HELLO}
world
```

Running Python commands in the default stack:

```bash
$ envstack -- python -c "import os; print(os.environ['HELLO'])"
world
```

Overriding values in the stack:

```bash
$ HELLO=goodbye envstack -- python -c "import os; print(os.environ['HELLO'])"
goodbye
```

Same command but using the "thing" stack"

```bash
$ envstack thing -- python -c "import os; print(os.environ['FOO'])"
bar
```

## Wrappers

Wrappers are command line executable scripts that automatically run a given
command in the environment stack.

Here is a simple example that runs a `python -c` command in the `hello`
environment stack that sets a value for `${PYEXE}`:

#### hello.env
```yaml
all: &default
  PYEXE: python
```

#### bin/hello
```python
import sys
from envstack.wrapper import Wrapper

class HelloWrapper(Wrapper):
    def __init__(self, *args, **kwargs):
        super(HelloWrapper, self).__init__(*args, **kwargs)

    def executable(self):
        """Return the command to run."""
        return "${PYEXE} -c 'import os,sys;print(os.getenv(sys.argv[1]))'"

if __name__ == "__main__":
    hello = HelloWrapper("hello", sys.argv[1:])
    hello.launch()
```

Running the wrapper:

```bash
$ hello HELLO
world
```

## Shells

In order to set an environment stack in your current shell, the stack must be
sourced (that's because Python processes and subshells cannot alter the
environment of the parent process).

To source the environment in your current shell, create an alias that sources
the output of the `--export` command:

#### bash
```bash
alias envstack-init='source <(envstack --export)';
```

#### cmd
```cmd
doskey envstack-set=for /f "usebackq" %i in (`envstack --export $*`) do %%i
```

Then you can set the environment stack in your shell with the `envstack-init`
command. To clear the environment in your current shell, create an alias that
sources the output of the `--clear` command:

#### bash
```bash
alias envstack-clear='source <(envstack --clear)';
```

#### cmd
```cmd
doskey envstack-clear=for /f "usebackq" %i in (`envstack --clear $*`) do %%i
```
