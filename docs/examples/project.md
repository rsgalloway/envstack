# Project Example

Download the `project.env` env file:

```shell
curl -o \
project.env \
https://raw.githubusercontent.com/rsgalloway/envstack/master/examples/project/project.env
```

This environment uses the active stack name as a scope selector. It gives the
stack-specific directory precedence in paths such as `PATH` and `PYTHONPATH`,
and also sets `ENV` to the stack name:

```shell
$ envstack project -u
DEPLOY_ROOT=${ROOT}/${ENV}
ENV=${STACK:=${ENV}}
ENVPATH=${ROOT}/${ENV}/env:${ROOT}/prod/env
PATH=${ROOT}/${ENV}/bin:${ROOT}/prod/bin:${PATH}
PYTHONPATH=${ROOT}/${ENV}/lib/python:${ROOT}/prod/lib/python:${PYTHONPATH}
STACK=project
```

Here the stack name identifies the file, while the directory identified by
`${ENV}` supplies the scope:

```text
${ROOT}/${ENV}/env/project.env
```

Because earlier `ENVPATH` entries have higher precedence, the scoped directory
takes precedence over `${ROOT}/prod/env`.

So any stack name in the `envstack` command becomes the higher-priority scope:

```shell
$ envstack project test -q
(test) ~$
```
```shell
$ envstack project foobar -q
(foobar) ~$
```

This pattern is useful when tools are deployed to predictable roots and the
stack name selects the active project, branch, or task context.
