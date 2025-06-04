# Contributing and Extending PyMAD-NG

This guide is for developers who want to contribute to PyMAD-NG or extend its capabilities. It outlines the structure of the codebase, how to develop new features, and best practices for writing and testing code.

---

## Overview of Repository Structure

| File / Module                        | Purpose                                                |
|--------------------------------------|--------------------------------------------------------|
| `src/pymadng/madp_object.py`         | Contains the main {class}`pymadng.MAD` class and high-level interface |
| `src/pymadng/madp_pymad.py`          | Manages subprocess communication and type handling     |
| `src/pymadng/madp_classes.py`        | Defines reference object wrappers (`mad_ref`, etc.)    |
| `src/pymadng/madp_last.py`           | Manages temporary variables like `_last[]`             |
| `src/pymadng/madp_strings.py`        | Utility for quoting and formatting MAD-compatible text |
| `examples/`                          | Contains working scripts and tutorials                 |
| `tests/`                             | Contains unit tests for the codebase                   |
| `docs/`                              | Documentation files                                   |

---

## Getting Started

### Prerequisites
- Python 3.7+
- `numpy`, `pandas`, and optionally `tfs-pandas`
- A valid MAD-NG executable (either system or bundled)

### Install PyMAD-NG in Editable Mode
To contribute to PyMAD-NG, clone the repository and install it in editable mode. This allows you to make changes and test them without reinstalling.
In specific cases, you may be allowed write access to the MAD-NG.py repository. If so, you only need to clone the repository and install it in editable mode.

```bash
git clone https://github.com/<your-org>/MAD-NG.py.git
cd pymadng
pip install -e .
```

---

## Development Workflow

1. **Create a Branch**
```bash
git checkout -b your-feature-name
```

2. **Write Code**

3. **Test Code**
   - All tests are located in the `tests/` directory, currently `unittests` are used.

4. **Run Tests** 
```bash
python -m unittest tests/*.py
```

5. **Submit a Pull Request**
   - Include a clear description of the change
   - Reference any related issues

---

## Best Practices

### Code Style
- Use descriptive names for everything
- Keep high-level user APIs separate from internal helpers
- Use Ruff for code and import formatting.

---

## Documentation

- Update or extend `.md` or `.rst` files as appropriate
- Document new examples in the `examples/` directory
- Ensure all new features are at least in the API reference

---

## Questions or Issues?

- Open a GitHub Issue
- Tag maintainers in your Pull Request
- See the [Debugging Guide] or [Architecture Overview] for internals

Thanks for contributing to PyMAD-NG!

