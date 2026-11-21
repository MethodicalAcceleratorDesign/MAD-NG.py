from __future__ import annotations

import numpy as np

from pymadng import MAD

A_MATRIX = np.arange(1, 21).reshape(4, 5)
B_MATRIX = np.arange(1, 7).reshape(2, 3)
C_MATRIX = (np.arange(1, 16) + 1j).reshape(5, 3)


def test_load(tmp_path):
    with MAD() as mad:
        mad.import_module("MAD", "matrix")
        assert mad.send("py:send(matrix == MAD.matrix)").recv()

        mad.import_module("MAD.gmath")
        assert mad.send("py:send(sin == MAD.gmath.sin)").recv()
        assert mad.send("py:send(cos == MAD.gmath.cos)").recv()
        assert mad.send("py:send(tan == MAD.gmath.tan)").recv()

        mad.import_module("MAD.element", "quadrupole", "sextupole", "drift")
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
        mad.import_file(test_file)
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
        mad.import_file(test_file, "res1", "res2")
        assert np.all(mad.res1 == np.matmul(A_MATRIX, C_MATRIX))
        assert np.all(mad.res2 == np.matmul(A_MATRIX, C_MATRIX.conj()))


def test_globals():
    with MAD() as mad:
        mad.send_vars(a=1, b=2, c=3)
        global_vars = mad.globals()
        assert "a" in global_vars
        assert "b" in global_vars
        assert "c" in global_vars


# mad.load / mad.loadfile are MAD-NG's own functions: string arguments are Lua expressions
def test_lua_load_returns_callable():
    with MAD(stdout="/dev/null", redirect_stderr=True) as mad:
        assert mad.load("'return 20 + 22'")().eval() == 42


def test_lua_load_chunk_from_mad_variable():
    with MAD(stdout="/dev/null", redirect_stderr=True) as mad:
        mad.send("src = 'return 5'")
        assert mad.load("src")().eval() == 5


def test_lua_load_default_env_is_global():
    with MAD(stdout="/dev/null", redirect_stderr=True) as mad:
        mad.load("'loaded_global = 5'", "'=chunk'")()
        assert mad.loaded_global == 5


def test_lua_load_syntax_error_returns_nil_and_message():
    with MAD(stdout="/dev/null", redirect_stderr=True) as mad:
        result = mad.load("'return +'", "'=mychunk'").eval()
        assert result[2].startswith("mychunk:1:")


def test_lua_load_mode_binary_rejects_text():
    with MAD(stdout="/dev/null", redirect_stderr=True) as mad:
        result = mad.load("'return 1'", "'=chunk'", "'b'").eval()
        assert result[2] == "attempt to load chunk with wrong mode"


def test_lua_load_env():
    with MAD(stdout="/dev/null", redirect_stderr=True) as mad:
        mad.send("custom_env = {seed = 1}")
        mad.load("'only_in_env = 7'", "'=chunk'", "'t'", "custom_env")()
        assert mad.only_in_env is None
        assert mad.custom_env.only_in_env == 7


def test_lua_loadfile(tmp_path):
    test_file = tmp_path / "test_loadfile.mad"
    test_file.write_text("loadfile_global = 11\nreturn 3\n")
    with MAD(stdout="/dev/null", redirect_stderr=True) as mad:
        chunk = mad.loadfile(f"'{test_file}'")
        assert mad.loadfile_global is None  # compiled, not run
        assert chunk().eval() == 3
        assert mad.loadfile_global == 11


def test_lua_loadfile_missing_returns_nil_and_message():
    with MAD(stdout="/dev/null", redirect_stderr=True) as mad:
        result = mad.loadfile("'does_not_exist.mad'").eval()
        assert "cannot open" in result[2]
