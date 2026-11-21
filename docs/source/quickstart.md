# Quick start

This page runs a twiss calculation on a FODO cell and plots the beta function (about 10 minutes). The `python` blocks run in order in a folder that holds [`fodo.seq`](https://github.com/MethodicalAcceleratorDesign/MAD-NG.py/blob/main/examples/ex-jupyter/fodo.seq), and CI runs them. Blocks marked as alternatives or as mistakes are not run.

## 1. Start MAD-NG

```python
from pymadng import MAD

mad = MAD()
```

`MAD()` starts a MAD-NG process. In scripts, `with MAD() as mad:` ends the process when the block ends.

Four rules explain most of the behaviour:

1. {meth}`mad.send("...") <pymadng.MAD.send>` sends code or data into the running MAD-NG process.
2. {meth}`mad.recv() <pymadng.MAD.recv>` only succeeds after MAD-NG has been told to `py:send(...)` something back ({doc}`communication`).
3. Objects such as `mad.seq`, `mad.twiss(...)` or `mad.math.sin(1)` are usually references into MAD-NG, not copies ({doc}`references`).
4. `mad["x"] = 5` sets a variable in MAD-NG; `mad.x = 5` only sets an attribute of the Python object.

## 2. Load a sequence

```python
mad.MADX.load("'fodo.seq'", "'fodo.mad'")
mad["seq"] = mad.MADX.seq
```

The same in MAD-NG code:

```{code-block} python
mad.send("MADX:load('fodo.seq', 'fodo.mad')")
mad.send("seq = MADX.seq")
```

## 3. Set up a beam

```python
mad.seq.beam = mad.beam()
```

```{code-block} python
mad.send("seq.beam = beam {}")
```

## 4. Run twiss

```python
mad["tbl", "flw"] = mad.twiss(sequence=mad.seq)
```

```{code-block} python
mad.send("tbl, flw = twiss {sequence=seq}")
mad.send("py:send(tbl)")
tbl = mad.recv("tbl")
```

## 5. References and values

Large or structured objects stay inside MAD-NG and Python holds a reference to them:

```python
ref = mad.twiss(sequence=mad.seq)
print(type(ref))
```

Ask for a Python value with `.eval()` or a conversion such as `.to_df()`:

```python
value = mad.math.sin(1).eval()
df = mad.tbl.to_df()
print(df.head())
```

## 6. Set variables

Use square brackets to create or overwrite a variable in MAD-NG:

```python
mad["energy"] = 6500
```

```{code-block} python
mad.energy = 6500   # changes the Python object only; MAD-NG does not see it
```

## 7. Plot the beta function

```python
import matplotlib.pyplot as plt

plt.plot(df["s"], df["beta11"])
plt.xlabel("s [m]")
plt.ylabel("Beta function [m]")
plt.title("Twiss beta11 vs s")
plt.grid(True)
plt.show()
```

## Next

- {doc}`communication`: the send/receive rules and the data types.
- {doc}`references`: references and values, and assigning variables.
- {doc}`examples`: complete scripts, also in the [`examples` folder](https://github.com/MethodicalAcceleratorDesign/MAD-NG.py/tree/main/examples) of the repository.
- The [MAD-NG manual](https://madx.web.cern.ch/releases/madng/html/) for the MAD-NG commands.
