import os
import unittest
import numpy as np
from pymadng import MAD

class TestLoad(unittest.TestCase):
    a = np.arange(1, 21).reshape(4, 5)
    b = np.arange(1, 7).reshape(2, 3)
    c = (np.arange(1, 16) + 1j).reshape(5, 3)

    def test_load(self):
        with MAD() as mad:
            mad.load("MAD", "matrix")
            self.assertTrue(mad.send("py:send(matrix == MAD.matrix)").recv())

            mad.load("MAD.gmath")
            self.assertTrue(mad.send("py:send(sin == MAD.gmath.sin)").recv())
            self.assertTrue(mad.send("py:send(cos == MAD.gmath.cos)").recv())
            self.assertTrue(mad.send("py:send(tan == MAD.gmath.tan)").recv())

            mad.load("MAD.element", "quadrupole", "sextupole", "drift")
            self.assertTrue(
                mad.send("py:send(quadrupole == MAD.element.quadrupole)").recv()
            )
            self.assertTrue(
                mad.send("py:send(sextupole  == MAD.element.sextupole )").recv()
            )
            self.assertTrue(
                mad.send("py:send(drift      == MAD.element.drift     )").recv()
            )

    def test_run_file(self):
        with open("test.mad", "w") as f:
            f.write("""
            local matrix, cmatrix in MAD
            a = matrix(4, 5):seq()
            b = cmatrix(2, 3):seq()
            """)
        with MAD(stdout="/dev/null", redirect_stderr=True) as mad:
            mad.loadfile("test.mad")
            self.assertIsNone(mad.matrix)
            self.assertTrue(np.all(mad.a == self.a))
            self.assertTrue(np.all(mad.b == self.b))
        os.remove("test.mad")

    def test_load_file(self):
        with open("test.mad", "w") as f:
            f.write("""
            local matrix, cmatrix in MAD
            local a = matrix(4, 5):seq()
            local c = cmatrix(5, 3):seq() + 1i
            return {res1 = a * c, res2 = a * c:conj()}
            """)
        with MAD() as mad:
            mad.loadfile("test.mad", "res1", "res2")
            self.assertTrue(np.all(mad.res1 == np.matmul(self.a, self.c)))
            self.assertTrue(np.all(mad.res2 == np.matmul(self.a, self.c.conj())))
        os.remove("test.mad")

    def test_globals(self):
        with MAD() as mad:
            mad.send_vars(a=1, b=2, c=3)
            global_vars = mad.globals()
            self.assertIn("a", global_vars)
            self.assertIn("b", global_vars)
            self.assertIn("c", global_vars)

if __name__ == "__main__":
    unittest.main()