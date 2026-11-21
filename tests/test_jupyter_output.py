import pytest

nbformat = pytest.importorskip("nbformat")
nbclient = pytest.importorskip("nbclient")
pytest.importorskip("ipykernel")

CELLS = [
    "from pymadng import MAD\nmad = MAD()",
    "mad.send(\"print('stdout line from MAD-NG')\")\nmad.send('py:send(1)'); mad.recv()",
    "mad.send(\"io.stderr:write('stderr line from MAD-NG\\\\n')\")\nmad.send('py:send(2)'); mad.recv()",
]


def run_notebook(cells, monkeypatch):
    monkeypatch.delenv("PYTEST_CURRENT_TEST")  # ipykernel does not capture fds when it is set
    nb = nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell(c) for c in cells])
    nbclient.NotebookClient(nb, timeout=60, kernel_name="python3").execute()
    return nb


def test_mad_output_is_captured_by_the_kernel(monkeypatch):
    """ipykernel captures fd 1 and 2 into the running cell; MAD-NG must write to those fds."""
    nb = run_notebook(CELLS, monkeypatch)

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
    nb = run_notebook([JEDI_CELL.format(args="")], monkeypatch)
    assert nb.cells[0].outputs[0].text == "False\n"


def test_jedi_is_kept_when_requested(monkeypatch):
    nb = run_notebook([JEDI_CELL.format(args="ipython_use_jedi=True")], monkeypatch)
    assert nb.cells[0].outputs[0].text == "True\n"
