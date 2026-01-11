## Usage

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
```
