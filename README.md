envstack
========

Stacked environment variable management system. The lightweight, easy to use
"rez" alternative for production pipelines.

Environment variables are declared in namespaced .env files using yaml syntax.
The default stack declares env variables in `stack.env` files. You can create
any new stack by creating new `.env` files, e.g. to create a new `thing` stack
just create `thing.env` files in any given context.

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

The install process will automatically attempt to install the default
`stack.env` file to the default env file directory defined `$DEFAULT_ENV_DIR`.
**Note:** The [siteconf](https://github.com/rsgalloway/siteconf)
sitecustomize.py module may override `$DEFAULT_ENV_DIR`.

If installing from source, you can use
[distman](https://github.com/rsgalloway/distman) to
install envstack and the default `stack.env` file using the provided
`dist.json` file:

```bash
$ distman
```

## Quickstart

The `stack` namespace is the default environment stack. Running the `envstack`
command should show you the default environment stack:

```bash
$ envstack
ENV=prod
HELLO=world
LOG_LEVEL=INFO
DEFAULT_ENV_DIR=${DEPLOY_ROOT}/env
DEPLOY_ROOT=${ROOT}/${ENV}
ROOT=${HOME}/.local/envstack
```

You can override anything in the environment stack by setting values in the
local environment first:

```bash
$ envstack -- echo \$ENV
prod
$ ENV=dev envstack -- echo \$ENV
dev
```

Modify the environment stack by editing `stack.env` or by creating new
contextual `stack.env` files up on the filesystem.

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

Variables can be platform specific (and inherit the defaults):

```yaml
linux:
  <<: *default
  HELLO: world
```

Environment files can include other namespaced environments (all stacks inherit
the default stack.env automatically).

```yaml
include: ['other']
```

## Context

Environment stacks are hierarchical, so values for `$FOO` defined in .env files
lower in the filesystem (lower in scope) override those defined higher up
(higher in scope):

```
${DEFAULT_ENV_DIR}
/stack.env
/show/stack.env
/show/seq/stack.env
/show/seq/shot/stack.env
/show/seq/shot/task/stack.env
```

If you are working in the task directory, those envstack $VARs will override the
$VARs defined in the shot, seq, show and root directories.

## Usage

To see the default environment for any given stack:

```bash
$ envstack [STACK]
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

To init the environment stack, use the `init` function:

```python
>>> envstack.init("thing")
>>> os.getenv("FOO")
'bar'
```

Alternatively, `envstack.getenv` can be a drop-in replacement for `os.getenv`
for the default environment stack:

```python
>>> import envstack
>>> envstack.getenv("HELLO")
'world'
```

## Running Commands

To run any command line executable inside of an environment stack, where
`[COMMAND]` is the command to run:

```bash
$ envstack [STACK] -- [COMMAND]
```

For example:

```bash 
$ envstack -- echo \$HELLO
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

## Shells

In order to set an environment stack in your current shell, the stack must be
sourced (that's because Python processes and subshells cannot alter the
environment of the parent process).

To source the environment in your current shell, create an alias that sources
the output of the `--export` command:

#### bash
```bash
alias envstack-set='source <(envstack "$1" --export)';
```

#### cmd
```cmd
doskey envstack-set=for /f "usebackq" %i in (`envstack --export $*`) do %%i
```

Then you can set the environment stack in your shell with the `envstack-set`
command. To clear the environment in your current shell, create an alias that
sources the output of the `--clear` command:

#### bash
```bash
alias envstack-clear='source <(envstack "$1" --clear)';
```

#### cmd
```cmd
doskey envstack-clear=for /f "usebackq" %i in (`envstack --clear $*`) do %%i
```

Create a function for convenience that does both in one command:

#### bash
```bash
envstack-init() { envstack-clear "$1"; envstack-set "$1"; }
```

#### cmd
```cmd
doskey envstack-init=envstack-clear $* & envstack-set $*
```

## Config

Default config settings are in the config.py module. The following environment
variables are supported:

| Variable            | Description |
|---------------------|-------------|
| $DEFAULT_ENV_DIR    | the folder containing the default env stack files |
| $DEFAULT_ENV_STACK  | the name of the default env stack namespace |
