# PyMAD-NG

PyMAD-NG runs [MAD-NG](https://madx.web.cern.ch/releases/madng/html/) (Methodical Accelerator Design - Next Generation) as a subprocess and controls it from Python. MAD-NG does all the computation. PyMAD-NG sends it code and data through pipes and brings back the results you ask for.

```python
from pymadng import MAD

with MAD() as mad:
    mad.MADX.load("'lhc_as-built.seq'", "'lhc_as-built.mad'")
    mad["tbl", "flw"] = mad.twiss(sequence=mad.MADX.lhcb1)
    df = mad.tbl.to_df()
    print(df[["name", "s", "beta11"]].head())
```

- **MAD-NG does the work**: you need to know MAD-NG; its [manual](https://madx.web.cern.ch/releases/madng/html/) describes every function used here.
- **Communication is explicit**: MAD-NG returns data only when told to send it, so each {meth}`mad.send(...) <pymadng.MAD.send>` that expects an answer needs a matching {meth}`mad.recv() <pymadng.MAD.recv>` ({doc}`communication`).
- **Results stay in MAD-NG**: many results are references to MAD-NG objects. Use `.eval()` or `.to_df()` to get Python values ({doc}`references`).
- **Python calls are shortcuts**: `mad.twiss(...)` runs the MAD-NG function of the same name, and {meth}`mad.send(...) <pymadng.MAD.send>` runs any MAD-NG code you write.

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
ai-agents
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
