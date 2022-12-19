import unittest
from pymadng import MAD
import numpy as np

class TestExecution(unittest.TestCase):

    def test_recv_and_exec(self):
        with MAD() as mad:
            mad.send("""py:send([==[mad.send('''py:send([=[mad.send("py:send([[a = 100/2]])")]=])''')]==])""")
            mad.recv_and_exec()
            mad.recv_and_exec()
            a = mad.recv_and_exec()["a"]
            self.assertEqual(a, 50)

    def test_err(self):
        with MAD() as mad:
            mad.send("py:__err(true)")
            mad.send("1+1") #Load error
            self.assertRaises(RuntimeError, mad.recv)
            mad.send("py:__err(true)")
            mad.send("print(nil/2)") #Runtime error
            self.assertRaises(RuntimeError, mad.recv)

class TestStrings(unittest.TestCase):

    def test_recv(self):
        with MAD() as mad:
            mad.send("py:send('hi')")
            mad.send("""py:send([[Multiline string should work

Like So.]])""")
            self.assertEqual(mad.recv(), 'hi')
            self.assertEqual(mad.recv(), 'Multiline string should work\n\nLike So.')

    def test_send(self):
        with MAD() as mad:
            initString = "asdfghjkl;"
            mad.send("str = py:recv(); py:send(str .. str)")
            mad.send(initString)
            self.assertEqual(mad.recv(), initString * 2)
            # mad.send("py:recv()")
            mad.send("""py:send([[Multiline string should work

Like So.]])""")
            self.assertEqual(mad.recv(), 'Multiline string should work\n\nLike So.')

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

class TestList(unittest.TestCase):
    
    def test_send_recv(self):
        with MAD() as mad:
            myList = [[1, 2, 3, 4, 5, 6, 7, 8, 9]] * 2
            mad.send("""
            local list = py:recv()
            list[1][1] = 10
            list[2][1] = 10
            py:send(list)
            """)
            mad.send(myList)
            myList[0][0] = 10
            myList[1][0] = 10
            self.assertEqual(mad.recv(), myList)

    def test_send_recv_wref(self):
        with MAD() as mad:
            mad.send("""
            list = {MAD.object "a" {a = 2}, MAD.object "b" {b = 2}}
            list2 = {1, 2, 3, 4, 5, a = 10, b = 3, c = 4}
            py:send(list)
            py:send(list2)
            """)
            list1 = mad.recv("list")
            list2 = mad.recv("list2")
            self.assertEqual(len(list1), 2)
            self.assertEqual(list2[0], [1, 2, 3, 4, 5])
            self.assertEqual(list2[1].a, 10)
            self.assertEqual(list2[1].b, 3)
            self.assertEqual(list2[1].c, 4)
            self.assertEqual(list1[0].a, 2)
            self.assertEqual(list1[1].b, 2)

    
class TestNums(unittest.TestCase):

    def test_send_recv_int(self):
        with MAD() as mad:
            myInt = 4
            mad.send("""
            local myInt = py:recv()
            py:send(myInt+2)
            """)
            mad.send(myInt)
            self.assertEqual(mad.recv(), 6)

    def test_send_recv_num(self):
        with MAD() as mad:
            myFloat = 6.612
            mad.send("""
            local myFloat = py:recv()
            py:send(myFloat + 0.56)
            """)
            mad.send(myFloat)
            self.assertEqual(mad.recv(), 6.612 + 0.56)

    def test_send_recv_cpx(self):
        with MAD() as mad:
            myCpx = 6.612 + 4j
            mad.send("""
            local myCpx = py:recv()
            py:send(myCpx + 0.5i)
            """)
            mad.send(myCpx)
            self.assertEqual(mad.recv(), 6.612 + 4.5j)

class TestRngs(unittest.TestCase):

    def test_recv(self):
        with MAD() as mad:
            mad.send("""
            irng = 3..11..2
            rng = MAD.nrange(3.5, 21.4, 12)
            lrng = MAD.nlogrange(1, 20, 20)
            py:send(irng)
            py:send(rng)
            py:send(lrng)
            py:send(irng:totable())
            py:send(rng:totable())
            py:send(lrng:totable())
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
            py:send(irng:totable())
            py:send(rng:totable())
            py:send(lrng:totable())
            """)
            mad.send(range(3, 10, 1))
            mad.send_rng(3.5, 21.4, 14)
            mad.send_lrng(1, 20, 20)
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
    
    def test_send_tpsa(self):
        with MAD() as mad:
            mad.send("""
            local tab = py:recv()
            py:send(tab)
            """)
            monos = np.asarray([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [2, 0, 0], [1, 1, 0]], dtype=np.uint8)
            coefficients = [11, 6, 4, 2, 1, 1]
            mad.send_tpsa(monos, coefficients)
            self.assertTrue(mad.recv("tab"), ["000", "100", "010", "001", "200", "110"].extend(coefficients)) #intentional?
    
    def test_send_ctpsa(self):
        with MAD() as mad:
            mad.send("""
            local tab = py:recv()
            py:send(tab)
            """)
            monos = np.asarray([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [2, 0, 0], [1, 1, 0]], dtype=np.uint8)
            coefficients = [10+6j, 2+14j, 2+9j, 2+4j, -3+4j, -3+4j]
            mad.send_ctpsa(monos, coefficients)
            self.assertTrue(mad.recv("tab"), ["000", "100", "010", "001", "200", "110"].extend(coefficients)) #intentional?

    def test_send_recv_damap(self):
        with MAD() as mad:
            mad.send("""
            local sin in MAD.gmath
            MAD.gtpsad(6, 5)
            local M = MAD.damap {xy = 5}
            M.x  = 1 ; M.y  = 2 ; M.t  = 3
            M.px = 2 ; M.py = 1 ; M.pt = 1
            res = sin(M.x) * sin(M.y)
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