```{eval-rst}
.. currentmodule:: pymadng
```

# Advanced Features in PyMAD-NG

This section covers some of the most powerful capabilities in PyMAD-NG. These features allow you to create scalable and complex accelerator workflows by combining the performance of MAD-NG with Python's expressiveness.

```{contents}
:depth: 1
:local:
```

---

## Understanding `_last[]` Temporary Variables

In MAD-NG, when a command returns a value, it is not automatically captured unless explicitly assigned. PyMAD-NG handles this by assigning results to a set of reserved variables: `_last[1]`, `_last[2]`, etc.

These are managed internally by PyMAD-NG using a helper class {class}`madp_last.last_counter`, and accessed in Python via references. This allows expressions like:

```python
result = mad.math.sqrt(2) + mad.math.log(10)
```

Behind the scenes, each intermediate operation is stored in a new `_last[i]` reference, then combined. You can access or evaluate the result using `.eval()`:

```python
print(result.eval())
```

These temporary variables are recycled unless manually stored using:

```python
mad["my_var"] = result
```

This is particularly useful in expressions, multi-step computations, and avoiding naming clutter.

---

## Function and Object References in MAD-NG

In PyMAD-NG, accessing or calling any MAD-NG function or object returns a Python reference to that MAD-NG entity, rather than immediately executing or resolving it. This enables symbolic chaining and precise control over execution.

### Example:
```python
r = mad.math.exp(1)
print(type(r))  # high_level_mad_ref
print(r.eval())  # 2.718...
```

You can delay evaluation until needed, allowing reuse:
```python
mad["result"] = mad.math.log(10) + mad.math.sin(1)
```

This keeps Python responsive and lets MAD-NG do the heavy lifting.

---

## Real-Time Feedback with Python During Matching

MAD-NG supports callbacks and iterative evaluations, which can be tied into Python logic. One common use is during `match` procedures, where you want to receive intermediate updates.

### Example Workflow:
In MAD:
```lua
function twiss_and_send()
  local tbl, flow = twiss {sequence=seq}
  py:send({tbl.s, tbl.beta11})
  return tbl, flow
end
```

In Python:
```python
mad.match(
  command=mad.twiss_and_send,
  variables=[...],
  equalities=[...],
  objective={"fmin": 1e-3},
  maxcall=100
)

while True:
    data = mad.recv()
    if data is None:
        break
    update_plot(data)
```

This is ideal for live visualization, feedback loops, or diagnostics during optimization.

---

## Using PyMAD-NG with Multiprocessing

Because PyMAD-NG communicates with MAD-NG via pipes (not shared memory), you can launch multiple independent MAD processes using `os.fork()` or `multiprocessing`.

### When to Use This:
- Run parallel simulations or parameter scans
- Avoid reloading large sequences repeatedly

### Example:
```python
import os
if os.fork() == 0:
    mad = MAD()
    mad.send("... long running setup ...")
    os._exit(0)
```

Each process maintains its own MAD instance and data pipeline.

---

## Loading and Using External MAD Files and Modules

MAD-X and MAD-NG models often consist of `.seq`, `.mad`, `.madx`, or `.str` files. You can load these via the high-level interface:

```python
mad.MADX.load("'lhc.seq'", "'lhc.mad'")
mad.load("MADX", "lhcb1")
```

Or load additional MAD-NG modules:
```python
mad.load("MAD.gphys", "melmcol")
```

This loads extended libraries for magnet properties, tracking models, or optics algorithms.

---

## Exporting Results for External Use

After running a Twiss or Survey, the results are stored in an `mtable`, which can be exported to a TFS file:

```python
mad.tbl.write("'results.tfs'", mad.quote_strings(["s", "beta11", "mu1"]))
```

You can read this file with `tfs-pandas` or use it as input to another tool.

---

## Combining with NumPy and Pandas

PyMAD-NG integrates cleanly with Python’s data ecosystem:

- Pass `numpy` arrays to MAD-NG using {func}`MAD.send`
- Use {func}`.to_df` on MAD tables to get Pandas DataFrames
- Use `tfs-pandas` for rich metadata support

### Example:
```python
import numpy as np
mad.send("my_array = py:recv()")
mad.send(np.linspace(0, 1, 100))
```

This allows direct use of scientific computation tools in tandem with accelerator modeling.

---

## Managing Larger Workflows

PyMAD-NG supports:
- Loading full files with `mad.loadfile("mysetup.mad")`
- Organising expressions using Python variables
- Retaining command history using:

```python
print(mad.history())
```

For clean resource management, always use context blocks:
```python
with MAD() as mad:
    mad.MADX.load("'lhc.seq'", "'lhc.mad'")
```

This ensures the MAD process is correctly shut down when finished.

---

## Summary of Advanced Features

| Feature                         | Purpose                                          |
|---------------------------------|--------------------------------------------------|
| `_last[]` Variables             | Track intermediate return values symbolically    |
| Reference Objects               | Access MAD-NG objects with delayed evaluation    |
| Matching Feedback               | Monitor intermediate results during match        |
| Multiprocessing                 | Run multiple MAD-NG simulations in parallel      |
| File and Module Loading         | Import sequences, optics files, and Lua modules  |
| Table Export                    | Write TFS files from MAD tables                  |
| NumPy / Pandas Interoperability  | Pass data between Python and MAD-NG seamlessly   |
| Project Structuring             | Use {func}`MAD.loadfile`, {func}`MAD.history`, and `with` block  |

These tools are designed to give you complete control over your simulations while staying fast and maintainable.

Next: head over to **Debugging & Troubleshooting** to diagnose and resolve common issues in real-world workflows.

