# Variable Expansion

envstack supports Bash-like variable expansion inside stack values.

This is the syntax behind values such as `${ROOT}/${ENV}`,
`${LOG_LEVEL:=INFO}`, and nested defaults like `${VAR:=${FOO:=bar}}`.

## Supported forms

| Form | Meaning |
|------|---------|
| `${VAR}` | Use `VAR`, or an empty string if it is unset |
| `${VAR:=default}` | If `VAR` is unset or empty, use `default` and assign it during resolution |
| `${VAR:-default}` | If `VAR` is unset or empty, use `default` without assigning it |
| `${VAR:?message}` | Raise an error if `VAR` is unset or empty |

These rules apply both in stack files and when resolving values through the
Python API.

## Simple substitution

Direct references are resolved against the current stack and then fall back to
the parent or process environment:

```yaml
ROOT: /mnt/pipe
ENV: prod
DEPLOY_ROOT: ${ROOT}/${ENV}
```

Resolved output:

```bash
DEPLOY_ROOT=/mnt/pipe/prod
```

If a variable is unset and no modifier is used, envstack resolves it to an
empty string:

```yaml
OPTIONAL_SUFFIX: ${SUFFIX}
```

## Defaults With `:=`

Use `:=` when the fallback should become the variable's effective value for the
rest of the resolution pass:

```yaml
LOG_LEVEL: ${LOG_LEVEL:=INFO}
```

If `LOG_LEVEL` is unset or empty, envstack resolves it as `INFO`.

This is especially useful when later values depend on the same variable:

```yaml
ENV: ${ENV:=prod}
ROOT: ${ROOT:=/mnt/pipe}
DEPLOY_ROOT: ${ROOT}/${ENV}
```

## Defaults Without Assignment With `:-`

Use `:-` when you want a fallback in one expression without changing the
variable itself:

```yaml
PROMPT_COLOR: ${PROMPT_COLOR:-green}
```

This is helpful when a value should have a display or formatting fallback, but
you do not want that fallback to become the new resolved value of
`PROMPT_COLOR`.

## Required Variables With `:?`

Use `:?` when the stack should fail loudly if a required value is missing:

```yaml
DEPLOY_ROOT: ${DEPLOY_ROOT:?set DEPLOY_ROOT before launching this stack}
```

This is useful for secrets, mount points, or site-specific paths that must be
provided externally.

## Nested Defaults

Defaults can contain other expansions:

```yaml
FOO: ${FOO:=${BAR:=/foo/bar}}
```

If neither `FOO` nor `BAR` is already set, this resolves to:

```bash
FOO=/foo/bar
BAR=/foo/bar
```

Nested expressions are often the cleanest way to define a chain of fallbacks
without repeating the final literal value.

## Mixed Strings

Expansion can appear inside larger strings:

```yaml
PYTHONPATH: ${DEPLOY_ROOT}/lib/python:${PYTHONPATH}
PATH: ${DEPLOY_ROOT}/bin:${PATH}
```

That makes it easy to build derived paths, URLs, prompts, or command lines from
shared variables.

## Template Tokens Stay Literal

envstack only resolves `${NAME}`-style expressions.

Brace tokens such as `{show}` or `{shot}` are preserved as literal template
placeholders:

```yaml
NUKESCRIPT: ${ROOT}/projects/{show}/{shot}/comp/{show}_{shot}.{version}.nk
```

If `ROOT` resolves to `/mnt/pipe`, the remaining `{show}`-style placeholders
stay intact for downstream tooling.

## Command Substitution

Variable expansion and command substitution can be combined:

```yaml
PYVERSION: $(python -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')")
PYTHONPATH: ${DEPLOY_ROOT}/lib/python${PYVERSION}
```

Command substitution is separate from modifier syntax and is only evaluated when
embedded commands are allowed.

## Resolution Notes

- Empty strings are treated the same as unset values for `:=`, `:-`, and `:?`.
- Nested expressions are supported in modifier arguments.
- Cyclical references resolve to an empty string instead of recursing forever.
- Path-like results such as `PATH` and `PYTHONPATH` are normalized and
  deduplicated during resolution.

## See Also

- [Default example](examples/default.md): practical stack examples using nested
  defaults and derived paths
- [Python API](api.md): loading and resolving environments programmatically
- [FAQ](faq.md): operational tradeoffs and common envstack questions
