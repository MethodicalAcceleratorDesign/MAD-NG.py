import importlib.util
import os
import subprocess
import sys
import unittest
from pathlib import Path

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"

# Mirrors examples/runall.py's list, run one process per example so a single
# failure doesn't stop the rest, and each gets its own cwd/env.
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

NEEDS_MATPLOTLIB = {
    "ex-benchmark-and-fork/ex-benchmark-and-fork.py",
    "ex-fodo/ex-fodos.py",
    "ex-lhc-couplingLocal/ex-lhc-couplingLocal.py",
}

HAS_MATPLOTLIB = importlib.util.find_spec("matplotlib") is not None


def _make_test(name):
    def test(self):
        if name in NEEDS_MATPLOTLIB and not HAS_MATPLOTLIB:
            self.skipTest("install the 'jupyter' extra (pip install .[jupyter]) for matplotlib")

        script = EXAMPLES_DIR / name
        env = dict(os.environ)
        # Non-interactive backend: plt.show()/plt.ion()/canvas.draw() become
        # no-ops instead of opening a GUI window and blocking the test.
        env["MPLBACKEND"] = "Agg"

        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(script.parent),
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode != 0:
            self.fail(
                f"{name} exited with code {result.returncode}\n"
                f"--- stdout ---\n{result.stdout}\n"
                f"--- stderr ---\n{result.stderr}"
            )
    return test


class TestExamplesRun(unittest.TestCase):
    """Runs every example script end-to-end as a subprocess, to catch
    regressions that break the examples (import errors, API drift, etc.)
    without needing plotting windows to open.
    """


for _name in EXAMPLE_SCRIPTS:
    _test_name = "test_" + _name.replace("/", "_").replace("-", "_").replace(".py", "")
    setattr(TestExamplesRun, _test_name, _make_test(_name))


if __name__ == "__main__":
    unittest.main()
