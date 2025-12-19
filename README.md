envstack
========

Environment variable management system.

[Installation](#installation) |
[Quickstart](#quickstart) |
[Setting Values](#setting-values) |
[Creating Stacks](#creating-stacks) |
[Encryption](#encryption) |
[Usage](#usage) |
[Python API](#python-api) |
[Running Commands](#running-commands)

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
$ pip install -U distman
$ ENVPATH=./env dist [-d]
```

Using distman will deploy the targets defined in the `dist.json` file to the
root folder defined by `${DEPLOY_ROOT}` (defined in `env/default.env`).

## Quickstart

Start by getting the latest `default.env` environment stack file:

```bash
$ curl -o default.env https://raw.githubusercontent.com/rsgalloway/envstack/master/env/default.env
```

Alternatively, set `${ENVPATH}` to the directory containing your environment
stack files:

```bash
$ export ENVPATH=/path/to/env/files
```

Define as many paths as you want, and envstack will search for stack files in
order from left to right, for example:

```bash
$ export ENVPATH=/mnt/pipe/dev/env:/mnt/pipe/prod/env
```

In the examples above, stack files in `dev` will take precedence over those
found in `prod`.

#### Basic Usage

Running the `envstack` command will show you the default, unresolved environment
stack, defined in `default.env` files in `${ENVPATH}`:

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

If you are not seeing the above output, make sure the `default.env` stack file
is in `${ENVPATH}` or the current working directory.

> NOTE: The name of the current stack will always be stored in `${STACK}`.

ENV is the tier, STACK is the namespace.

Environments can be combined, or stacked, in order of priority (variables
defined in stacks flow from higher scope to lower scope, left to right):

```bash
$ envstack [STACK [STACK ...]]
```

#### Resolving Values

To resolve an environment stack or a variable use `--resolve/-r [VAR]`. 

```bash
$ envstack -r HELLO
HELLO=world
$ envstack -r DEPLOY_ROOT
DEPLOY_ROOT=/mnt/pipe/prod
```

## Setting Values

Envstack uses bash-like variable expansion modifiers. Setting `$VAR` to a fixed
value means `$VAR` will always use that value. Using an expansion modifier
allows you to override the value:

| Value | Description |
|---------------------|-------------|
| value |  'value' |
| ${VAR:=default} | VAR = VAR or 'default' |
| ${VAR:-default} | os.environ.get('VAR', 'default') |
| ${VAR:?error message} | if not VAR: raise ValueError() |

Without the expansion modifier, values are set and do not change (but can be
overridden by lower scope stacks, i.e. a lower scope stack file may override
a higher one). 

If we define `${HELLO}` like this:

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

#### Using the command-line

Here we can set values using the `envstack` command:

```bash
$ envstack --set HELLO=world
HELLO=world
```

We can also encrypt the values automatically (base64 by default):

```bash
$ envstack -s HELLO=world -e
HELLO=d29ybGQ=
```

Add more variables (note that `$` needs to be escaped in bash or else it will
be evaluated immediately):

```bash
$ envstack -s HELLO=world VAR=\${HELLO}
HELLO=world
VAR=${HELLO}
```

To write out the results to an env file, use the `-o` option:

```bash
$ envstack -s HELLO=world -o hello.env
```

You can convert existing `.env` files to envstack by piping them into envstack:

```bash
$ cat .env | envstack --set -o out.env
```

## Creating Environments

Several example or starter stacks are available in the [env folder of the
envstack repo](https://github.com/rsgalloway/envstack/tree/master/env).

To create a new environment file, use `--set` to declare some variables:

```bash
$ envstack -s FOO=bar BAR=\${FOO} -o out.env
```

Using Python:

```python
>>> env = Env({"FOO": "bar", "BAR": "${FOO}"})
>>> env.write("out.env")
```

Get the resolved values back:

```bash
$ ./out.env -r
BAR=bar
FOO=bar
STACK=out
```

#### More Details

Variables can be platform specific:

```yaml
darwin:
  HELLO: olleh
linux:
  HELLO: world
windows:
  HELLO: goodbye
```

Variables can reference other variables:

```yaml
all: &all
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

Here is an example using nested variable expansion:

```yaml
FOO: ${BIZ:=${BAR:=${BAZ:=baz}}}
```

Resolves to:

```bash
$ envstack -r
FOO=baz
```

#### Includes

Environment stack files can include other namespaced environments (you should
probably always include the `default` stack):

```yaml
include: [default, test]
```

## Encryption

Supported encryption algorithms include
[AES-GCM](https://en.wikipedia.org/wiki/Galois/Counter_Mode),
[Fernet](https://github.com/fernet/spec/),
and
[Base64](https://en.wikipedia.org/wiki/Base64). This allows
you to securely encrypt and decrypt sensitive environment variables.

To use AES-GCM or Fernet, and encryption key must be found somewhere in the
environment. No key is required for Base64 encryption (the default). Encrypted
nodes look for keys in the following order, favoring AES-GCM over Fernet:

| Algorithm | Key |
|---------|-------------|
| Base64 | (no key required) |
| AES-GCM | ${ENVSTACK_SYMMETRIC_KEY} |
| Fernet | ${ENVSTACK_FERNET_KEY} |

If no encryption keys are found in the environment, envstack will default to
using Base64 encoding:

```bash
$ envstack --encrypt
DEPLOY_ROOT=JHtST09UfS8ke0VOVn0=
ENV=cHJvZA==
ENVPATH=JHtERVBMT1lfUk9PVH0vZW52OiR7RU5WUEFUSH0=
HELLO=JHtIRUxMTzo9d29ybGR9
LOG_LEVEL=JHtMT0dfTEVWRUw6PUlORk99
PATH=JHtERVBMT1lfUk9PVH0vYmluOiR7UEFUSH0=
PYTHONPATH=JHtERVBMT1lfUk9PVH0vbGliL3B5dGhvbjoke1BZVEhPTlBBVEh9
ROOT=L21udC9waXBl
STACK=ZGVmYXVsdA==
```

#### Generating Keys

To use AES-GCM or Fernet encryption and serialize to an `encrypted.env` file,
first generate and source keys in the shell using the `--keygen` option:

```bash
$ source <(envstack --keygen --export)
```

Once the keys are in the environment, you can encrypt the env stack:

```bash
$ envstack -o encrypted.env --encrypt
```

Encrypted variables will resolve as long as the key is in the environment:

```bash
$ envstack encrypted -r HELLO
HELLO=world
```

#### Storing Keys

Keys can be stored in other environment stacks, e.g. a `keys.env` file
(keys are automatically base64 encoded):

```bash
$ envstack --keygen -o keys.env
```

Then use `keys.env` to encrypt any other environment files:

```bash
$ ./keys.env -- envstack -eo encrypted.env
```

To decrypt, run the command inside the `keys` environment again:

```bash
$ ./keys.env -- envstack encrypted -r HELLO
HELLO=world
```

Or add `keys` to the env stack:

```bash
$ envstack keys encrypted -r HELLO
HELLO=world
```

Or automatically include `keys`:

```yaml
include: [keys]
```

Variables will automatically decrypt when resolved:

```bash
$ ./encrypted.env -r HELLO
HELLO=world
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

To run commands in an environment stack:

```bash
$ envstack [STACK] -- [COMMAND]
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

Create an encrypted environment:

```python
>>> from envstack.env import Env, encrypt_environ
>>> env = Env({"SECRET": "super_secret", "PASSWORD": "my_password"})
>>> encrypted = encrypt_environ(env)
```

Loading and resolving predefined environments from stack files:

```python
>>> from envstack.env import load_environ, resolve_environ
>>> env = load_environ(name)
>>> resolved = resolve_environ(env)
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

Running a node command:

```bash
$ echo "console.log('Hello ' + process.env.HELLO)" > index.js
$ node index.js 
Hello undefined
$ envstack hello -- node index.js 
Hello world
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
all: &all
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

#### Executing Scripts

On linux, environment stack files are also executable scripts that can be called
directly:

```bash
$ ./test.env
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
$ ./test.env -- [COMMAND]
```

For example:

```bash
$ ./hello.env -- echo {HELLO}
world
```

Export a specific environment stack file:

```bash
$ ./hello.env --export
```

## Config

The following environment variables are used to help manage functionality:

| Name | Description |
|------|-------------|
| DEFAULT_ENV_STACK | Name of the default environment stack (default) |
| ENVPATH | Colon-separated paths to search for stack files |
| IGNORE_MISSING | Ignore missing stack files when resolving environments |
| STACK | Stores the name of the current environment stack |

# Tests

Unit tests can be run using pytest (note: some tests fail on win32 currently).
Make sure you don't have any local .env files that may intefere with the unit
tests.

```bash
$ pytest tests -s
```