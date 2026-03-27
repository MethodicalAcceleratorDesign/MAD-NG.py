# Communication with MAD-NG

```{contents}
:depth: 2
:local:
```

## Protocol Overview

PyMAD-NG communicates with MAD-NG using a **pipe-based protocol**, ensuring efficient, direct, two-way communication between the Python and MAD-NG processes.

Key points:

- Data is sent through FIFO pipes (first-in, first-out).
- Commands are sent as MAD-NG script strings (Lua-like).
- Data is retrieved via `{func}`MAD.recv`()` after explicit instruction to send it.
- MAD-NG stdout is redirected to Python, but not intercepted.

```{tip}
Think of PyMAD-NG as controlling a persistent remote interpreter. Python and MAD-NG do not share memory; they exchange commands, references, and serialised data through pipes.
```

```{important}
You must always **send instructions before sending data**, and **send a request before receiving data**.
```

### Example: Basic Communication
```python
from pymadng import MAD
mad = MAD()

mad.send("a = py:recv()")   # Tell MAD-NG to receive
mad.send(42)                # Send the value
mad.send("py:send(a)")     # Request it back
mad.recv()                  # Receive the value → 42
```

Both {func}`MAD.send` and {func}`MAD.recv` are the core communication methods.
See the {class}`pymadng.MAD` reference for more details.

### Two Common Patterns

#### Pattern A: MAD-NG asks Python for data

```python
mad.send("arr = py:recv()")
mad.send(my_array)
```

#### Pattern B: Python asks MAD-NG for data

```python
mad.send("tbl = twiss {sequence=seq}")
mad.send("py:send(tbl)")
tbl = mad.recv("tbl") # Receives the table as a Python object that is interactive and can be converted to a DataFrame
```

If you keep these two patterns distinct, most send/receive bugs become much easier to reason about.

---

## Supported Data Types

The following types can be sent from Python to MAD-NG:

```{list-table} Supported Send Types
:header-rows: 1

* - Python Type
  - MAD-NG Type
  - Function to Use
* - `None`, `str`, `int`, `float`, `complex`, `bool`, `list`
  - Various
  - {func}`MAD.send`
* - `numpy.ndarray (float64)`
  - `matrix`
  - {func}`MAD.send`
* - `numpy.ndarray (complex128)`
  - `cmatrix`
  - {func}`MAD.send`
* - `numpy.ndarray (int32)`
  - `imatrix`
  - {func}`MAD.send`
* - `range`
  - `irange`
  - {func}`MAD.send`
* - `start, stop, size` as float, int
  - `range`, `logrange`
  - `mad.send_range()`, `mad.send_logrange()`
* - Complex structures (e.g., TPSA, CTPSA)
  - `TPSA`, `CTPSA`
  - `mad.send_tpsa()`, `mad.send_cpx_tpsa()`
```

For full compatibility, see the {mod}`pymadng.MAD` documentation.

```{note}
High-level MAD objects are often returned as references rather than copied Python objects. This is expected behaviour and is part of how PyMAD-NG avoids unnecessary data transfer.
```

---

## Converting TFS Tables to DataFrames

If you use {func}`twiss` or {func}`survey`, MAD-NG returns an `mtable`, which can be converted to a Pandas or TFS-style DataFrame:

```python
mtbl = mad.twiss(...)
df = mtbl.to_df()  # Either DataFrame or TfsDataFrame
```

If the object is not an `mtable`, a `TypeError` will be raised.

```{note}
`tfs-pandas` (if installed) will enhance the output with headers and metadata.
```

See:
```{literalinclude} ../../examples/ex-ps-twiss/ex-ps-twiss.py
:lines: 19, 25, 42-53
:linenos:
```

---

## Avoiding Deadlocks

Deadlocks can occur if Python and MAD-NG wait on each other to send/receive large data without syncing.

### Example of a Deadlock
```python
mad.send('arr = py:recv()')
mad.send(arr0)                 # Large matrix
mad.send('py:send(arr)')       # Sends data to Python
mad.send('arr2 = py:recv()')   # Asks for new data
mad.send(arr2)                 # DEADLOCK if previous data not yet received
```

```{warning}
Always ensure each {func}`MAD.send` has a matching {func}`MAD.recv` if data is expected back.
```

### A Safer Way to Think About It

Before each operation, ask one question:

- "Is MAD-NG waiting for Python?"
- or "Is Python waiting for MAD-NG?"

If both sides are waiting to receive, the session will deadlock.

---

## Scope: Local vs Global

MAD-NG uses Lua-style scoping:

- Variables declared with `local` are temporary.
- Variables without `local` persist across {func}`MAD.send` calls.

### Example:
```python
mad.send("""
a = 10
local b = 20
print(a + b)
""")

mad.send("print(a + (b or 5))")  # b is nil → 10 + 5 = 15
```

```{tip}
Use `local` to avoid polluting the global MAD-NG namespace.
```

### Python Assignment vs MAD Assignment

This is worth stating explicitly because it is a common first-use mistake:

```python
mad["x"] = 5   # writes x inside MAD-NG
mad.x = 5      # writes an attribute on the Python wrapper only
```

If you intend to create a MAD-NG variable, always use square-bracket assignment.

---

## References and Materialising Values

Many objects returned by the high-level interface are references to values living inside MAD-NG.

```python
ref = mad.math.sin(1)
```

To materialise a Python value, if it exists (rather than a reference), use the `eval()` method:

```python
value = ref.eval()
```

To materialise a table:

```python
df = mad.tbl.to_df()
```

This distinction is especially important when inspecting objects interactively, writing assertions in tests, or passing results into ordinary Python libraries.

---

## Executing Python Returned by MAD-NG

{func}`MAD.recv_and_exec` executes Python code sent back from MAD-NG:

```python
mad.send("py:send([[print('hello from MAD')]])")
mad.recv_and_exec()
```

The execution context automatically includes:

- `mad`: the current PyMAD-NG session
- `breakpoint`: the debugger bridge
- `pydbg`: alias for the debugger bridge

That means MAD-NG can request an interactive debugger stop like this:

```python
mad.send("py:send([[breakpoint()]])")
mad.recv_and_exec()
```

---

## Customising the Environment

You can configure the `MAD()` instance with options to better suit your environment:

### Change the Python alias used inside MAD-NG:
```python
mad = MAD(py_name="python")
```

### Specify a custom MAD-NG binary:
```python
mad = MAD(mad_path="/custom/path/to/mad")
```

### Enable debug mode:
```python
mad = MAD(debug=True)
```

### Increase the number of temporary variables:
```python
mad = MAD(num_temp_vars=10)
```

See {meth}`pymadng.MAD.__init__` for all configuration options.

---

```{eval-rst}
.. currentmodule:: pymadng
```

## Summary

- Always match {func}`MAD.send` with {func}`MAD.recv` when data is expected.
- Use `.to_df()` on MAD tables when you want a DataFrame.
- Avoid deadlocks by receiving before sending again.
- Manage scope using `local` wisely.
- Use configuration flags to tailor behaviour.

For more, see the {doc}`advanced_features`, {doc}`debugging`, and {doc}`function_reference` sections.
