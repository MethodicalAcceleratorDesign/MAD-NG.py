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

When you initialise the {class}`MAD` object with `debug=True`, MAD-NG runs in a verbose mode. This prints extra information about each command you send, as well as diagnostic messages from the Lua side.

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

This helps keep logs organised, especially when running long scripts.

---

## 2. Interactive MAD Debugger

PyMAD-NG now exposes MAD-NG's `MAD.dbg()` debugger directly through the Python wrapper.

### 2.1 Entering the Debugger from Python

Use {meth}`MAD.breakpoint` to stop inside MAD-NG and interact with the debugger from the Python terminal:

```python
from pymadng import MAD

with MAD() as mad:
    mad.breakpoint()
```

There is also a shorter alias:

```python
mad.pydbg()
```

When the Python process is attached to a real terminal, PyMAD-NG uses Python's line editor for the debugger prompt. That gives you normal command editing while still sending completed commands to `MAD.dbg()`.

```{note}
The visible debugger prompt is re-drawn by Python, not by MAD-NG directly. This keeps cursor positioning, history navigation, and prompt colouring stable even though MAD-NG itself is running behind a pipe.
```

### 2.2 Entering the Debugger from MAD-NG Code

During process startup, PyMAD-NG defines these MAD-side helper functions:

- `python_breakpoint()`
- `pydbg()`
- `breakpoint()`

That means ordinary MAD strings can drop into the debugger directly:

```python
mad.send("breakpoint()")
```

or from within larger MAD programs:

```python
mad.send(
    """
if my_condition then
  pydbg()
end
"""
)
```

### 2.3 Entering the Debugger from `py:send([[...]])`

The Python execution bridge also exposes `breakpoint` and `pydbg` when using {meth}`MAD.recv_and_exec`.

```python
mad.send("py:send([[breakpoint()]])")
mad.recv_and_exec()
```

This is useful when MAD-NG wants to request a Python-driven debugging pause without embedding the control flow on the Python side ahead of time.

You can also use the alias:

```python
mad.send("py:send([[pydbg()]])")
mad.recv_and_exec()
```

### 2.4 Scripted Debugger Commands

For tests, automation, or non-interactive environments, pass a list of debugger commands:

```python
mad.breakpoint(commands=["h", "c"])
```

This sends:

1. `h` to print help
2. `c` to continue execution

This mode is especially useful in unit tests, CI jobs, and examples where a real terminal is not available.

### 2.5 Continue vs Quit

The MAD debugger has two very different exit modes:

- `c` / `continue`: resume execution and keep the MAD process alive
- `q` / `quit`: terminate the MAD process

If you quit from the debugger, PyMAD-NG closes its side of the pipes cleanly and returns from {meth}`MAD.breakpoint` without raising a traceback. After that, the `MAD` session is finished and should be recreated before sending more commands.

### 2.6 Practical Example

```python
from pymadng import MAD

with MAD() as mad:
    mad.send("a = 2")
    mad.send("b = 3")
    mad.send(
        """
function inspect_sum()
  local total = a + b
  if total == 5 then
    breakpoint()
  end
  py:send(total)
end
inspect_sum()
"""
    )
    print(mad.recv())
```

### 2.7 Terminal Limitations

The debugger bridge works over the same pipes used for normal PyMAD-NG communication. Because of that:

- MAD-NG itself is **not** attached to your terminal directly
- line editing is provided on the Python side when a terminal is available
- in non-terminal environments, use `commands=[...]` or a basic line-oriented stream

If you are in a notebook or another non-TTY environment, prefer scripted commands:

```python
mad.breakpoint(commands=["where", "c"])
```

---

## 3. Inspecting Command History

PyMAD-NG keeps track of all **string-based commands** sent to MAD-NG in a history buffer. To review them:

```python
print(mad.history())
```

This is invaluable for tracing unexpected behaviour. For instance, if you suspect a weird command or an incorrect syntax was sent, you can look up the last lines in the history.

```{note}
Binary data (like large NumPy arrays) won’t appear in `mad.history()`. Only textual commands are recorded.
```

---

## 4. Communication Rules

### 4.1 Send Before Receive

PyMAD-NG uses pipes for **first-in-first-out** communication. If you call:

```python
mad.recv()  # This will block forever if there's nothing to read!
```

without telling MAD-NG to `py:send(...)` first, your script will hang.

**Correct Sequence**:
1. `mad.send(...)`
2. `mad.recv()`

Any mismatch in these calls can lead to deadlocks.

### 4.2 Matching Data Transfers

If you instruct MAD-NG to receive data (`arr = py:recv()`), you must ensure Python **actually sends** that data:

```python
mad.send("arr = py:recv()")
mad.send(my_array)  # Actually transmit the data
```

Failing to do so can cause indefinite blocking or partial reads.

---

## 5. Handling Errors

### 5.1 Protected Sends

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

## 6. Debugging Subprocess Behaviour

### 6.1 Starting MAD-NG

During initialisation, PyMAD-NG calls:

```
mad_binary -q -e "<startup chunk creating pymad bridge, debugger aliases, and __ini(fd)>"
```

- If `mad_binary` is missing or not executable, you’ll get `FileNotFoundError`.
- If it fails to run, an `OSError` is raised.
- The startup chunk now also exports MAD-side debugger aliases (`python_breakpoint`, `pydbg`, and `breakpoint`) before entering the pipe loop.

### 6.2 Checking Streams

- **stdout**: By default prints to Python’s standard output unless you pass `stdout=...`.
- **stderr**: Remains attached to Python’s own stderr, unless you specify `redirect_stderr=True`.

---

## 7. Common Pitfalls & Solutions

| Issue                                    | Possible Cause                                                   | Recommended Fix                                           |
|------------------------------------------|------------------------------------------------------------------|-----------------------------------------------------------|
| **Hang / Deadlock**                      | Called `mad.recv()` without `mad.send(...)`, or vice versa       | Always pair `send()` → `recv()`. Use `debug=True` to see if MAD is expecting data. |
| **BrokenPipeError**                      | MAD-NG crashed or closed unexpectedly                            | Re-initialise `MAD()`. Check logs for the underlying error.                        |
| **Debugger `q` ended the session**       | `q` in `MAD.dbg()` terminates the MAD subprocess                 | Create a new `MAD()` instance if you want to continue working.                     |
| **Arrow keys or history unavailable**    | Running without a real terminal                                  | Use a standard terminal or scripted `commands=[...]`.                              |
| **“Unsupported data type”** error        | Attempted to `send()` an object that PyMAD-NG can’t serialise    | Limit data to `str`, `int`, `float`, `bool`, `list`, or `np.ndarray`.             |
| **AttributeError / KeyError** accessing a field | Tried to read a reference property without evaluating it first | Call `.eval()` if you need the actual value.                                     |
| **Exceeding `_last[]`** references       | Too many temp variables stored in `_last[]`                      | Manually name them in MAD, or increase `num_temp_vars`.                           |

---

## 8. Cleaning Up

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

## 9. Summary

- **Enable** `debug=True` to see more logs.
- **Use** `mad.breakpoint()` to drop into `MAD.dbg()` from Python.
- **Call** `breakpoint()` or `pydbg()` inside MAD strings when you want MAD-side code to trigger debugging.
- **Trigger** `breakpoint()` or `pydbg()` inside `py:send([[...]])` blocks when using `mad.recv_and_exec()`.
- **Check** `mad.history()` to identify incorrect or unexpected commands.
- **Balance** each `mad.send()` with a `mad.recv()` to avoid deadlocks.
- **Catch** `RuntimeError` to handle failures gracefully.
- **Evaluate** references (`.eval()`) if you need real values from objects in MAD.

If you still have trouble:
- Look at the [Architecture Overview](architecture.md) for the internal design.
- See [Contributing](contributing.md) for details on how to extend or fix PyMAD-NG’s internals.
- Open an issue on GitHub if you suspect a bug in the code.

Happy debugging!
