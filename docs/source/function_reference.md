```{eval-rst}
.. currentmodule:: pymadng
```

# Useful Functions & Objects in PyMAD-NG

This page provides a reference-style overview of functions, libraries, and patterns available through a {class}`MAD()` instance. It complements the API reference by highlighting common tools and objects exposed in the high-level interface for scripting and interacting with MAD-NG.

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
| `match`     | Launch matching optimisations                           |
| `twiss`     | Compute Twiss parameters                                |
| `survey`    | Calculate survey tables and coordinates                 |
| `mtable`    | Handle MAD-NG table output                              |

These are accessible as attributes of the {class}`MAD` instance:

```python
mad["seq"] = mad.sequence(...)       # Create a sequence
mad.seq.beam = mad.beam(...)         # Attach a beam to the sequence
mad["tbl", "flw"] = mad.twiss(sequence=mad.seq)  # Run a Twiss
```
See {doc}`references` for how to set variables in MAD-NG.

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

For modules, files and `load`, see {doc}`load-and-import`; for references, assigning variables and tables, see {doc}`references` and {doc}`communication`.

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
