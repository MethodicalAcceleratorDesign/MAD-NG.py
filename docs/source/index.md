# PyMAD-NG

PyMAD-NG drives [MAD-NG](https://madx.web.cern.ch/releases/madng/html/) (Methodical Accelerator Design - Next Generation) from Python. It starts a MAD-NG process, sends it commands and data through pipes, and returns the results as Python values, NumPy arrays and Pandas DataFrames.

```python
from pymadng import MAD

with MAD() as mad:
    mad.MADX.load("'lhc_as-built.seq'", "'lhc_as-built.mad'")
    mad["tbl", "flw"] = mad.twiss(sequence=mad.MADX.lhcb1)
    df = mad.tbl.to_df()
    print(df[["name", "s", "beta11"]].head())
```

- **Two APIs**: Python calls such as `mad.twiss(...)`, or MAD-NG code sent as strings with `mad.send(...)`.
- **Tables as DataFrames**: `mad.tbl.to_df()` gives a `pandas.DataFrame`, or a `TfsDataFrame` when `tfs-pandas` is installed.
- **MAD-X sequences**: `MADX:load` reads MAD-X files into MAD-NG.
- **Jupyter**: MAD-NG output appears in the notebook cell ({doc}`jupyter`).

```{toctree}
:maxdepth: 2
:caption: Start

installation
quickstart
```

```{toctree}
:maxdepth: 2
:caption: Concepts

communication
references
architecture
```

```{toctree}
:maxdepth: 2
:caption: How-to

load-and-import
jupyter
workflows
troubleshooting
```

```{toctree}
:maxdepth: 2
:caption: Examples

ex-lhc-couplingLocal
examples
```

```{toctree}
:maxdepth: 2
:caption: Reference

function_reference
reference
developer
```

```{toctree}
:maxdepth: 2
:caption: Project

contributing
```

Next: {doc}`installation`, then {doc}`quickstart` (about 10 minutes).
