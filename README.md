envstack
========

Environment variable management system.

| Feature | Description |
|---------|-------------|
| Namespaced environments | Environments in envstack are namespaced, allowing you to organize and manage variables based on different contexts or projects. Each environment stack can have its own set of variables, providing a clean separation and avoiding conflicts between different environments. |
| Environment stacks | Allows you to manage environment variables using .env files called environment stacks. These stacks provide a hierarchical and contextual approach to managing variables. |
| Hierarchical structure | Stacks can be combined and have a defined order of priority. Variables defined in higher scope stacks flow from higher scope to lower scope, left to right. |
| Variable expansion modifiers | Supports bash-like variable expansion modifiers, allowing you to set default values for variables and override them in the environment or by higher scope stacks. |
| Platform-specific variables | Stacks can have platform-specific variables and values. This allows you to define different values for variables based on the platform. |
| Variable references | Variables can reference other variables, allowing for more flexibility and dynamic value assignment. |
| Multi-line values | Supports variables with multi-line values. |
| Includes | Stack files can include other stacks, making it easy to reuse and combine different stacks. |
| Python API | Provides a Python API that allows you to initialize and work with environment stacks programmatically. Easily initialize pre-defined environments with Python scripts, tools, and wrappers. |
| Running commands | Allows you to run command line executables inside an environment stack, providing a convenient way to execute commands with a pre-defined environment. |
| Wrappers | Supports wrappers, which are command line executable scripts that automatically run a given command in the environment stack. This allows for easy customization and management of environments. |
| Shell integration | Provides instructions for sourcing the environment stack in your current shell, allowing you to set and clear the environment easily. |

## Installation

The easiest way to install:

```bash
$ pip install -U envstack
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
$ ENVPATH=./env distman [-d]
```

Using distman will deploy the targets defined in the `dist.json` file to the
root folder defined by `${DEPLOY_ROOT}` (defined in `env/default.env`).

## Quickstart

Envstack looks for .env files in directories specified by `${ENVPATH}` and i
the current working directory. Start by getting the latest `default.env` 
environment stack file:

```bash
$ wget -O default.env \
https://raw.githubusercontent.com/rsgalloway/envstack/master/env/default.env
```

Set `$ENVPATH` to the directory containing your environment stack files:

```bash
$ export ENVPATH=/path/to/env/stack/files
```

Define as many paths as you want, and envstack will search for stack file in
order from left to right, for example:

```bash
$ export ENVPATH=/mnt/pipe/dev/env:/mnt/pipe/prod/env
```

In the case above, stack files in `/mnt/pipe/dev/env` will take precedence over those
found in `/mnt/pipe/prod/env`.

#### Basic Usage

Running the `envstack` command will show you the default environment stack,
defined in the `default.env` stack file:

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

If you are not seeing the above output, make sure the `default.env`
stack file is in your `$ENVPATH` or current working directory.

> NOTE: The name of the current stack will always be stored in `${STACK}`.

To see stacks, pass the stack name as the first arg. Environment stacks can be
combined, in order of priority (variables defined in stacks flow from higher
scope to lower scope, left to right):

```bash
$ envstack [STACK [STACK ...]]
```

#### Executing Scripts

Environment stack files are also executable scripts that can be run directly:


```bash
$ ./env/test.env
DEPLOY_ROOT=${ROOT}/${STACK}
ENV=${STACK}
ENVPATH=${DEPLOY_ROOT}/env:${ROOT}/prod/env
HELLO=${HELLO:=world}
LOG_LEVEL=DEBUG
PATH=${DEPLOY_ROOT}/bin:${ROOT}/prod/bin:${PATH}
PYTHONPATH=${DEPLOY_ROOT}/lib/python:${ROOT}/prod/lib/python:${PYTHONPATH}
ROOT=/mnt/pipe
STACK=test
```

Run commands inside a specific environment stack file:

```bash
$ ./env/test.env -- <command>
```

For example:

```bash
$ ./env/hello.env -- echo {HELLO}
world
```

Export a specific environment stack file:

```bash
$ ./env/hello.env --export
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

Several example or starter stacks are available in the [env folder of the
envstack repo](https://github.com/rsgalloway/envstack/tree/master/env).

To create a blank environment stack, create a new envstack file and declare some
variables.

Create a new stack file called "foobar.env" and make it executable (note: at
least one VAR needs to be defined under all):

#### foobar.env

```yaml
#!/usr/bin/env envstack

all: &default
  FOO: bar
  BAR: ${FOO}
darwin:
  <<: *default
linux:
  <<: *default
windows:
  <<: *default
```

Make it executable

```bash
$ chmod +x ./foobar.env
```

To see the resolved environment for the `foobar` stack, run:

```bash
$ envstack foobar
FOO=bar
BAR=$FOO
```

or execute it directly:

```bash
$ ./foobar.env
```

To see resolved values:

```bash
$ ./foobar.env -r
FOO=bar
BAR=bar
```

#### More Details

Variables can be platform specific:

```yaml
darwin:
  <<: *default
  HELLO: olleh
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
probably always include the `default` stack):

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

Creating and resolving environments:

```python
>>> from envstack.env import Env, resolve_environ
>>> env = Env({"BAR": "${FOO}", "FOO": "foo"})
>>> resolve_environ(env)
{'BAR': 'foo', 'FOO': 'foo'}
```

Loading and resolving predefined environments from stack files:

```python
>>> from envstack.env import load_environ, resolve_environ
>>> env = resolve_environ(load_environ(name))
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
  PYEXE: /usr/bin/python
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

## Config

The following environment variables are used to help manage functionality:

| Name | Description |
|------|-------------|
| ENVPATH | Colon-separated paths to search for stack files |
| IGNORE_MISSING | Ignore missing stack files when resolving environments |
| STACK | Name of the current environment stack |

# Tests

Unit tests can be run using pytest (currently only tested on linux):

```bash
$ pytest tests -s
```