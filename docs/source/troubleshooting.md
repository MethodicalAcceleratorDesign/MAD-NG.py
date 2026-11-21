```{eval-rst}
.. currentmodule:: pymadng
```

# Troubleshooting

## A script hangs

Python is waiting for MAD-NG, and MAD-NG is waiting for Python. Check each {meth}`mad.recv() <pymadng.MAD.recv>` has a `py:send(...)` before it, and each `py:recv()` has a {meth}`mad.send(data) <pymadng.MAD.send>` after it. The rules and an example are in {doc}`communication`.

## Read the output of MAD-NG

MAD-NG output goes to the Python `sys.stdout` by default. Write it to a file, with the error output included:

```python
mad = MAD(stdout="mad.log", redirect_stderr=True)
```

Without `redirect_stderr=True`, the error output stays on the Python `sys.stderr`.

## See the commands that were sent

With `debug=True`, MAD-NG runs in its debug mode and PyMAD-NG records the text commands (binary data, such as arrays, is not recorded):

```python
mad = MAD(debug=True)
mad.send("a = 1 + 2")
print(mad.history())
```

## Errors in MAD-NG

An error in MAD-NG raises `RuntimeError("MAD Errored (see the MAD error output)")` in Python, and the message of MAD-NG is in its error output. To continue after errors, and check for failures yourself:

```python
mad = MAD(raise_on_madng_error=False)
mad.send("invalid lua code")
mad.send("py:send(1)")
assert mad.recv() == 1
```

## Common errors

| Symptom | Cause | Fix |
|---|---|---|
| The script hangs | `recv()` without a `py:send`, or a send that MAD-NG never reads | Pair every send with its receive ({doc}`communication`) |
| `AssertionError: Assigned too many anonymous variables` | All `num_temp_vars` temporary references are alive | Name results with `mad["name"] = ...`, delete references, or raise `num_temp_vars` ({doc}`references`) |
| A variable set from Python is missing in MAD-NG | `mad.x = 5` sets a Python attribute | Use `mad["x"] = 5` |
| A reference shows no properties | References are evaluated by MAD-NG | Call `.eval()` or `.to_df()` |

## End the session

Use a context manager so the MAD-NG process ends with the block, or call {meth}`mad.close() <pymadng.MAD.close>`:

```python
with MAD() as mad:
    mad.send("a = 1 + 2")
```
