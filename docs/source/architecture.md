```{eval-rst}
.. currentmodule:: pymadng
```

# PyMAD-NG Architecture Overview

This section explains the internal architecture of PyMAD-NG, outlining how Python interacts with MAD-NG. 

```{note}
Understanding the architecture will help advanced users contribute to development, extend functionality, and debug issues more effectively.
```

```{contents}
:depth: 2
:local:
```

---

## High-Level Overview

PyMAD-NG is a **Python wrapper for MAD-NG**, using standard UNIX pipes to manage two-way communication between Python and the MAD-NG subprocess. It provides both:

- A **low-level string-based API** (like scripting MAD-NG manually)
- A **high-level object-based API** that emulates Pythonic behavior

At the heart of PyMAD-NG is the {class}`MAD` class, which:

- Spawns the MAD-NG binary as a subprocess
- Manages sending commands and receiving data
- Handles variable binding, temporary variables, and object references

---

## Communication Pipeline

The communication between Python and MAD-NG follows this pipeline:

```
+-----------+        send()        +---------+
|  Python   | -------------------> | MAD-NG  |
|  Script   | <------------------- | Process |
+-----------+        recv()        +---------+
```

This is implemented using `os.pipe()` and `select.select()` to manage reads and writes asynchronously.

### Communication Protocol

- Commands are sent as strings to MAD-NG (e.g., `mad.send("a = 1 + 2")`)
- Responses are requested explicitly via `{func}`MAD.recv`
- Data can be sent and received in binary or string formats, depending on the type

---

## Core Components

### {class}`MAD` Class ({class}`madp_object`)

- Main interface for users
- Automatically loads common MAD-NG modules (e.g. `twiss`, `element`, `sequence`)
- Handles naming of Python process in MAD-NG via `py_name`
- Configures subprocess behavior (debug mode, stdout redirection)

### {class}`madp_pymad.mad_process`

- Manages low-level pipe setup and subprocess launch
- Provides `send`, `recv`, and `close` methods
- Serialises and deserialises Python <-> MAD data

### {class}`madp_classes`

- Wraps MAD-NG references returned to Python
- Allows chained method calls like `mad.math.sin(1)`
- Supports `.eval()` to convert a MAD value into a native Python object
- Implements `__getattr__`, `__getitem__`, `__call__` to emulate Lua table behavior

### {class}`madp_last`

- Implements `_last[]` variable management for symbolic return values
- Ensures unique temporary variable usage
- Used in constructing expression chains

### {class}`madp_strings`

- Contains helpers for quoting strings for MAD-NG consumption
- Supports quote-conversion for use in file writing and table exporting

---

## Data Types and Serialization

PyMAD-NG supports a wide range of Python-native and NumPy types, which are automatically serialised and mapped to MAD-NG equivalents.

| Python Type           | MAD-NG Type     | Transport Format  |
| --------------------- | --------------- | ----------------- |
| `int`, `float`, `str` | number, string  | text or binary    |
| `bool`                | bool            | text              |
| `complex`             | complex         | binary            |
| `list`                | table           | serialised list   |
| `numpy.ndarray`       | matrix, cmatrix | binary            |
| `range`, `np.geomspace`     | range types     | encoded structure |

Conversion is handled by {func}`MAD.send` and `{func}`MAD.recv`, both methods on the {class}`MAD` class.

---

## Dynamic Attributes & Autocompletion

Because MAD-NG entities are only known at runtime, PyMAD-NG uses dynamic attribute access via `__getattr__`. This means:

- Tab completion (`dir(mad)`) only works for preloaded or cached attributes
- Use {func}`MAD.globals()` to list current MAD-NG global variables
- {class}`madp_classes.high_level_mad_ref` objects will not show introspectable properties until evaluated

---

## Protected Execution

All sends are "protected" by default:

- If MAD-NG returns an error, PyMAD-NG raises a Python `RuntimeError`
- The return type `err_` is automatically detected and escalated
- This avoids crashes and lets users handle exceptions gracefully

---

## Summary

| Component                                      | Role                                                       |
| ---------------------------------------------- | ---------------------------------------------------------- |
| {class}`MAD` class                      | Main interface and environment for interacting with MAD-NG |
| {class}`madp_pymad.mad_process`         | Launches and communicates with MAD-NG subprocess           |
| {class}`madp_classes.high_level_mad_ref` | Wraps MAD objects for Pythonic access                      |
| {class}`madp_last`                       | Tracks temporary intermediate results from MAD-NG          |
| Type dispatch                                  | Maps Python objects to MAD-NG-compatible messages          |

This modular, pipe-based architecture ensures PyMAD-NG remains flexible, efficient, and closely integrated with MAD-NG’s scripting model.