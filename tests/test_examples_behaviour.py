from __future__ import annotations

import json
import os

import numpy as np
import pytest

from pymadng import MAD


def test_manual_close_without_context_manager():
    mad = MAD()
    try:
        mad.send("py:send(math.sqrt(16))")
        assert mad.recv() == 4
        assert mad._MAD__process.process.poll() is None
    finally:
        mad.close()

    assert mad._MAD__process.process.poll() is not None
    assert mad._MAD__process.mad_read_stream.closed
    assert mad._MAD__process.mad_input_stream.closed


@pytest.mark.skipif(not hasattr(os, "fork"), reason="requires os.fork")
def test_forked_processes_have_independent_mad_sessions():
    read_fd, write_fd = os.pipe()
    pid = os.fork()

    if pid == 0:
        os.close(read_fd)
        try:
            with MAD() as child_mad:
                child_mad["value"] = 7
                payload = {"value": int(child_mad["value"])}
        except RuntimeError as exc:  # pragma: no cover - child failure path
            payload = {"error": repr(exc)}
        finally:
            os.write(write_fd, json.dumps(payload).encode("utf-8"))
            os.close(write_fd)
            os._exit(0)

    os.close(write_fd)
    try:
        with MAD() as parent_mad:
            parent_mad["value"] = 3
            child_payload = os.read(read_fd, 4096).decode("utf-8")
            pid_done, status = os.waitpid(pid, 0)
            assert pid_done == pid
            assert os.WIFEXITED(status)
            assert os.WEXITSTATUS(status) == 0
            assert parent_mad["value"] == 3
            child_result = json.loads(child_payload)
            assert "error" not in child_result
            assert child_result["value"] == 7
    finally:
        os.close(read_fd)


def test_multi_assignment_of_numpy_arrays():
    with MAD() as mad:
        arr = np.arange(9, dtype=np.float64).reshape(3, 3)
        mad["arr1", "arr2", "arr3"] = arr, arr * 2, arr * 3

        recv1, recv2, recv3 = mad["arr1", "arr2", "arr3"]

    assert np.array_equal(recv1, arr)
    assert np.array_equal(recv2, arr * 2)
    assert np.array_equal(recv3, arr * 3)
