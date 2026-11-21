from __future__ import annotations

import threading
from unittest.mock import patch

import pytest

from pymadng import MAD


def test_recv_and_exec():
    with MAD() as mad:
        mad.send(
            """py:send([==[mad.send('''py:send([=[mad.send("py:send([[a = 100/2]])")]=])''')]==])"""
        )
        mad.recv_and_exec()
        mad.recv_and_exec()
        assert mad.recv_and_exec()["a"] == 50


def test_err():
    with MAD(stdout="/dev/null", redirect_stderr=True) as mad:
        mad.send("py:__err(true)")
        mad.send("1+1")
        with pytest.raises(RuntimeError):
            mad.recv()

        mad.send("py:__err(true)")
        mad.send("print(nil/2)")
        with pytest.raises(RuntimeError):
            mad.recv()


def test_recv():
    with MAD() as mad:
        mad.send("py:send('hi')")
        mad.send("""py:send([[Multiline string should work

Like So.]])""")
        assert mad.recv() == "hi"
        assert mad.receive() == "Multiline string should work\n\nLike So."


@pytest.mark.parametrize(
    "value",
    [
        "asdfghjkl;",
        """Py Multiline string should work

Like So.]])""",
    ],
)
def test_send(value: str):
    with MAD() as mad:
        mad.send("str = py:recv(); py:send(str .. str)")
        mad.send(value)
        assert mad.recv() == value * 2


def test_protected_send():
    with MAD(stdout="/dev/null", redirect_stderr=True, raise_on_madng_error=False) as mad:
        mad.send("py:send('hello world'); a = nil/2")
        assert mad.recv() == "hello world"
        mad.send("py:send(1)")
        assert mad.recv() == 1

        mad.protected_send("a = nil/2")
        with pytest.raises(RuntimeError):
            mad.recv()

        mad.psend("a = nil/2")
        with pytest.raises(RuntimeError):
            mad.recv()


def test_print():
    with MAD() as mad:
        mad.send("py:send('hello world')")
        assert mad.recv() == "hello world"


@patch("pymadng.madp_pymad.MadProcess._setup_signal_handler")
def test_signal_handler_called_in_main_thread(mock_setup_signal_handler):
    with patch("pathlib.Path.exists", return_value=True):
        MAD()
    mock_setup_signal_handler.assert_called_once()


@patch("pymadng.madp_pymad.MadProcess._setup_signal_handler")
def test_signal_handler_not_called_in_non_main_thread(mock_setup_signal_handler):
    def create_mad_proc():
        with patch("pathlib.Path.exists", return_value=True):
            MAD()

    thread = threading.Thread(target=create_mad_proc)
    thread.start()
    thread.join()
    mock_setup_signal_handler.assert_not_called()
