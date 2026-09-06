import unittest
from pathlib import Path

try:
    import nbformat
    from nbclient import NotebookClient
    from nbclient.exceptions import CellExecutionError

    HAS_NBCLIENT = True
except ImportError:
    HAS_NBCLIENT = False

NOTEBOOK = Path(__file__).parent.parent / "examples" / "ex-jupyter" / "ex-jupyter.ipynb"


@unittest.skipUnless(
    HAS_NBCLIENT, "install the 'jupyter' extra (pip install .[jupyter]) to run this test"
)
class TestJupyterExample(unittest.TestCase):
    """Runs examples/ex-jupyter/ex-jupyter.ipynb in a Jupyter
    kernel, to prove that pymadng works from inside a notebook.

    mad.send() does not block until MAD-NG finishes running the sent code, so
    (as the notebook itself explains) the output of a `send()`-only cell is
    only drained and displayed once Python next talks to the MAD-NG process -
    here, that is the following cell, which pulls mtbl.s/mtbl.beta11 back.
    """

    def test_notebook_runs_and_streams_output(self):
        nb = nbformat.read(NOTEBOOK, as_version=4)
        client = NotebookClient(
            nb,
            timeout=120,
            kernel_name="python3",
            resources={"metadata": {"path": str(NOTEBOOK.parent)}},
        )
        try:
            client.execute()
        except CellExecutionError as e:
            self.fail(f"Example notebook failed to execute: {e}")

        def cell_stream_text(cell) -> str:
            return "".join(
                output.get("text", "")
                for output in cell.get("outputs", [])
                if output.get("output_type") == "stream"
            )

        creation_cell = next(
            cell
            for cell in nb.cells
            if cell.cell_type == "code" and "mad = MAD()" in cell.source
        )
        twiss_cell = next(
            cell for cell in nb.cells if cell.cell_type == "code" and "twiss" in cell.source
        )
        plot_cell = next(
            cell for cell in nb.cells if cell.cell_type == "code" and "plt.plot" in cell.source
        )

        # Check not there in the first cell
        self.assertNotIn("loading the fodo sequence", cell_stream_text(creation_cell))

        # Check not in the twiss cell, but in the next cell (plot_cell) that actually interacts with MAD-NG
        self.assertNotIn("loading the fodo sequence", cell_stream_text(twiss_cell))
        self.assertNotIn("running twiss", cell_stream_text(twiss_cell))

        # The print output is not attributed to twiss_cell itself (send() does not
        # block), but to the next cell that actually interacts with MAD-NG (plot_cell).
        self.assertEqual(cell_stream_text(twiss_cell), "")
        self.assertIn("loading the fodo sequence", cell_stream_text(plot_cell))
        self.assertIn("running twiss", cell_stream_text(plot_cell))
        self.assertIn("done", cell_stream_text(plot_cell))

        cached_translation = NOTEBOOK.parent / "fodo.mad"
        if cached_translation.exists():
            cached_translation.unlink()


if __name__ == "__main__":
    unittest.main()
