# Contributing and Extending PyMAD-NG

This guide is for developers who want to contribute to PyMAD-NG or extend its capabilities. It outlines the structure of the codebase, how to develop new features, and best practices for writing and testing code.

---

## Overview of Repository Structure

| File / Module                        | Purpose                                                |
|--------------------------------------|--------------------------------------------------------|
| `src/pymadng/madp_object.py`         | Contains the main {class}`pymadng.MAD` class and high-level interface |
| `src/pymadng/madp_pymad.py`          | Manages subprocess communication and type handling     |
| `src/pymadng/madp_classes.py`        | Defines reference object wrappers (`MadRef`, etc.)    |
| `src/pymadng/madp_last.py`           | Manages temporary variables like `_last[]`             |
| `src/pymadng/madp_strings.py`        | Utility for quoting and formatting MAD-compatible text |
| `examples/`                          | Contains working scripts and tutorials                 |
| `tests/`                             | Contains unit tests for the codebase                   |
| `docs/`                              | Documentation files                                   |

---

## Getting Started

### Prerequisites
- Python 3.11+
- `uv` for dependency and environment management
- A valid MAD-NG executable (either system or bundled)

### Set Up a Development Environment
Clone the repository, create the project environment with `uv`, and install the development tooling defined by the project extras.

```bash
git clone https://github.com/<your-org>/MAD-NG.py.git
cd MAD-NG.py
uv sync --extra dev --extra test --extra tfs
```

That command creates the local `.venv` and installs:
- the package itself in editable mode
- test dependencies such as `pytest` and `pytest-cov`
- development tools such as `pre-commit` and `ruff`
- optional `tfs-pandas` support used by some tests and examples

If you only need the core development tools, you can omit extras you do not need:

```bash
uv sync --extra dev --extra test
```

---

## Development Workflow

1. **Create a Branch**
```bash
git checkout -b your-feature-name
```

2. **Write Code**

3. **Run the Test Suite**
```bash
uv run pytest tests
```

4. **Run Coverage Locally**
```bash
uv run pytest tests --cov=src/pymadng --cov-report=term-missing
```

Coverage is configured in `pyproject.toml` to report on `src/pymadng` rather than the test files themselves.

5. **Run the linters**
```bash
uv run ruff check .
uv run ruff format .
```

6. **Enable and Run Pre-commit Hooks**
Install the hooks once per clone:

```bash
uv run pre-commit install
```

Run all configured hooks manually:

```bash
uv run pre-commit run --all-files
```

The repository currently uses:
- `ruff-check` for linting
- `ruff-format` for formatting
- `cspell` for spell-checking with British English (`en-GB`) configuration

Spell-check configuration lives in `cspell.config.yaml`.

7. **Submit a Pull Request**
   - Include a clear description of the change
   - Reference any related issues

---

## Best Practices

### Code Style
- Use descriptive names for everything
- Keep high-level user APIs separate from internal helpers
- Use Ruff for linting and formatting.
- Prefer public API tests over mock-heavy tests when verifying subprocess behaviour.
- Update documentation whenever user-visible behaviour changes.

### CI Expectations
- GitHub Actions uses `uv` to create the environment and run the test suite.
- Coverage is uploaded from the main Linux / Python 3.11 test job.
- Keep local commands aligned with CI when debugging failures.

---

## Documentation

- Update or extend `.md` or `.rst` files as appropriate
- Document new examples in the `examples/` directory
- Ensure all new features are at least in the API reference

---

## Questions or Issues?

- Open a GitHub Issue
- Tag maintainers in your Pull Request
- See the [Debugging Guide](debugging.md) or [Architecture Overview](architecture.md) for internals

Thanks for contributing to PyMAD-NG!
