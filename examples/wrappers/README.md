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
        self.shell = True

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

## Executing Scripts

In bash, envstack files are also executable scripts that can be called directly:

```bash
$ envstack test -s FOO=bar -o test.env
$ ./test.env -- echo {FOO}
bar
```

Or exported:

```bash
$ ./test.env --export
export FOO=bar
export STACK=test
```

## More Details

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

## Includes

Environment stack files can include other namespaced environments (you should
probably always include the `default` stack):

```yaml
include: [default, test]
```
