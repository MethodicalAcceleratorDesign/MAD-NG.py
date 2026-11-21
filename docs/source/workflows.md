```{eval-rst}
.. currentmodule:: pymadng
```

# Workflows

## Live feedback during a match

A MAD-NG function can send data to Python while `match` runs, so Python can plot each step. In MAD-NG:

```lua
function twiss_and_send()
  local tbl, flow = twiss {sequence=seq}
  py:send({tbl.s, tbl.beta11})
  return tbl, flow
end
```

In Python, start the match and receive until MAD-NG sends `None`:

```python
mad.match(
    command=mad.twiss_and_send,
    variables=[...],
    equalities=[...],
    objective={"fmin": 1e-3},
    maxcall=100,
)

while (data := mad.recv()) is not None:
    update_plot(data)
```

`examples/ex-lhc-couplingLocal` is a full example ({doc}`ex-lhc-couplingLocal`).

## Several MAD-NG processes

Each `MAD()` is its own process with its own pipes, so a `MAD` per worker runs scans in parallel. Create the `MAD` inside the worker, after the fork:

```python
import os

if os.fork() == 0:
    with MAD() as mad:
        ...
    os._exit(0)
```

`examples/ex-benchmark-and-fork` is a complete script.

## Write a table to a TFS file

```python
mad.tbl.write("'results.tfs'", mad.quote_strings(["s", "beta11", "mu1"]))
```

`tfs-pandas` reads the file back.

## NumPy arrays

```python
import numpy as np

mad.send("my_array = py:recv()")
mad.send(np.linspace(0, 1, 100))
```

The types that can be sent are listed in {doc}`communication`.
