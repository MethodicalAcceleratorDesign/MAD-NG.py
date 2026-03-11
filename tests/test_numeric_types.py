from __future__ import annotations

import numpy as np
import pytest

from pymadng import MAD

FLT_EPS = 2**-52
FLT_TINY = 2**-1022
FLT_HUGE = 2**1023
FLOAT_VALUES = [
    0,
    FLT_TINY,
    2**-64,
    2**-63,
    2**-53,
    FLT_EPS,
    2**-52,
    2 * FLT_EPS,
    2**-32,
    2**-31,
    1e-9,
    0.1 - FLT_EPS,
    0.1,
    0.1 + FLT_EPS,
    0.5,
    0.7 - FLT_EPS,
    0.7,
    0.7 + FLT_EPS,
    1 - FLT_EPS,
    1,
    1 + FLT_EPS,
    1.1,
    1.7,
    2,
    10,
    1e2,
    1e3,
    1e6,
    1e9,
    2**31,
    2**32,
    2**52,
    2**53,
    2**63,
    2**64,
    FLT_HUGE,
]
INT_VALUES = [0, 1, 2, 10, 1e2, 1e3, 1e6, 1e9, 2**31 - 1]


def test_send_recv_list():
    with MAD() as mad:
        test_list = [[1, 2, 3, 4, 5, 6, 7, 8, 9]] * 2
        mad.send(
            """
            list = py:recv()
            list[1][1] = 10
            list[2][1] = 10
            py:send(list)
            """
        )
        mad.send(test_list)
        test_list[0][0] = 10
        test_list[1][0] = 10
        mad_list = mad.recv("list")

        for i, inner_list in enumerate(mad_list):
            for j, value in enumerate(inner_list):
                assert value == test_list[i][j], (
                    f"Mismatch at index [{i}][{j}]: {value} != {test_list[i][j]}"
                )


def test_send_recv_list_with_ref():
    with MAD() as mad:
        python_dict = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, "a": 10, "b": 3, "c": 4}
        mad.send(
            """
            list = {MAD.object "a" {a = 2}, MAD.object "b" {b = 6}}
            list2 = py:recv()
            py:send(list)
            py:send(list2)
            """
        ).send(python_dict)
        list1 = mad.recv("list")
        list2 = mad.recv("list2")
        received_dict = list2.eval()

        assert len(list1) == 2
        assert received_dict == python_dict
        assert list1[0].a == 2
        assert list1[1].b == 6


@pytest.mark.parametrize("value", INT_VALUES)
def test_send_recv_int(value):
    with MAD() as mad:
        mad.send(
            """
            local is_integer in MAD.typeid
            local num = py:recv()
            py:send(num)
            py:send(-num)
            py:send(is_integer(num))
            """
        )
        mad.send(value)
        recv_num = mad.recv()
        assert recv_num == value
        assert isinstance(recv_num, np.int32)

        recv_num = mad.recv()
        assert recv_num == -value
        assert isinstance(recv_num, np.int32)
        assert mad.recv()


@pytest.mark.parametrize("value", FLOAT_VALUES)
def test_send_recv_num(value):
    with MAD() as mad:
        mad.send(
            """
            local num = py:recv()
            local negative = py:recv()
            py:send(num)
            py:send(negative)
            py:send(num * 1.61)
            """
        )
        mad.send(value)
        mad.send(-value)
        assert mad.recv() == value
        assert mad.recv() == -value
        assert mad.recv() == value * 1.61


def test_send_recv_cpx():
    with MAD() as mad:
        for real in FLOAT_VALUES:
            for imag in FLOAT_VALUES:
                mad.send(
                    """
                    local my_cpx = py:recv()
                    py:send(my_cpx)
                    py:send(-my_cpx)
                    py:send(my_cpx * 1.31i)
                    """
                )
                value = real + 1j * imag
                mad.send(value)
                assert mad.recv() == value
                assert mad.recv() == -value
                assert mad.recv() == value * 1.31j


@pytest.mark.parametrize(
    ("lua_ctor", "array"),
    [
        (
            "MAD.imatrix(3, 5):seq()",
            np.random.default_rng().integers(0, 255, (5, 5), dtype=np.int32),
        ),
        ("MAD.matrix(3, 5):seq() / 2", np.arange(1, 25).reshape(4, 6) / 4),
        (
            "MAD.cmatrix(3, 5):seq() / 2i",
            np.arange(1, 25).reshape(4, 6) / 4 + 1j * np.arange(1, 25).reshape(4, 6) / 4,
        ),
    ],
    ids=["imat", "mat", "cmat"],
)
def test_send_recv_matrices(lua_ctor, array):
    with MAD() as mad:
        local_name = (
            "imat"
            if np.issubdtype(array.dtype, np.integer)
            else "cmat"
            if np.iscomplexobj(array)
            else "mat"
        )
        mad.send(
            f"""
            local {local_name} = py:recv()
            py:send({local_name})
            py:send({lua_ctor})
            """
        )
        mad.send(array)
        assert np.all(mad.recv() == array)

        expected = np.arange(1, 16).reshape(3, 5)
        if np.issubdtype(array.dtype, np.integer):
            assert np.all(mad.recv() == expected)
        elif np.iscomplexobj(array):
            assert np.all(mad.recv() == (expected / 2j))
        else:
            assert np.all(mad.recv() == (expected / 2))
