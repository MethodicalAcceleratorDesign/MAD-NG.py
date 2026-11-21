import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"

# The scripts of examples/runall.py
EXAMPLE_SCRIPTS = [
    "ex-benchmark-and-fork/ex-benchmark-and-fork.py",
    "ex-fodo/ex-fodos.py",
    "ex-lhc-couplingLocal/ex-lhc-couplingLocal.py",
    "ex-managing-refs/ex-managing-refs.py",
    "ex-LowLevel/ex-send-multypes.py",
    "ex-LowLevel/ex-send-recv.py",
    "ex-ps-twiss/ex-ps-twiss.py",
    "ex-recv-lhc/ex-defexpr.py",
]


@pytest.mark.parametrize("name", EXAMPLE_SCRIPTS)
def test_example_runs(name, tmp_path):
    """Each example runs end to end in a copy of its folder (the examples write into it)."""
    script = EXAMPLES_DIR / name
    if "matplotlib" in script.read_text() and importlib.util.find_spec("matplotlib") is None:
        pytest.skip("install the 'jupyter' extra for matplotlib")

    folder = tmp_path / script.parent.name
    shutil.copytree(script.parent, folder)
    result = subprocess.run(
        [sys.executable, str(folder / script.name)],
        cwd=folder,
        # The Agg backend makes plt.show() a no-op; limit the threads on shared hosts
        env=dict(os.environ, MPLBACKEND="Agg", OMP_NUM_THREADS="2"),
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert result.returncode == 0, (
        f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
    )
