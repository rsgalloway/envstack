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
