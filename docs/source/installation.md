# Installation & Setup

```{contents}
:depth: 2
:local:
```

## System Requirements
Before installing PyMAD-NG, ensure that your system meets the following requirements:

- **Python**: Version 3.7 or later
- **Operating System**: Linux, macOS, or Windows
- **Dependencies**:
  - `numpy`
  - `pandas` (optional, for data handling)
  - `matplotlib` (optional, for visualization)

---

## Installing PyMAD-NG

PyMAD-NG is available on PyPI and can be installed using `pip`:

```bash
pip install pymadng
```

If you need to install optional dependencies for advanced features:

```bash
pip install pymadng[tfs]
```

This installs `tfs-pandas` for handling MAD-NG TFS tables.

### Verifying Installation

To check if PyMAD-NG is installed correctly, open Python and run:

```python
import pymadng
print(pymadng.__version__)
```

If this prints a version number, the installation was successful.

---

## Updating PyMAD-NG

To update PyMAD-NG to the latest version:

```bash
pip install --upgrade pymadng
```

You can check your current version using:

```bash
pip show pymadng
```

---

## Uninstalling PyMAD-NG

If you need to remove PyMAD-NG from your system:

```bash
pip uninstall pymadng
```

---

## Using a Custom MAD-NG Executable

If you have a specific MAD-NG binary, you can specify its path:

```python
from pymadng import MAD
mad = MAD(mad_path="/path/to/mad")
```
## Understanding {class}`pymadng.MAD` Object Initialization

When you create a {class}`pymadng.MAD` object, an instance of MAD-NG is launched. The `__init__` method in `mad_object.py` handles the following:

- **Process Creation**: Starts MAD-NG and establishes a communication channel.
- **Module Imports**: By default, imports essential MAD-NG modules, see [Useful Modules](function_reference.md) for the complete list.
- **Environment Configuration**: Sets up the Python-MAD environment, including handling `py_name` and error handling.
- **Temporary Variable Management**: Uses `last_counter` to track temporary variables (`_last[]`) for improved performance.

This ensures that users can quickly interface with MAD-NG without extensive manual setup.

---

## Debugging Tips

Debugging PyMAD-NG can involve both Python-side and MAD-NG-side issues. Below are some strategies and tools built into PyMAD-NG to help troubleshoot effectively:

### 1. Enable Debug Mode

You can enable verbose output during initialization by setting `debug=True`. This enables MAD-NG's debug mode and prints useful messages:

```python
mad = MAD(debug=True)
```

### 2. Redirect Standard Output and Standard Error

You can log all MAD-NG output to a file:

```python
mad = MAD(stdout="mad_debug.log")
```

This is useful for reviewing MAD-NG output, especially when running large scripts.

If you want to redirect the standard error to a different file (as by default it is redirected to the standard output file), you can use the `stderr` parameter:

```python
mad = MAD(stdout="mad_debug.log", stderr="mad_error.log")
```

### 3. Catch Errors from MAD-NG

Internally, MAD-NG returns an `err_` token to signal an error. PyMAD-NG raises a `RuntimeError` with a message when this happens. If you encounter unexpected crashes, wrap your calls in try/except:

```python
try:
    mad.send("a = 1/'0'").recv()
except RuntimeError as e:
    print("MAD-NG Error:", e)
```

Or it is possible to ignore the error and continue execution of the python script:

```python
mad = MAD(raise_on_error=False)
mad.send("a = 1/'0'")
assert mad.send("py:send(1)").recv() == 1
``` 

### 4. View Communication History

You can inspect the full history of MAD-NG commands sent from Python, *only if **debug mode** is enabled*:

```python
print(mad.history())
```

### 5. Interactive Execution

Use `mad.recv_and_exec()` to execute MAD-NG commands returned as Python strings. This is helpful when MAD sends back executable code:

```python
mad.send("py:send('print(\'debug line\')')")
mad.recv_and_exec()
```

### 6. Ensure Communication Order

MAD-NG uses FIFO communication. Always follow the rule:

- **Before calling `recv()`**, ensure MAD was told to `send()` something.
- **Before calling `send(data)`**, ensure MAD expects to `recv()` something.

Failing to follow this can cause deadlocks or hangs.

---

## Next Steps

Now that PyMAD-NG is installed, you can move on to:

- **[Quick Start Guide →](quickstartguide.md)** *(Learn the basics and run your first PyMAD-NG script)*  
- **[API Reference →](reference.rst)** *(Explore the functions and classes available in PyMAD-NG)*

