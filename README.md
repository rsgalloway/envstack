envstack
========

Stacked environment variable management system. The lightweight, easy to use
"rez" alternative for production pipelines.

Environment variables are declared in namespaced .env files using yaml syntax.
The default stack is `stack` and variables are declared in `stack.env`
files. You can create any new stack by creating new `.env` files, e.g. creating
a new `test` stack just create `test.env` files.

> **Note:** envstack works best combined with [siteconf](https://github.com/rsgalloway/siteconf).

## Installation

The easiest way to install:

```bash
$ pip install envstack
```

## Quickstart

Copy the default stack file
[`stack.env`](https://github.com/rsgalloway/envstack/blob/master/stack.env)
to your current working directory, the root of your project or $DEFAULT_ENV_DIR if defined (defaults: /etc/envstack on posix platforms and C:/ProgramData/envstack on Windows).


```bach
$ cp stack.env $DEFAULT_ENV_DIR
```

The `stack` namespace is the default environment stack. Running the `envstack` command
should show you the resolved environment for your platform:

```bash
$ envstack
ENV 'prod'
HELLO 'world'
FOO 'bar'
PYVERSION 3.11
LIB 'lib/python3.11'
LOG_LEVEL 20
ROOT '/mnt/tools/lib/python3.11'
```

Modify the environment stack by updating `stack.env` or by creating new contextual
`stack.env` files up and down the project hierarchy.

You can execute any command inside the default stacked environment like this:

```bash
$ envstack -- <command>
```

For example:

```bash
$ envstack -- python -c "import os; print(os.environ['HELLO'])"
world
```

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

Environment stacks are hierarchical, so values for `$FOO` defined in .env files lower
in the filesystem (lower in scope) override those defined higher up (higher in scope):

```
/show/thing.env
/show/seq/thing.env
/show/seq/shot/thing.env
/show/seq/shot/task/thing.env
```

Variables can reference other variables defined elsewhere (but cannot be circular):

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

Environment files can include other namespaced environments (all stacks inherit the default stack.env automatically).

```yaml
include: ['other']
```

## Usage

To see the default resolved environment for any given scope (directory):

```bash
$ envstack
```

To see the resolved environment for a given namespace.

```bash
$ envstack <stack> [OPTIONS]
```

To resolve a `$VAR` declaration for a given environment stack:

```bash
$ envstack <stack> -r <VAR>
```

To trace where a `$VAR` declaration is being set:

```bash
$ envstack <stack> -t <VAR>
```

To see an environment stack on another platform:

```bash
$ envstack <stack> -p <platform>
```

## Python API

By default, `envstack.getenv` uses the resolved default env stack `stack` and can be
a drop-in replacement for `os.getenv` 

```python
>>> import envstack
>>> envstack.getenv("HELLO")
'world'
```

To use a different stack, use the `init` function:

```python
>>> envstack.init("thing")
>>> envstack.getenv("FOO")
'bar'
```

The `init` function also updates the current environment for code that is not using envstack:

```python
>>> os.getenv("FOO")
'bar'
```

## Running Commands

To run any command line executable inside of an environment stack, where `<command>`
is the command to run:

```bash
$ envstack <stack> -- <command>
```

For example, running python in the default stack (reading from the default `stack.env` file):

```bash
$ envstack -- python -c "import os; print(os.environ['HELLO'])"
world
```

Same command but using the "thing" stack"

```bash
$ envstack thing -- python -c "import os; print(os.environ['FOO'])"
bar
```

To source the environment in your current shell, source the output of --export (and create
an alias for convenience):

```bash
$ source <(envstack --export)
$ alias esinit='source <(envstack $ARG --export)'
```

In Windows command prompt:

```cmd
for /f "usebackq" %i in (`envstack --export`) do %i
```

## Config

Default config settings are in the config.py module. The following environment variables are supported:

| Variable            | Description |
|---------------------|-------------|
| $DEFAULT_ENV_DIR    | the folder containing the default env stack files |
| $DEFAULT_ENV_STACK  | the name of the default env stack namespace (default "stack") |
