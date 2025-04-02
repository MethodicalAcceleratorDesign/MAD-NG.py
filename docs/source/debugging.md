```{eval-rst}
.. currentmodule:: pymadng
```

# Debugging & Troubleshooting in PyMAD-NG

This guide explains how to diagnose and fix common issues in PyMAD-NG’s communication with MAD-NG. You’ll learn how to enable debug output, inspect logs, redirect streams, and avoid typical pitfalls (like deadlocks or type mismatches).

```{contents}
:depth: 2
:local:
```

---

## 1. Enable Debug Mode

When you initialize the {class}`MAD` object with `debug=True`, MAD-NG runs in a verbose mode. This prints extra information about each command you send, as well as diagnostic messages from the Lua side.

```python
from pymadng import MAD

mad = MAD(debug=True)
```

### 1.1 Redirecting Output
By default, PyMAD-NG writes MAD-NG’s standard output to Python’s `sys.stdout`. To redirect it:

```python
# Send MAD-NG stdout to a file
mad = MAD(debug=True, stdout="mad_debug.log")
```

If you need to redirect standard error as well:

```python
mad = MAD(debug=True, stdout="mad_debug.log", redirect_stderr=True)
```

This helps keep logs organized, especially when running long scripts.

---

## 2. Inspecting Command History

PyMAD-NG keeps track of all **string-based commands** sent to MAD-NG in a history buffer. To review them:

```python
print(mad.history())
```

This is invaluable for tracing unexpected behavior. For instance, if you suspect a weird command or an incorrect syntax was sent, you can look up the last lines in the history.

```{note}
Binary data (like large NumPy arrays) won’t appear in `mad.history()`. Only textual commands are recorded.
```

---

## 3. Communication Rules

### 3.1 Send Before Receive

PyMAD-NG uses pipes for **first-in-first-out** communication. If you call:

```python
mad.recv()  # This will block forever if there's nothing to read!
```

without telling MAD-NG to `py:send(...)` first, your script will hang.

**Correct Sequence**:
1. `mad.send(...)`
2. `mad.recv()`

Any mismatch in these calls can lead to deadlocks.

### 3.2 Matching Data Transfers

If you instruct MAD-NG to receive data (`arr = py:recv()`), you must ensure Python **actually sends** that data:

```python
mad.send("arr = py:recv()")
mad.send(my_array)  # Actually transmit the data
```

Failing to do so can cause indefinite blocking or partial reads.

---

## 4. Handling Errors

### 4.1 Protected Sends

All sends in PyMAD-NG are automatically “protected” by default. If MAD-NG issues an error (`err_`), PyMAD-NG raises a `RuntimeError` on the Python side.

```python
try:
    mad.send("invalid_lua_code").recv()
except RuntimeError as e:
    print("Caught MAD-NG error:", e)
```

If you need to **ignore** an error and continue, you can instantiate:

```python
mad = MAD(raise_on_madng_error=False)
```

and manually check for failures.

---

## 5. Debugging Subprocess Behavior

### 5.1 Starting MAD-NG

During initialization, PyMAD-NG calls:

```
mad_binary -q -e "MAD.pymad 'py' {_dbg = true} :__ini(fd)"
```

- If `mad_binary` is missing or not executable, you’ll get `FileNotFoundError`.
- If it fails to run, an `OSError` is raised.

### 5.2 Checking Streams

- **stdout**: By default prints to Python’s standard output unless you pass `stdout=...`.
- **stderr**: Remains attached to Python’s own stderr, unless you specify `redirect_sterr=True`.

---

## 6. Common Pitfalls & Solutions

| Issue                                    | Possible Cause                                                   | Recommended Fix                                           |
|------------------------------------------|------------------------------------------------------------------|-----------------------------------------------------------|
| **Hang / Deadlock**                      | Called `mad.recv()` without `mad.send(...)`, or vice versa       | Always pair `send()` → `recv()`. Use `debug=True` to see if MAD is expecting data. |
| **BrokenPipeError**                      | MAD-NG crashed or closed unexpectedly                            | Re-initialize `MAD()`. Check logs for the underlying error.                        |
| **“Unsupported data type”** error        | Attempted to `send()` an object that PyMAD-NG can’t serialize    | Limit data to `str`, `int`, `float`, `bool`, `list`, or `np.ndarray`.             |
| **AttributeError / KeyError** accessing a field | Tried to read a reference property without evaluating it first | Call `.eval()` if you need the actual value.                                     |
| **Exceeding `_last[]`** references       | Too many temp variables stored in `_last[]`                      | Manually name them in MAD, or increase `num_temp_vars`.                           |

---

## 7. Cleaning Up

If you’re done using MAD-NG, **close** the session:

```python
mad.close()
```

or use Python’s **context manager**:

```python
with MAD(debug=True) as mad:
    mad.send("a = 1 + 2").recv()
    ...
# Subprocess automatically ends here
```

---

## 8. Summary

- **Enable** `debug=True` to see more logs.
- **Check** `mad.history()` to identify incorrect or unexpected commands.
- **Balance** each `mad.send()` with a `mad.recv()` to avoid deadlocks.
- **Catch** `RuntimeError` to handle failures gracefully.
- **Evaluate** references (`.eval()`) if you need real values from objects in MAD.

If you still have trouble:
- Look at the [Architecture Overview](architecture.md) for the internal design.
- See [Contributing](contributing.md) for details on how to extend or fix PyMAD-NG’s internals.
- Open an issue on GitHub if you suspect a bug in the code.

Happy debugging!

