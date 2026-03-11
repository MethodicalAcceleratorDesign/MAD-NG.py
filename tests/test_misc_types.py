from __future__ import annotations

import numpy as np
import pytest

from pymadng import MAD

RANGE_CASES = [
    pytest.param(
        "MAD.range(3, 11, 2)",
        range(3, 12, 2),
        False,
        id="integer-range",
    ),
    pytest.param(
        "MAD.nrange(3.5, 21.4, 12)",
        np.linspace(3.5, 21.4, 12),
        False,
        id="numeric-range",
    ),
    pytest.param(
        "MAD.nlogrange(1, 20, 20)",
        np.geomspace(1, 20, 20),
        False,
        id="log-range",
    ),
    pytest.param(
        "MAD.range(3, 11, 2)",
        list(range(3, 12, 2)),
        True,
        id="integer-range-table",
    ),
    pytest.param(
        "MAD.nrange(3.5, 21.4, 12)",
        np.linspace(3.5, 21.4, 12),
        True,
        id="numeric-range-table",
    ),
    pytest.param(
        "MAD.nlogrange(1, 20, 20)",
        np.geomspace(1, 20, 20),
        True,
        id="log-range-table",
    ),
]

SEND_RANGE_CASES = [
    pytest.param(
        "send",
        (range(3, 10, 1),),
        "py:recv() + 1",
        list(range(4, 12, 1)),
        id="python-range",
    ),
    pytest.param(
        "send_range",
        (3.5, 21.4, 14),
        "py:recv() + 2",
        np.linspace(5.5, 23.4, 14),
        id="numeric-range",
    ),
    pytest.param(
        "send_logrange",
        (1, 20, 20),
        "py:recv()",
        np.geomspace(1, 20, 20),
        id="log-range",
    ),
]

TPSA_MONOMIALS = np.asarray(
    [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [2, 0, 0], [1, 1, 0]],
    dtype=np.uint8,
)
TPSA_INDEX = ["000", "100", "010", "001", "200", "110"]


def assert_received_value(actual, expected):
    if isinstance(expected, np.ndarray):
        assert np.allclose(actual, expected)
    else:
        assert actual == expected


def test_send_recv_nil():
    with MAD() as mad:
        mad.send(
            """
            local myNil = py:recv()
            py:send(myNil)
            py:send(nil)
            py:send()
            """
        )
        mad.send(None)
        assert mad.recv() is None
        assert mad.recv() is None
        assert mad.recv() is None


@pytest.mark.parametrize(("lua_expr", "expected", "as_table"), RANGE_CASES)
def test_recv_ranges(lua_expr, expected, as_table):
    with MAD() as mad:
        mad.send(
            f"""
            local value = {lua_expr}
            py:send({"value:totable()" if as_table else "value"}{", true" if as_table else ""})
            """
        )
        assert_received_value(mad.recv(), expected)


@pytest.mark.parametrize(("send_method", "args", "lua_expr", "expected"), SEND_RANGE_CASES)
def test_send_ranges(send_method, args, lua_expr, expected):
    with MAD() as mad:
        mad.send(
            f"""
            local value = {lua_expr}
            py:send(value:totable(), true)
            """
        )
        getattr(mad, send_method)(*args)
        assert_received_value(mad.recv(), expected)


@pytest.mark.parametrize(("value", "expected"), [(True, False), (False, True)])
def test_send_recv_bool(value, expected):
    with MAD() as mad:
        mad.send(
            """
            local value = py:recv()
            py:send(not value)
            """
        )
        mad.send(data=value)
        assert mad.recv() == expected


@pytest.mark.parametrize(
    ("lua_input", "expected"),
    [
        ("{1, 2, 3, 4, 6, 20, 100}", [1, 2, 3, 4, 6, 20, 100]),
        ('"WZ346oy"', [32, 35, 3, 4, 6, 50, 60]),
    ],
    ids=["from-table", "from-string"],
)
def test_recv_monomial(lua_input, expected):
    with MAD() as mad:
        mad.send(
            f"""
            local m = MAD.monomial({lua_input})
            py:send(m)
            """
        )
        assert np.all(mad.recv() == expected)


def test_send_recv_monomial():
    with MAD() as mad:
        mad.send(
            """
            local m1 = py:recv()
            local m2 = py:recv()
            py:send(m1 + m2)
            """
        )
        rng = np.random.default_rng()
        pym1 = rng.integers(0, 255, 20, dtype=np.ubyte)
        pym2 = rng.integers(0, 255, 20, dtype=np.ubyte)
        mad.send(pym1)
        mad.send(pym2)
        mad_res = mad.recv()
        assert np.all(mad_res == pym1 + pym2)
        assert mad_res.dtype == np.dtype("ubyte")


@pytest.mark.parametrize(
    ("lua_type", "setter_values", "expected_coefficients"),
    [
        pytest.param(
            "tpsa",
            ("2", "1", "1", "1"),
            [11, 6, 4, 2, 1, 1],
            id="real",
        ),
        pytest.param(
            "ctpsa",
            ("2+1i", "1+2i", "1+2i", "1+2i"),
            [10 + 6j, 2 + 14j, 2 + 9j, 2 + 4j, -3 + 4j, -3 + 4j],
            id="complex",
        ),
    ],
)
def test_recv_tpsa(lua_type, setter_values, expected_coefficients):
    with MAD() as mad:
        first, second, third, fourth = setter_values
        mad.send(
            f"""
            local d = MAD.gtpsad(3, 6)
            res = MAD.{lua_type}(6):set(1,{first}):set(2, {second})
            res2 = res:copy():set(3, {third})
            res3 = res2:copy():set(4, {fourth})
            py:send(res:axypbzpc(res2, res3, 1, 2, 3))
            """
        )
        monomials, coefficients = mad.recv()
        assert np.array_equal(monomials, TPSA_MONOMIALS)
        assert np.all(coefficients == expected_coefficients)


@pytest.mark.parametrize(
    ("send_method", "coefficients"),
    [
        pytest.param("send_tpsa", [11, 6, 4, 2, 1, 1], id="real"),
        pytest.param(
            "send_cpx_tpsa", [10 + 6j, 2 + 14j, 2 + 9j, 2 + 4j, -3 + 4j, -3 + 4j], id="complex"
        ),
    ],
)
def test_send_tpsa(send_method, coefficients):
    with MAD() as mad:
        mad.send(
            """
            tab = py:recv()
            index_part = {}
            for i = 1, #tab do
                index_part[i] = tab[i]
            end
            py:send(tab, true)
            py:send(index_part, true)
            """
        )
        getattr(mad, send_method)(TPSA_MONOMIALS, coefficients)

        whole_tab = mad.recv("tab")
        index_part = mad.recv("index_part")
        assert index_part == TPSA_INDEX
        for key, value in whole_tab.items():
            if isinstance(key, int):
                assert value == TPSA_INDEX[key - 1]
            else:
                idx = TPSA_INDEX.index(key)
                assert whole_tab[key] == coefficients[idx]


def test_send_recv_damap():
    with MAD() as mad:
        mad.send(
            """
            py:__err(true)
            local sin in MAD.gmath
            MAD.gtpsad(6, 5)
            local M = MAD.damap {xy = 5}
            M[1] = 1 ; M[3] = 2 ; M[5] = 3
            M[2] = 2 ; M[4] = 1 ; M[6] = 1
            res = sin(M[1]) * sin(M[3])
            py:send(res)
            recved = MAD.tpsa():fromtable(py:recv())
            py:send(recved)
            """
        )
        init = mad.recv()
        mad.send_tpsa(*init)
        final = mad.recv()
        assert (init[0] == final[0]).all()
        assert (init[1] == final[1]).all()
