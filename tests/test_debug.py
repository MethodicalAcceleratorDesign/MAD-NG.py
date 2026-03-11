from __future__ import annotations

import io
import re
import time
from pathlib import Path

import pytest

from pymadng import MAD

INPUTS_FOLDER = Path(__file__).parent / "inputs"
ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    return ANSI_ESCAPE.sub("", text)


def test_logfile(tmp_path):
    test_log1 = tmp_path / "test.log"
    test_log2 = tmp_path / "test2.log"

    with MAD(stdout=test_log1, debug=True, raise_on_madng_error=False):
        pass
    time.sleep(0.1)
    text = test_log1.read_text()
    assert "***pymad.recv: type is str_" in text
    assert "io.stdout:setvbuf('line')" in text
    assert "py:send('started')" in text
    assert "started" in text

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
    test_log1 = tmp_path / "test.log"

    with (
        test_log1.open("w") as handle,
        MAD(debug=True, stdout=handle, raise_on_madng_error=False) as mad,
    ):
        mad.psend("a = nil/2")
        with pytest.raises(RuntimeError):
            mad.recv()

    file_text = test_log1.read_text()
    assert "[py:__err(true); a = nil/2; py:__err(false);]" in file_text
    assert "***pymad.run:" not in file_text

    with MAD(stdout=test_log1, redirect_stderr=True) as mad:
        mad.psend("a = nil/2")
        with pytest.raises(RuntimeError):
            mad.recv()

    assert test_log1.read_text()[:13] == "***pymad.run:"


def test_breakpoint(tmp_path):
    test_log = tmp_path / "test_breakpoint.log"

    with MAD(stdout=test_log, redirect_stderr=True, raise_on_madng_error=False) as mad:
        for name in ("python_breakpoint", "pydbg", "breakpoint"):
            mad.send(f"py:send(type({name}))")
            assert mad.recv() == "function"

        mad.breakpoint(commands=["h", "c"])
        mad.send("py:send('alive')")
        assert mad.recv() == "alive"

    file_text = strip_ansi(test_log.read_text())
    assert "break via dbg()" in file_text
    assert "h(elp)" in file_text


def test_breakpoint_from_py_send(tmp_path):
    test_log = tmp_path / "test_breakpoint_exec.log"

    with MAD(stdout=test_log, redirect_stderr=True, raise_on_madng_error=False) as mad:
        mad.send("py:send([[breakpoint(commands=['h', 'c'])]])")
        mad.recv_and_exec()
        mad.send("py:send([[pydbg(commands=['c'])]])")
        mad.recv_and_exec()
        mad.send("py:send('alive')")
        assert mad.recv() == "alive"

    file_text = strip_ansi(test_log.read_text())
    assert file_text.count("break via dbg()") >= 2


def test_breakpoint_invalid_scripted_commands(tmp_path):
    test_log = tmp_path / "test_breakpoint_invalid.log"

    with MAD(stdout=test_log, redirect_stderr=True, raise_on_madng_error=False) as mad:
        with pytest.raises(ValueError, match="must not be empty"):
            mad.breakpoint(commands=[])

        mad.send("py:send('alive')")
        assert mad.recv() == "alive"


def test_breakpoint_interactive_input_stream_resume(tmp_path):
    test_log = tmp_path / "test_breakpoint_input_stream_resume.log"

    with MAD(stdout=test_log, redirect_stderr=True, raise_on_madng_error=False) as mad:
        mad.breakpoint(input_stream=io.StringIO("h\nc\n"))
        mad.send("py:send('alive')")
        assert mad.recv() == "alive"

    file_text = strip_ansi(test_log.read_text())
    assert "break via dbg()" in file_text
    assert "h(elp)" in file_text


def test_breakpoint_interactive_input_stream_quit(tmp_path):
    test_log = tmp_path / "test_breakpoint_input_stream_quit.log"

    with MAD(stdout=test_log, redirect_stderr=True, raise_on_madng_error=False) as mad:
        mad.breakpoint(input_stream=io.StringIO("q\n"))
        assert mad._MAD__process.process.poll() is not None
        assert mad._MAD__process.mad_read_stream.closed
        assert mad._MAD__process.mad_input_stream.closed

    assert "break via dbg()" in strip_ansi(test_log.read_text())


def test_breakpoint_reentry_from_python_callback(tmp_path):
    test_log = tmp_path / "test_breakpoint_reentry.log"

    with MAD(stdout=test_log, redirect_stderr=True, raise_on_madng_error=False) as mad:
        mad.send("py:send([[breakpoint(commands=['c'])]])")
        mad.recv_and_exec({"breakpoint": lambda *_args, **_kwargs: mad.breakpoint(commands=["c"])})

        mad.send("py:send('alive')")
        assert mad.recv() == "alive"


def test_breakpoint_quit(tmp_path):
    test_log = tmp_path / "test_breakpoint_quit.log"

    with MAD(stdout=test_log, redirect_stderr=True, raise_on_madng_error=False) as mad:
        mad.breakpoint(commands=["q"])
        assert mad._MAD__process.process.poll() is not None
        assert mad._MAD__process.mad_read_stream.closed
        assert mad._MAD__process.mad_input_stream.closed

    assert "break via dbg()" in strip_ansi(test_log.read_text())
