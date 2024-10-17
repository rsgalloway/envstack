envstack
========

Stacked environment variable management system. The lightweight, easy to use
"rez" alternative for production pipelines.

Environment variables are declared in namespaced .env files using yaml syntax.
The default stack is `stack` and variables are declared in `stack.env`
files. You can create any new stack by creating new `.env` files, e.g. creating
a new `test` stack just create `test.env` files.

Envstack works best combined with [siteconf](https://github.com/rsgalloway/siteconf).

## Quickstart

To create a new environment stack, create a new namespaced .env file.
For example, here is a simple `thing.env` file (the stack namespace is "thing"):

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

Environment files can include other namespaced environments:
```yaml
include: ['other']
```

Installation
------------

The easiest way to install:

```bash
$ pip install envstack
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

Running Commands
----------------

To run any command line executable inside of an environment stack, where `<command>`
is the command to run:

```bash
$ enstack <stack> -- <command>
```

For example, running python in the default stack (reading from the default `stack.env` file):

```bash
$ envstack -- python -c "from envstack.env import environ; print(environ['HELLO'])"
world
```

Same command but using the "thing" stack"

```bash
$ envstack thing -- python -c "from envstack.env import environ; print(environ['FOO'])"
bar
```
