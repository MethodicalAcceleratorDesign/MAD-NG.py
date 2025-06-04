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
  - `mad.send_rng()`, `mad.send_lrng()`
* - Complex structures (e.g., TPSA, CTPSA)
  - `TPSA`, `CTPSA`
  - `mad.send_tpsa()`, `mad.send_ctpsa()`
```

For full compatibility, see the {mod}`pymadng.MAD` documentation.

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
- Use `mad.to_df()` for table conversion.
- Avoid deadlocks by receiving before sending again.
- Manage scope using `local` wisely.
- Use configuration flags to tailor behavior.

For more, see the {doc}`advanced_features`, {doc}`debugging`, and {doc}`function_reference` sections.

