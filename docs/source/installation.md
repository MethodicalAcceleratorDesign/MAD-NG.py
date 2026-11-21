# Installation

## Requirements

- Python 3.11 or later
- Linux or macOS (the package bundles a MAD-NG binary for each)
- `numpy` (installed automatically)
- Optional: `tfs-pandas` (the `tfs` extra) for DataFrames with TFS headers, and `matplotlib` for plots

## Install

```bash
pip install pymadng
pip install pymadng[tfs]   # with tfs-pandas
```

Check the installation:

```python
import pymadng
print(pymadng.__version__)
```

Update with `pip install --upgrade pymadng` and remove with `pip uninstall pymadng`.

## Use a different MAD-NG binary

```python
from pymadng import MAD

mad = MAD(mad_path="/path/to/mad")
```

## Next

{doc}`quickstart` runs a first twiss calculation. To install the tools for working on PyMAD-NG itself, see {doc}`contributing`.
