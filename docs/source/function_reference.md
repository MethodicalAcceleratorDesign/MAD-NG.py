```{eval-rst}
.. currentmodule:: pymadng
```

# Useful Functions & Objects in PyMAD-NG

This page provides a reference-style overview of functions, libraries, and patterns available through a {class}`MAD()` instance. It complements the API reference by highlighting common tools and objects exposed in the high-level interface for scripting and interacting with MAD-NG.

```{contents}
:depth: 2
:local:
```

---

## Top-Level Objects in `pymadng`

When you create a {class}`MAD()` instance, PyMAD-NG exposes many MAD-NG global libraries and functions directly as attributes of the object.

### Example:
```python
from pymadng import MAD
mad = MAD()
print(mad.math.sin(1).eval())
```

These objects mirror MAD-NG’s Lua-style modules and can be accessed directly via `mad.<name>`.

---

## Global Utility Modules

| Name       | Description                                      |
|------------|--------------------------------------------------|
| `math`     | Basic math functions: `sin`, `cos`, `sqrt`, etc. |
| `os`       | Operating system functions (limited)             |
| `io`       | Input/output and file manipulation               |
| `table`    | Table and list utilities                         |
| `string`   | String manipulation                              |
| `MAD`      | Core MAD-NG functions and module loader          |
| `MADX`     | Legacy-style MAD-X environment adapter           |

All returned values are *references* until explicitly evaluated with `.eval()`.

---

## Global Functions from Lua
These functions are available globally in the MAD-NG environment:

| Name        | Description                                      |
|-------------|--------------------------------------------------|
| `assert`    | Assert a condition (throws error if false)       |
| `print`     | Print to the console                             |
| `error`     | Throw an error                                   |
| `ipairs`    | Iterate over indexed part of a table             |
| `pairs`     | Iterate over all parts of a table                |
| `tonumber`  | Convert a string to a number                     |
| `tostring`  | Convert a number to a string                     |
| `type`      | Get the type of a variable                       |
| `load`      | Load a Lua chunk (string)                        |
| `loadfile`  | Load a Lua file                                  |
| `require`   | Load a Lua module                                |
---

## MAD Physics Libraries

These libraries expose MAD-NG’s physics simulation functionality, and are made available automatically by PyMAD-NG when you initialise {class}`MAD`.

| Name        | Purpose                                                 |
|-------------|---------------------------------------------------------|
| `beam`      | Define beam particle and energy                         |
| `beta0`     | Create Beta0 optics state                               |
| `element`   | Create MAD-NG elements (e.g. quadrupoles, dipoles)      |
| `sequence`  | Build beamline sequences                                |
| `object`    | General MAD-NG object interface                         |
| `track`     | Perform particle tracking                               |
| `match`     | Launch matching optimizations                           |
| `twiss`     | Compute Twiss parameters                                |
| `survey`    | Calculate survey tables and coordinates                 |
| `mtable`    | Handle MAD-NG table output                              |

These are accessible as attributes of the {class}`MAD` instance:

```python
mad["seq"] = mad.sequence(...)       # Create a sequence
mad.seq.beam = mad.beam(...)         # Attach a beam to the sequence
mad["tbl", "flw"] = mad.twiss(sequence=mad.seq)  # Run a Twiss
```
See [Setting Variables in MAD-NG](#setting-variables-in-mad-ng) for more details on how to set variables in MAD-NG and explanation of the code above.

---

## Importing MAD-NG Modules via PyMAD-NG

You can load MAD-NG modules dynamically using the {func}`MAD.load` function.
This is useful for loading built-in modules that are not automatically available.

### Example:

You can load modules directly from MAD-NG namespaces:

```python
mad.load("MAD", "gphys")        # Load a module such as MAD.gphys
mad.load("element", "quadrupole")  # Load a specific element type
```

The first argument is the module path. Optional additional arguments allow importing specific submodules or functions.

---


## Core Communication Methods

| Method               | Description                                      |
|----------------------|--------------------------------------------------|
| {func}`MAD.send`         | Send Python data or MAD-NG code to MAD-NG       |
| {func}`MAD.recv`         | Receive results or values from MAD-NG           |
| {func}`MAD.eval`         | Evaluate an expression and return the result    |
| {func}`MAD.recv_and_exec`| Execute Python code sent from MAD-NG            |

These tools are essential for controlling the MAD subprocess directly.

---

## Reference Objects and Evaluation

(setting-variables-in-mad-ng)=
### Setting Variables in MAD-NG

To assign values in MAD-NG, always use square bracket syntax on the {class}`MAD` object. Dot syntax does not trigger assignment inside MAD-NG.

```python
mad["energy"] = 6500                 # Sets a global MAD-NG variable
mad["tw"] = mad.twiss(...)           # Stores the result in MAD-NG
```

Using `mad.energy = 6500` only affects Python, not MAD-NG, and will not produce the expected behavior.


Functions like `mad.math.sin()` return reference objects that defer computation.
You must call `.eval()` to obtain the actual value.

```python
r = mad.math.sin(1)
print(r.eval())  # returns float result
```

References can be composed symbolically:
```python
expr = mad.math.sin(1) + mad.math.cos(1)
print(expr.eval())
```

---

## Table Conversion

MAD tables returned from `twiss()`, `survey()`, etc., can be converted into Pandas-style data frames:

```python
df = mad.tbl.to_df()
```

- If `tfs-pandas` is installed, a `TfsDataFrame` is returned (with headers).
- Otherwise, a regular `pandas.DataFrame` is returned, with the headers in the attrs.

Raises `TypeError` if called on a non-table object.

---


## Listing Available Globals

PyMAD-NG provides functions to explore the MAD-NG runtime environment:

### `mad.globals()`
Returns all top-level variable names currently defined in the MAD-NG session.

### `dir(mad)`
Returns cached or known Python-accessible attributes.

---

## Quoting Strings

### `mad.quote_strings(list_of_str)`
Converts a Python list of strings to a MAD-NG-compatible quoted list.

#### Example:
```python
columns = ["s", "beta11", "mu1"]
mad.tbl.write("'output.tfs'", mad.quote_strings(columns))
```

---

## Summary

PyMAD-NG makes many MAD-NG modules and tools accessible from Python in an intuitive way. This reference highlights the most useful global objects, simulation modules, utility functions, and internal submodules available for scripting or extension work.

For additional control or automation, refer to the API reference or the examples directory.