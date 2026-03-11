# Quick Start Guide

This guide will walk you through your first experience with **PyMAD-NG**. By the end, you'll know how to run MAD-NG commands from Python, send and receive data, and perform a basic optics calculation.

```{contents}
:depth: 2
:local:
```

---

## Step 1: Create a MAD Instance

Start by importing and creating an instance of the {class}`pymadng.MAD` object:

```python
from pymadng import MAD
mad = MAD()
```

This automatically launches a MAD-NG process and connects it to Python.

```{important}
`MAD()` launches a real MAD-NG subprocess immediately. For normal scripts, prefer `with MAD() as mad:` so the process is always cleaned up.
```

### Mental Model

Four rules explain most PyMAD-NG behaviour:

1. `mad.send("...")` sends code or data into the running MAD-NG process.
2. `mad.recv()` only succeeds after MAD-NG has been told to `py:send(...)` something back.
3. High-level objects like `mad.seq`, `mad.twiss(...)`, or `mad.math.sin(1)` are usually references into MAD-NG, not copied Python values.

---

## Step 2: Load a Sequence

PyMAD-NG supports two approaches: a high-level (pythonic) interface and a low-level (script-driven) interface.

### High-Level API:

```python
mad.MADX.load("'fodo.seq'", "'fodo.mad'")
mad["seq"] = mad.MADX.seq
```

### Low-Level API:

```python
mad.send("MADX:load('fodo.seq', 'fodo.mad')")
mad.send("seq = MADX.seq")
```

---

## Step 3: Set Up a Beam

### High-Level:

```python
mad.seq.beam = mad.beam()
```

### Low-Level:

```python
mad.send("seq.beam = beam {}")
```

---

## Step 3.5: References vs Values

PyMAD-NG keeps most large or structured objects inside MAD-NG and gives Python a reference to them.

```python
tbl_ref = mad.twiss(sequence=mad.seq)
print(type(tbl_ref))
```

That is useful for performance and for symbolic chaining, but it also means you should explicitly ask for concrete Python values when needed:

```python
value = mad.math.sin(1).eval()
df = mad.tbl.to_df()
```

```{note}
If an object feels more like a handle than a Python value, that is usually correct. Use `.eval()` or a conversion method such as `.to_df()` when you want data materialised on the Python side.
```

---

## Step 4: Run a Twiss Calculation

### High-Level:

```python
mad["tbl", "flw"] = mad.twiss(sequence=mad.seq)
```

### Low-Level:

```python
mad.send("tbl, flw = twiss {sequence=seq}")
mad.send("py:send(tbl)")
tbl = mad.recv()
```

---

## Step 4.5: Assigning MAD-NG Variables Correctly

To create or overwrite a variable in MAD-NG, use square brackets:

```python
mad["energy"] = 6500
mad["seq"] = mad.MADX.seq
```

Do not use:

```python
mad.energy = 6500
```

That only changes the Python wrapper object and does not update the running MAD-NG process.

---

## Step 5: Analyse the Results

Convert the resulting MAD table to a Pandas DataFrame:

```python
df = mad.tbl.to_df()
print(df.head())
```

---

## Step 6: Visualise the Optics

Plot the beta function using Matplotlib:

```python
import matplotlib.pyplot as plt
plt.plot(df["s"], df["beta11"])
plt.xlabel("s [m]")
plt.ylabel("Beta Function")
plt.title("Twiss Beta11 vs s")
plt.grid(True)
plt.show()
```

---

## Additional Tips

- If you want to send MAD-NG commands directly:
  ```python
  mad.send("py:send(math.sin(1))")
  print(mad.recv())
  ```

- If MAD-NG is expecting Python data, send it immediately:
  ```python
  mad.send("arr = py:recv()")
  mad.send(my_array)
  ```

- You can enter the MAD debugger from Python:
  ```python
  mad.breakpoint()
  ```

- Quitting the debugger with `q` terminates the current MAD session. After that, create a new `MAD()` instance before continuing.

## What Next?

Now that you’ve completed your first PyMAD-NG workflow, explore:
- **[MAD-NG Documentation](https://madx.web.cern.ch/releases/madng/html/)** for details on MAD-NG features
- **[API Reference](reference.rst)** for full documentation of the {class}`pymadng.MAD` class
- **[Examples](examples.rst)** to see real-world scripts. With all the scripts also in the [`examples` folder of the PyMAD-NG repository](https://github.com/MethodicalAcceleratorDesign/MAD-NG.py/tree/main/examples).
