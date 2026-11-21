import time
from pathlib import Path

import pytest

from pymadng import MAD

inputs_folder = Path(__file__).parent / "inputs"


def test_logfile(tmp_path):
    test_log1 = tmp_path / "test.log"
    test_log2 = tmp_path / "test2.log"
    example_log = inputs_folder / "example.log"

    with MAD(stdout=test_log1, debug=True, raise_on_madng_error=False):
        pass
    time.sleep(0.1)  # Wait for file to be written
    assert test_log1.read_text() == example_log.read_text()

    with MAD(stdout=test_log2, debug=True) as mad:
        mad.send("!This is a line that does nothing")
        mad.send("print('hello world')")

    text = test_log2.read_text()
    assert "[!This is a line that does nothing]" in text
    assert "hello world\n" in text
    assert "[print('hello world')]" in text

    with MAD(stdout=test_log2, debug=False) as mad:
        mad.send("!This is a line that does nothing")
        mad.send("print('hello world')")

    assert test_log2.read_text() == "hello world\n"


def test_err(tmp_path):
    test_log = tmp_path / "test.log"

    # Run debug without stderr redirection
    with (
        test_log.open("w") as f,
        MAD(debug=True, stdout=f, raise_on_madng_error=False) as mad,
    ):
        mad.psend("a = nil/2")
        # receive the error before closing the pipe
        with pytest.raises(RuntimeError):
            mad.recv()
    file_text = test_log.read_text()
    assert "[py:__err(true); a = nil/2; py:__err(false);]" in file_text  # command was sent
    assert "***pymad.run:" not in file_text  # error was not in stdout

    # Run debug with stderr redirection
    with MAD(stdout=test_log, redirect_stderr=True) as mad:
        mad.psend("a = nil/2")
        with pytest.raises(RuntimeError):
            mad.recv()
    assert test_log.read_text()[:13] == "***pymad.run:"  # error was in stdout
