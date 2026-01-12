# envstack

envstack is a **stacked environment configuration and activation layer** for tools
and processes.

It provides a deterministic way to **activate environments and compose
configuration hierarchically**, using explicit layering, inheritance, and
overrides.

At its core, envstack is about:
- Environment activation
- Configuration layering
- Policy and precedence
- Making sure tools run with the correct environment

## The problem envstack solves

Real environments are not flat.

They are:
- Hierarchical (base → env → project → task)
- Contextual (dev, prod, CI, local)
- Layered over time
- Full of defaults, overrides, and exceptions

Flat `.env` files don’t model this well. envstack treats environment
configuration as a **stack**: ordered, inspectable, and reproducible.

## Core concepts

### Environment stacks
An environment stack is one or more named environments combined in order.
Stacks define **precedence**: variables flow from higher scope to lower scope,
with explicit overrides.

### Hierarchy and inheritance
Environments can inherit from other environments, forming a hierarchy.
Downstream environments may refine or override upstream values without
duplication.

### Includes
Environment definitions may include other environments declaratively,
allowing shared base configuration to be reused consistently.

### Resolution
Variables can reference other variables, define defaults, or require values
to be set. Resolution is explicit and inspectable before execution.

## What envstack is (and is not)

**envstack is:**
- A configuration layer for environment variables
- An environment activation mechanism
- A system for hierarchical configuration composition

**envstack is not:**
- A dependency resolver
- A package manager
- A runtime isolation tool by default

envstack focuses on **how environments are composed and activated**, not how
dependencies are installed.

## Typical uses

envstack is commonly used for:
- CLI tools
- Services
- CI/CD pipelines
- Developer workstations
- Pipeline and DCC tooling
- Shared, hierarchical environment configuration

## A simple example

```yaml
ROOT: /mnt/pipe
ENV: ${ENV:=prod}
DEPLOY_ROOT: ${ROOT}/${ENV}
```

```bash
$ envstack -r DEPLOY_ROOT
DEPLOY_ROOT=/mnt/pipe/prod
```
```bash
$ envstack -- echo {DEPLOY_ROOT}
/mnt/pipe/prod
```

## Philosophy

"You want envstack. It’s what .env files wish they were when they grew up."

envstack is intentionally opinionated:

- Explicit over implicit
- Layered over flat
- Inspectable over magical

## Basic Usage

To see the unresolved environment for one or more environment stacks (values are
defined in the stacks from left to right):

```bash
$ envstack [STACK [STACK ...]] -u
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
$ envstack -- python -c "import os; print(os.environ['LOG_LEVEL'])"
INFO
```

Overriding values in the stack:

```bash
$ LOG_LEVEL=DEBUG envstack -- python -c "import os; print(os.environ['LOG_LEVEL'])"
DEBUG
```

## Resolving Values

To resolve an environment stack or a variable use `--resolve/-r [VAR]`. 

```bash
$ envstack -r ENV
ENV=prod
$ envstack -r DEPLOY_ROOT
DEPLOY_ROOT=/mnt/pipe/prod
```

## Setting Values

envstack uses bash-like variable expansion modifiers. Setting `$VAR` to a fixed
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

## Using the command-line

Here we can set values using the `envstack` command:

```bash
$ envstack --set HELLO=world
HELLO=world
```

We can also Base64 encode or encrypt values automatically:

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
envstack -s HELLO=world -o hello.env
```

Convert existing `.env` files to envstack by piping them into envstack:

```bash
cat .env | envstack --set -o out.env
```

## Creating Environments

Several example or starter stacks are available in the [env folder of the
envstack repo](https://github.com/rsgalloway/envstack/tree/master/env).

To create a new environment file, use `--set` to declare some variables:

```bash
envstack -s FOO=bar BAR=\${FOO} -o out.env
```
