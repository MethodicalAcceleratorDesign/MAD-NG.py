from __future__ import annotations

import numpy as np

from pymadng import MAD

A_MATRIX = np.arange(1, 21).reshape(4, 5)
B_MATRIX = np.arange(1, 7).reshape(2, 3)
C_MATRIX = (np.arange(1, 16) + 1j).reshape(5, 3)


def test_load(tmp_path):
    with MAD() as mad:
        mad.load("MAD", "matrix")
        assert mad.send("py:send(matrix == MAD.matrix)").recv()

        mad.load("MAD.gmath")
        assert mad.send("py:send(sin == MAD.gmath.sin)").recv()
        assert mad.send("py:send(cos == MAD.gmath.cos)").recv()
        assert mad.send("py:send(tan == MAD.gmath.tan)").recv()

        mad.load("MAD.element", "quadrupole", "sextupole", "drift")
        assert mad.send("py:send(quadrupole == MAD.element.quadrupole)").recv()
        assert mad.send("py:send(sextupole  == MAD.element.sextupole )").recv()
        assert mad.send("py:send(drift      == MAD.element.drift     )").recv()

    test_file = tmp_path / "test.mad"
    test_file.write_text(
        """
            local matrix, cmatrix in MAD
            a = matrix(4, 5):seq()
            b = cmatrix(2, 3):seq()
            """
    )
    with MAD(stdout="/dev/null", redirect_stderr=True) as mad:
        mad.loadfile(test_file)
        assert mad.matrix is None
        assert np.all(mad.a == A_MATRIX)
        assert np.all(mad.b == B_MATRIX)

    test_file.write_text(
        """
            local matrix, cmatrix in MAD
            local a = matrix(4, 5):seq()
            local c = cmatrix(5, 3):seq() + 1i
            return {res1 = a * c, res2 = a * c:conj()}
            """
    )
    with MAD() as mad:
        mad.loadfile(test_file, "res1", "res2")
        assert np.all(mad.res1 == np.matmul(A_MATRIX, C_MATRIX))
        assert np.all(mad.res2 == np.matmul(A_MATRIX, C_MATRIX.conj()))


def test_globals():
    with MAD() as mad:
        mad.send_vars(a=1, b=2, c=3)
        global_vars = mad.globals()
        assert "a" in global_vars
        assert "b" in global_vars
        assert "c" in global_vars
