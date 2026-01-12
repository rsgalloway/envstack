## Project Example

Download the `project.env` env file:

```shell
curl -o \
project.env \
https://raw.githubusercontent.com/rsgalloway/envstack/master/examples/project/project.env
```

This environment gives precedence to project names in paths (e.g. `PATH` and
`PYTHONPATH`). It also sets `ENV` to the stack name:

```shell
$ envstack project -u
DEPLOY_ROOT=${ROOT}/${ENV}
ENV=${STACK:=${ENV}}
ENVPATH=${ROOT}/${ENV}/env:${ROOT}/prod/env
PATH=${ROOT}/${ENV}/bin:${ROOT}/prod/bin:${PATH}
PYTHONPATH=${ROOT}/${ENV}/lib/python:${ROOT}/prod/lib/python:${PYTHONPATH}
STACK=project
```

So any stack name in the `envstack` command is given precedence:

```shell
$ envstack project test -q
(test) ~$ 
```
```shell
$ envstack project foobar -q
(foobar) ~$ 
```

The advantage of this is that tools can be disted, for example using distman,
to arbitrary deployment roots and activated with envstack.
