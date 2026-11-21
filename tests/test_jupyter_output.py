import shutil
from pathlib import Path

import pytest

nbformat = pytest.importorskip("nbformat")
nbclient = pytest.importorskip("nbclient")
pytest.importorskip("ipykernel")

# ipykernel's fd reader thread sends output after the cell is idle if it lags; nbclient drops it
DRAIN = "import time; time.sleep(0.5)"
CELLS = [
    "from pymadng import MAD\nmad = MAD()",
    f"mad.send(\"print('stdout line from MAD-NG')\")\nmad.send('py:send(1)'); mad.recv()\n{DRAIN}",
    f"mad.send(\"io.stderr:write('stderr line from MAD-NG\\\\n')\")\nmad.send('py:send(2)'); mad.recv()\n{DRAIN}",
]


def run_notebook(nb, monkeypatch, path=None):
    monkeypatch.delenv("PYTEST_CURRENT_TEST")  # ipykernel does not capture fds when it is set
    resources = {"metadata": {"path": str(path)}} if path else {}
    nbclient.NotebookClient(nb, timeout=120, kernel_name="python3", resources=resources).execute()
    return nb


def run_cells(cells, monkeypatch):
    return run_notebook(
        nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell(c) for c in cells]), monkeypatch
    )


def test_mad_output_is_captured_by_the_kernel(monkeypatch):
    """ipykernel captures fd 1 and 2 into the running cell; MAD-NG must write to those fds."""
    nb = run_cells(CELLS, monkeypatch)

    streams = {
        (out.name, out.text)
        for cell in nb.cells
        for out in cell.outputs
        if out.output_type == "stream"
    }
    assert ("stdout", "stdout line from MAD-NG\n") in streams
    assert ("stderr", "stderr line from MAD-NG\n") in streams


# Tab completion with jedi evaluates MAD-NG references, which blocks while MAD-NG is busy
JEDI_CELL = "from pymadng import MAD\nmad = MAD({args})\nprint(get_ipython().Completer.use_jedi)"


def test_jedi_is_disabled(monkeypatch):
    nb = run_cells([JEDI_CELL.format(args="")], monkeypatch)
    assert nb.cells[0].outputs[0].text == "False\n"


def test_jedi_is_kept_when_requested(monkeypatch):
    nb = run_cells([JEDI_CELL.format(args="ipython_use_jedi=True")], monkeypatch)
    assert nb.cells[0].outputs[0].text == "True\n"


def test_example_notebook_runs(tmp_path, monkeypatch):
    pytest.importorskip("matplotlib")
    monkeypatch.setenv("MPLBACKEND", "Agg")
    source = Path(__file__).parent.parent / "examples" / "ex-jupyter"
    folder = shutil.copytree(source, tmp_path / "ex-jupyter")
    nb = run_notebook(nbformat.read(folder / "ex-jupyter.ipynb", as_version=4), monkeypatch, folder)

    stdout = "".join(
        out.text
        for cell in nb.cells
        for out in cell.get("outputs", [])
        if out.output_type == "stream" and out.name == "stdout"
    )
    # Not "running twiss...": MAD-NG prints it after the cell that sent it has finished, and
    # nbclient drops output that arrives between two cells (a notebook front end shows it)
    assert "loading the fodo sequence..." in stdout
    assert "done" in stdout
