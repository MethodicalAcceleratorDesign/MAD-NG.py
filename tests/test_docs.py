import os
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FODO = ROOT / "examples" / "ex-jupyter" / "fodo.seq"
FENCE = re.compile(r"^ *```python\n(.*?)^ *```", re.S | re.M)


def test_quickstart_runs(tmp_path):
    text = (ROOT / "docs" / "source" / "quickstart.md").read_text()
    shutil.copy(FODO, tmp_path / "fodo.seq")
    script = tmp_path / "quickstart.py"
    script.write_text("\n".join(textwrap.dedent(b) for b in FENCE.findall(text)))
    env = {**os.environ, "MPLBACKEND": "Agg", "OMP_NUM_THREADS": "2"}
    run = subprocess.run(
        [sys.executable, str(script)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert run.returncode == 0, run.stderr[-2000:]
