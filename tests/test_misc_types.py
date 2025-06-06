from pathlib import Path
import time
import unittest

import numpy as np

from pymadng import MAD

inputs_folder = Path(__file__).parent / "inputs"
# TODO: Test the following functions:
# - eval
# - error on stdout = something strange
           
class TestNil(unittest.TestCase):

    def test_send_recv(self):
        with MAD() as mad:
            mad.send("""
            local myNil = py:recv()
            py:send(myNil)
            py:send(nil)
            py:send()
            """)
            mad.send(None)
            self.assertIsNone(mad.recv())
            self.assertIsNone(mad.recv())
            self.assertIsNone(mad.recv())

class TestRngs(unittest.TestCase):

    def test_recv(self):
        with MAD() as mad:
            mad.send("""
            irng = MAD.range(3, 11, 2)
            rng = MAD.nrange(3.5, 21.4, 12)
            lrng = MAD.nlogrange(1, 20, 20)
            py:send(irng)
            py:send(rng)
            py:send(lrng)
            py:send(irng:totable(), true)
            py:send(rng:totable(), true)
            py:send(lrng:totable(), true)
            """)

            self.assertEqual(mad.recv(), range(3  , 12  , 2)) #MAD is inclusive, python is exclusive (on stop)
            self.assertTrue (np.allclose(mad.recv(), np.linspace(3.5, 21.4, 12)))
            self.assertTrue (np.allclose(mad.recv(), np.geomspace(1, 20, 20)))
            self.assertEqual(mad.recv(), list(range(3, 12, 2))) #MAD is inclusive, python is exclusive (on stop)
            self.assertTrue (np.allclose(mad.recv(), np.linspace(3.5, 21.4, 12)))
            self.assertTrue (np.allclose(mad.recv(), np.geomspace(1, 20, 20)))

    def test_send(self):
        with MAD() as mad:
            mad.send("""
            irng = py:recv() + 1 
            rng  = py:recv() + 2
            lrng = py:recv()
            py:send(irng:totable(), true)
            py:send(rng:totable(), true)
            py:send(lrng:totable(), true)
            """)
            mad.send(range(3, 10, 1))
            mad.send_range(3.5, 21.4, 14)
            mad.send_logrange(1, 20, 20)
            self.assertEqual(mad.recv(), list(range(4, 12, 1)))
            self.assertTrue (np.allclose(mad.recv(), np.linspace(5.5, 23.4, 14)))
            self.assertTrue (np.allclose(mad.recv(), np.geomspace(1, 20, 20)))

class TestBool(unittest.TestCase):
    
    def test_send_recv(self):
        with MAD() as mad:
            mad.send("""
            bool1 = py:recv()
            bool2 = py:recv()
            py:send(not bool1)
            py:send(not bool2)
            """)
            mad.send(True )
            mad.send(False)
            self.assertEqual(mad.recv(), False)
            self.assertEqual(mad.recv(), True)

class TestMono(unittest.TestCase):

    def test_recv(self):
        with MAD() as mad:
            mad.send("""
            local m = MAD.monomial({1, 2, 3, 4, 6, 20, 100})
            py:send(m)
            local m = MAD.monomial("WZ346oy")
            py:send(m)
            """)
            
            self.assertTrue(np.all(mad.recv() == [1, 2, 3, 4, 6, 20, 100]))
            self.assertTrue(np.all(mad.recv() == [32, 35, 3, 4, 6, 50, 60]))
    
    def test_send_recv(self):
        with MAD() as mad:
            mad.send("""
            local m1 = py:recv()
            local m2 = py:recv()
            py:send(m1 + m2)
            """)
            pym1 = np.random.randint(0, 255, 20, dtype=np.ubyte)
            pym2 = np.random.randint(0, 255, 20, dtype=np.ubyte)
            mad.send(pym1)
            mad.send(pym2)
            mad_res = mad.recv()
            self.assertTrue(np.all(mad_res == pym1+pym2))
            #Check the return is a monomial
            self.assertEqual(mad_res.dtype, np.dtype("ubyte"))

class TestTPSA(unittest.TestCase):

    def test_recv_real(self):
        with MAD() as mad:
            mad.send("""
            local d = MAD.gtpsad(3, 6)
            res = MAD.tpsa(6):set(1,2):set(2, 1)
            res2 = res:copy():set(3, 1)
            res3 = res2:copy():set(4, 1)
            py:send(res:axypbzpc(res2, res3, 1, 2, 3))
            """)
            monomials, coefficients = mad.recv()
            self.assertTrue(np.all(monomials[0] == [0, 0, 0]))
            self.assertTrue(np.all(monomials[1] == [1, 0, 0]))
            self.assertTrue(np.all(monomials[2] == [0, 1, 0]))
            self.assertTrue(np.all(monomials[3] == [0, 0, 1]))
            self.assertTrue(np.all(monomials[4] == [2, 0, 0]))
            self.assertTrue(np.all(monomials[5] == [1, 1, 0]))
            self.assertTrue(np.all(coefficients == [11, 6, 4, 2, 1, 1]))

    def test_recv_cpx(self):
        with MAD() as mad:
            mad.send("""
            local d = MAD.gtpsad(3, 6)
            res = MAD.ctpsa(6):set(1,2+1i):set(2, 1+2i)
            res2 = res:copy():set(3, 1+2i)
            res3 = res2:copy():set(4, 1+2i)
            py:send(res:axypbzpc(res2, res3, 1, 2, 3))
            """)
            monomials, coefficients = mad.recv()
            self.assertTrue(np.all(monomials[0] == [0, 0, 0]))
            self.assertTrue(np.all(monomials[1] == [1, 0, 0]))
            self.assertTrue(np.all(monomials[2] == [0, 1, 0]))
            self.assertTrue(np.all(monomials[3] == [0, 0, 1]))
            self.assertTrue(np.all(monomials[4] == [2, 0, 0]))
            self.assertTrue(np.all(monomials[5] == [1, 1, 0]))
            self.assertTrue(np.all(coefficients == [10+6j, 2+14j, 2+9j, 2+4j, -3+4j, -3+4j]))
    
    # Might be worth checking if the tab can be converted into a tpsa from Monomials. (jgray 2025)
    def test_send_tpsa(self):
        with MAD() as mad:
            mad.send("""
            tab = py:recv()
            index_part = {}
            for i = 1, #tab do
                index_part[i] = tab[i]
            end
            py:send(tab, true)
            py:send(index_part, true)
            """)
            monos = np.asarray([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [2, 0, 0], [1, 1, 0]], dtype=np.uint8)
            coefficients = [11, 6, 4, 2, 1, 1]
            expected_index = ["000", "100", "010", "001", "200", "110"]

            mad.send_tpsa(monos, coefficients)
            
            whole_tab = mad.recv("tab")
            index_part = mad.recv("index_part")
            self.assertEqual(index_part, expected_index)
            for key, value in whole_tab.items():
                if isinstance(key, int):
                    self.assertTrue(value == expected_index[key-1])
                else:
                    idx = expected_index.index(key)
                    self.assertTrue(whole_tab[key] == coefficients[idx])
    
    def test_send_ctpsa(self):
        with MAD() as mad:
            mad.send("""
            tab = py:recv()
            index_part = {}
            for i = 1, #tab do
                index_part[i] = tab[i]
            end
            py:send(tab, true)
            py:send(index_part, true)
            """)
            monos = np.asarray([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [2, 0, 0], [1, 1, 0]], dtype=np.uint8)
            coefficients = [10+6j, 2+14j, 2+9j, 2+4j, -3+4j, -3+4j]
            expected_index = ["000", "100", "010", "001", "200", "110"]
            
            mad.send_cpx_tpsa(monos, coefficients)
            
            whole_tab = mad.recv("tab")
            index_part = mad.recv("index_part")
            self.assertEqual(index_part, expected_index)
            for key, value in whole_tab.items():
                if isinstance(key, int):
                    self.assertTrue(value == expected_index[key-1])
                else:
                    idx = expected_index.index(key)
                    self.assertTrue(whole_tab[key] == coefficients[idx])

    def test_send_recv_damap(self):
        with MAD() as mad:
            mad.send("""
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
            """)
            init = mad.recv()
            mad.send_tpsa(*init)
            final = mad.recv()
            self.assertTrue((init[0] == final[0]).all())
            self.assertTrue((init[1] == final[1]).all())

        
if __name__ == '__main__':
    unittest.main()
