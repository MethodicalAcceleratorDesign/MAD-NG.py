# PyMAD-NG

**Python interface to MAD-NG running as a subprocess**

[![PyPI version](https://img.shields.io/pypi/v/pymadng.svg)](https://pypi.org/project/pymadng/)
[![Documentation Status](https://readthedocs.org/projects/pymadng/badge/?version=latest)](https://pymadng.readthedocs.io/en/latest/)
[![License](https://img.shields.io/github/license/MethodicalAcceleratorDesign/MAD-NG.py)](https://github.com/MethodicalAcceleratorDesign/MAD-NG.py/blob/main/LICENSE)

---

## 🚀 Installation

Install via pip from [PyPI](https://pypi.org/project/pymadng/):

```bash
pip install pymadng
```

---

## 🧠 Getting Started

Before diving into PyMAD-NG, we recommend you:

1. Familiarise yourself with [MAD-NG](https://madx.web.cern.ch/releases/madng/html/) — understanding MAD-NG is essential.
2. Read the [Quick Start Guide](https://pymadng.readthedocs.io/en/latest/quickstartguide.html) to see how to control MAD-NG from Python.

### Explore Key Examples

- **[LHC Matching Example](https://pymadng.readthedocs.io/en/latest/ex-lhc-couplingLocal.html)** – Real-world optics matching with intermediate feedback.
- **[Examples Page](https://pymadng.readthedocs.io/en/latest/examples.html)** - List of examples in an easy to read format. 
- **[GitHub Examples Directory](https://github.com/MethodicalAcceleratorDesign/MAD-NG.py/blob/main/examples/)** – List of avaliable examples on the repository

If anything seems unclear:
- Refer to the [API Reference](https://pymadng.readthedocs.io/en/latest/pymadng.html#module-pymadng)
- Check the [MAD-NG Docs](https://madx.web.cern.ch/releases/madng/html/)
- Or open an [issue](https://github.com/MethodicalAcceleratorDesign/MAD-NG.py/issues)

---

## 📚 Documentation

Full documentation and example breakdowns are hosted at:
[https://pymadng.readthedocs.io/en/latest/](https://pymadng.readthedocs.io/en/latest/)

To build locally:

```bash
git clone https://github.com/MethodicalAcceleratorDesign/MAD-NG.py.git
cd MAD-NG.py/docs
make html
```

---

## 🧪 Running Examples

Examples are stored in the `examples/` folder.
Run any script with:

```bash
python3 examples/ex-fodos.py
```

You can also batch-run everything using:

```bash
python3 runall.py
```

---

## 💡 Features

- High-level Python interface to MAD-NG
- Access to MAD-NG functions, sequences, optics, and tracking
- Dynamic `send()` and `recv()` communication
- Python-native handling of MAD tables and expressions
- Optional integration with `pandas` and `tfs-pandas`

---

## 🤝 Contributing

We welcome contributions! See [`CONTRIBUTING.md`](docs/source/contributing.md) or the [Contributing Guide](https://pymadng.readthedocs.io/en/latest/contributing.html) in the docs.

Bug reports, feature requests, and pull requests are encouraged.

---

## 📜 License

PyMAD-NG is licensed under the [GNU General Public License v3.0](https://github.com/MethodicalAcceleratorDesign/MAD-NG.py/blob/main/LICENSE).

---

## 🙌 Acknowledgements

Built on top of MAD-NG, developed at CERN. This interface aims to bring MAD's power to the Python ecosystem with minimal friction.
