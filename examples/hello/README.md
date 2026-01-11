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