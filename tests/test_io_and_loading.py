import unittest
from pathlib import Path

import numpy as np

from pymadng import MAD


class TestLoad(unittest.TestCase):
    a = np.arange(1, 21).reshape(4, 5)
    b = np.arange(1, 7).reshape(2, 3)
    c = (np.arange(1, 16) + 1j).reshape(5, 3)

    def test_load(self):
        with MAD() as mad:
            mad.import_module("MAD", "matrix")
            self.assertTrue(mad.send("py:send(matrix == MAD.matrix)").recv())

            mad.import_module("MAD.gmath")
            self.assertTrue(mad.send("py:send(sin == MAD.gmath.sin)").recv())
            self.assertTrue(mad.send("py:send(cos == MAD.gmath.cos)").recv())
            self.assertTrue(mad.send("py:send(tan == MAD.gmath.tan)").recv())

            mad.import_module("MAD.element", "quadrupole", "sextupole", "drift")
            self.assertTrue(mad.send("py:send(quadrupole == MAD.element.quadrupole)").recv())
            self.assertTrue(mad.send("py:send(sextupole  == MAD.element.sextupole )").recv())
            self.assertTrue(mad.send("py:send(drift      == MAD.element.drift     )").recv())

        test_file = Path("test.mad")
        with test_file.open("w") as f:
            f.write("""
            local matrix, cmatrix in MAD
            a = matrix(4, 5):seq()
            b = cmatrix(2, 3):seq()
            """)
        with MAD(stdout="/dev/null", redirect_stderr=True) as mad:
            mad.import_file("test.mad")
            self.assertIsNone(mad.matrix)
            self.assertTrue(np.all(mad.a == self.a))
            self.assertTrue(np.all(mad.b == self.b))
        test_file.unlink()
        with test_file.open("w") as f:
            f.write("""
            local matrix, cmatrix in MAD
            local a = matrix(4, 5):seq()
            local c = cmatrix(5, 3):seq() + 1i
            return {res1 = a * c, res2 = a * c:conj()}
            """)
        with MAD() as mad:
            mad.import_file("test.mad", "res1", "res2")
            self.assertTrue(np.all(mad.res1 == np.matmul(self.a, self.c)))
            self.assertTrue(np.all(mad.res2 == np.matmul(self.a, self.c.conj())))
        test_file.unlink()

    def test_globals(self):
        with MAD() as mad:
            mad.send_vars(a=1, b=2, c=3)
            global_vars = mad.globals()
            self.assertIn("a", global_vars)
            self.assertIn("b", global_vars)
            self.assertIn("c", global_vars)


class TestLuaLoad(unittest.TestCase):
    """``MAD.load`` and ``MAD.loadfile`` follow Lua: ``load (ld [, source [, mode [, env]]])``."""

    def test_load_chunk_returns_callable(self):
        with MAD(stdout="/dev/null", redirect_stderr=True) as mad:
            chunk = mad.load("return 20 + 22")
            self.assertEqual(chunk().eval(), 42)

    def test_load_default_env_is_global(self):
        with MAD(stdout="/dev/null", redirect_stderr=True) as mad:
            mad.load("loaded_global = 5", "=chunk")()
            self.assertEqual(mad.loaded_global, 5)

    def test_load_syntax_error_returns_nil_and_message(self):
        with MAD(stdout="/dev/null", redirect_stderr=True) as mad:
            chunk, msg = mad.load("return +", "=mychunk")
            self.assertIsNone(chunk)
            self.assertTrue(msg.startswith("mychunk:1:"), msg)

    def test_load_mode_binary_rejects_text(self):
        with MAD(stdout="/dev/null", redirect_stderr=True) as mad:
            chunk, msg = mad.load("return 1", "=chunk", "b")
            self.assertIsNone(chunk)
            self.assertEqual(msg, "attempt to load chunk with wrong mode")

    def test_load_env(self):
        with MAD(stdout="/dev/null", redirect_stderr=True) as mad:
            mad.send("custom_env = {seed = 1}")
            mad.load("only_in_env = 7", "=chunk", "t", mad.custom_env)()
            self.assertIsNone(mad.only_in_env)
            self.assertEqual(mad.custom_env.only_in_env, 7)

    def test_loadfile(self):
        test_file = Path("test_loadfile.mad")
        test_file.write_text("loadfile_global = 11\nreturn 3\n")
        try:
            with MAD(stdout="/dev/null", redirect_stderr=True) as mad:
                chunk = mad.loadfile(test_file)
                self.assertIsNone(mad.loadfile_global)  # compiled, not run
                self.assertEqual(chunk().eval(), 3)
                self.assertEqual(mad.loadfile_global, 11)
        finally:
            test_file.unlink()

    def test_loadfile_missing_returns_nil_and_message(self):
        with MAD(stdout="/dev/null", redirect_stderr=True) as mad:
            chunk, msg = mad.loadfile("does_not_exist.mad")
            self.assertIsNone(chunk)
            self.assertIn("cannot open", msg)


if __name__ == "__main__":
    unittest.main()
