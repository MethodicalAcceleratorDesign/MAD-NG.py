from __future__ import annotations

import io
import re
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pymadng import MAD
from pymadng.madp_pymad import MadProcess

INPUTS_FOLDER = Path(__file__).parent / "inputs"
ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    return ANSI_ESCAPE.sub("", text)


def make_test_process() -> MadProcess:
    process = object.__new__(MadProcess)
    process.py_name = "py"
    process.process = MagicMock()
    process.process.poll.return_value = None
    process.mad_read_stream = MagicMock()
    process.mad_input_stream = MagicMock()
    process.python_exec_context = {}
    process._debugger_active = False
    process.close = MagicMock()
    process.send = MagicMock()
    process.recv = MagicMock()
    process.protected_variable_retrieval = MagicMock()
    return process


def test_logfile(tmp_path):
    test_log1 = tmp_path / "test.log"
    test_log2 = tmp_path / "test2.log"

    with MAD(stdout=test_log1, debug=True, raise_on_madng_error=False):
        pass
    time.sleep(0.1)
    text = test_log1.read_text()
    assert "***pymad.recv: binary data 4 bytes" in text
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


def test_madprocess_startup_failure_paths():
    common_patches = [
        patch("pymadng.madp_pymad.Path.exists", return_value=True),
        patch("pymadng.madp_pymad.os.pipe", side_effect=[(10, 11), (12, 13)]),
        patch("pymadng.madp_pymad.os.fdopen", side_effect=[MagicMock(), MagicMock()]),
        patch("pymadng.madp_pymad.os.close"),
        patch("pymadng.madp_pymad.subprocess.Popen", return_value=MagicMock()),
        patch.object(MadProcess, "_setup_signal_handler"),
        patch.object(MadProcess, "send"),
        patch.object(MadProcess, "close"),
    ]

    with (
        common_patches[0],
        common_patches[1],
        common_patches[2],
        common_patches[3],
        common_patches[4],
        common_patches[5],
        common_patches[6],
        common_patches[7],
        patch("pymadng.madp_pymad.select.select", return_value=([], [], [])),
        patch.object(MadProcess, "recv", return_value="started"),
        pytest.raises(OSError, match="Could not establish communication"),
    ):
        MadProcess("/tmp/mad")

    with (
        patch("pymadng.madp_pymad.Path.exists", return_value=True),
        patch("pymadng.madp_pymad.os.pipe", side_effect=[(10, 11), (12, 13)]),
        patch("pymadng.madp_pymad.os.fdopen", side_effect=[MagicMock(), MagicMock()]),
        patch("pymadng.madp_pymad.os.close"),
        patch("pymadng.madp_pymad.subprocess.Popen", return_value=MagicMock()),
        patch.object(MadProcess, "_setup_signal_handler"),
        patch.object(MadProcess, "send"),
        patch.object(MadProcess, "close"),
        patch("pymadng.madp_pymad.select.select", return_value=([object()], [], [])),
        patch.object(MadProcess, "recv", return_value="boom"),
        pytest.raises(OSError, match="Could not start"),
    ):
        MadProcess("/tmp/mad")


def test_madprocess_internal_debugger_branches():
    process = make_test_process()
    with pytest.raises(TypeError, match="Debugger commands must be strings"):
        process._normalise_debugger_command(1)  # type: ignore[arg-type]

    process = make_test_process()
    process.process.poll.return_value = 0
    assert process._read_debugger_state() == "terminated"

    process = make_test_process()
    process.recv.side_effect = RuntimeError("boom")
    with (
        patch("pymadng.madp_pymad.select.select", return_value=([object()], [], [])),
        pytest.raises(RuntimeError, match="boom"),
    ):
        process._read_debugger_state()

    process = make_test_process()
    process.recv.return_value = "unexpected"
    with (
        patch("pymadng.madp_pymad.select.select", return_value=([object()], [], [])),
        pytest.raises(RuntimeError, match="Unexpected message"),
    ):
        process._read_debugger_state()

    process = make_test_process()
    process._debugger_active = True
    with pytest.raises(RuntimeError, match="already active"):
        process.enter_debugger()

    process = make_test_process()
    process.recv.return_value = "not-enter"
    with pytest.raises(RuntimeError, match="Unexpected message received while entering debugger"):
        process.enter_debugger(commands=["c"])

    process = make_test_process()
    with pytest.raises(ValueError, match="must end with continue"):
        process._run_scripted_debugger(["h"])

    process = make_test_process()
    process._read_debugger_state = MagicMock(side_effect=["active", "active", "resumed"])
    process._run_scripted_debugger(["h", "c"])

    process = make_test_process()
    process._read_debugger_state = MagicMock(side_effect=["active", "active", "terminated"])
    process._run_scripted_debugger(["h", "q"])
    process.close.assert_called_once()

    process = make_test_process()
    process._read_debugger_state = MagicMock(side_effect=["active", "active", "active"])
    with pytest.raises(RuntimeError, match="did not resume"):
        process._run_scripted_debugger(["h", "c"])

    process = make_test_process()
    process._stdin_is_tty = MagicMock(return_value=True)
    process._run_readline_debugger = MagicMock()
    process._run_interactive_debugger(None)
    process._run_readline_debugger.assert_called_once()

    process = make_test_process()
    process._stdin_is_tty = MagicMock(return_value=False)
    process._read_debugger_state = MagicMock(return_value="resumed")
    with (
        patch("pymadng.madp_pymad.Path.open", side_effect=OSError),
        patch("sys.stdin", io.StringIO("c\n")),
    ):
        process._run_interactive_debugger(None)

    process = make_test_process()
    process.process.poll.return_value = 0
    with pytest.raises(RuntimeError, match="terminated the subprocess"):
        process._run_interactive_debugger(io.StringIO(""))

    process = make_test_process()
    with pytest.raises(EOFError, match="Reached EOF"):
        process._run_interactive_debugger(io.StringIO(""))

    process = make_test_process()
    with patch("pymadng.madp_pymad.os.isatty", side_effect=ValueError):
        assert process._stdin_is_tty() is False

    process = make_test_process()
    process._read_debugger_state = MagicMock(return_value="terminated")
    with patch("builtins.input", return_value="q"):
        process._run_readline_debugger()
    process.close.assert_called_once()

    process = make_test_process()
    process.process.poll.return_value = 0
    with (
        patch("builtins.input", side_effect=EOFError),
        pytest.raises(RuntimeError, match="terminated the subprocess"),
    ):
        process._run_readline_debugger()

    process = make_test_process()
    with (
        patch("builtins.input", side_effect=EOFError),
        pytest.raises(EOFError, match="Reached EOF"),
    ):
        process._run_readline_debugger()

    with patch("sys.stdout.write", side_effect=OSError):
        make_test_process()._render_debugger_prompt()


def test_madprocess_internal_recv_and_close_branches():
    process = make_test_process()
    process.recv.return_value = "value = 3"
    env = process.recv_and_exec()
    assert env["value"] == 3
    assert env["mad"] is process

    process = make_test_process()
    process.recv.return_value = "value = 4"
    env = {"mad": "sentinel"}
    result = process.recv_and_exec(env)
    assert result["mad"] == "sentinel"

    with pytest.raises(ValueError, match="Cannot retrieve private variables"):
        make_test_process().recv_vars("_private")

    process = make_test_process()
    process.recv.return_value = "unexpected"
    process.stdout_file = MagicMock()
    process.mad_read_stream.closed = False
    process.mad_input_stream.closed = False
    with (
        patch("pymadng.madp_pymad.select.select", return_value=([object()], [], [])),
        patch("pymadng.madp_pymad.logging.warning") as warning,
    ):
        MadProcess.close(process)
    warning.assert_called_once()

    process = make_test_process()
    process.send.side_effect = BrokenPipeError
    process.stdout_file = MagicMock()
    process.mad_read_stream.closed = False
    process.mad_input_stream.closed = False
    MadProcess.close(process)
