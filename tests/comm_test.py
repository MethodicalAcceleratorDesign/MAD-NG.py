from pathlib import Path
import time
import unittest

import numpy as np

from pymadng import MAD

inputs_folder = Path(__file__).parent / "inputs"
# TODO: Test the following functions:
# - eval
# - error on stdout = something strange

class TestExecution(unittest.TestCase):

    def test_recv_and_exec(self):
        with MAD() as mad:
            mad.send("""py:send([==[mad.send('''py:send([=[mad.send("py:send([[a = 100/2]])")]=])''')]==])""")
            mad.recv_and_exec()
            mad.recv_and_exec()
            a = mad.recv_and_exec()["a"]
            self.assertEqual(a, 50)

    def test_err(self):
        with MAD(stdout="/dev/null", redirect_sterr=True) as mad:
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
            self.assertEqual(mad.receive(), 'Multiline string should work\n\nLike So.')

    def test_send(self):
        with MAD() as mad:
            initString = "asdfghjkl;"
            mad.send("str = py:recv(); py:send(str .. str)")
            mad.send(initString)
            self.assertEqual(mad.recv(), initString * 2)
            mad.send("str2 = py:recv(); py:send(str2 .. str2)")
            initString = """Py Multiline string should work

Like So.]])"""
            mad.send(initString)
            self.assertEqual(mad.recv(), initString * 2)

    def test_protected_send(self):
        with MAD(stdout="/dev/null", redirect_sterr=True, raise_on_madng_error=False) as mad:
            mad.send("py:send('hello world'); a = nil/2")
            self.assertEqual(mad.recv(), "hello world") # python should not crash
            mad.send("py:send(1)")
            self.assertEqual(mad.recv(), 1) # Check that the error did not affect the pipe
            
            mad.protected_send("a = nil/2")
            self.assertRaises(RuntimeError, mad.recv)   # python should receive an error
            
            mad.psend("a = nil/2")
            self.assertRaises(RuntimeError, mad.recv)
           

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
            self.assertEqual([x for x in list2], [1, 2, 3, 4, 5])
            self.assertEqual(list2["a"], 10)
            self.assertEqual(list2["b"], 3)
            self.assertEqual(list2["c"], 4)
            self.assertEqual(list1[0].a, 2)
            self.assertEqual(list1[1].b, 2)

    
class TestNums(unittest.TestCase):

    eps = 2**-52
    tiny = 2**-1022
    huge = 2**1023
    flt_lst = [0, tiny, 2**-64, 2**-63, 2**-53, eps, 2**-52, 2*eps, 2**-32, 2**-31, 1e-9,
                0.1-eps, 0.1, 0.1+eps, 0.5, 0.7-eps, 0.7, 0.7+eps, 1-eps, 1, 1+eps,
                1.1, 1.7, 2, 10, 1e2, 1e3, 1e6, 1e9, 2**31, 2**32, 2**52, 2**53,
                2**63, 2**64, huge]

    def test_send_recv_int(self):
        with MAD() as mad:
            int_lst = [0, 1, 2, 10, 1e2, 1e3, 1e6, 1e9, 2**31-1]
            for i in range(len(int_lst)):
                mad.send("""
                local is_integer in MAD.typeid
                local num = py:recv()
                py:send( num)
                py:send(-num)
                py:send(is_integer(num))
                """)
                mad.send(int_lst[i])
                recv_num = mad.recv()
                self.assertEqual(recv_num, int_lst[i])
                self.assertTrue(isinstance(recv_num, np.int32))
                recv_num = mad.recv()
                self.assertEqual(recv_num, -int_lst[i])
                self.assertTrue(isinstance(recv_num, np.int32))
                self.assertTrue(mad.recv())

    def test_send_recv_num(self):
        with MAD() as mad:
            for i in range(len(self.flt_lst)):
                mad.send("""
                local num = py:recv()
                local negative = py:recv()
                py:send(num)
                py:send(negative)
                py:send(num * 1.61)
                """)
                mad.send(self.flt_lst[i])
                mad.send(-self.flt_lst[i])
                self.assertEqual(mad.recv(),  self.flt_lst[i]) #Check individual floats
                self.assertEqual(mad.recv(), -self.flt_lst[i]) #Check negation
                self.assertEqual(mad.recv(),  self.flt_lst[i] * 1.61) #Check manipulation

    def test_send_recv_cpx(self):
        with MAD() as mad:
            for i in range(len(self.flt_lst)):
                for j in range(len(self.flt_lst)):
                    mad.send("""
                    local my_cpx = py:recv()
                    py:send(my_cpx)
                    py:send(-my_cpx)
                    py:send(my_cpx * 1.31i)
                    """)
                    my_cpx = self.flt_lst[i] + 1j * self.flt_lst[j]
                    mad.send(my_cpx)
                    self.assertEqual(mad.recv(),  my_cpx)
                    self.assertEqual(mad.recv(), -my_cpx)
                    self.assertEqual(mad.recv(),  my_cpx * 1.31j)

class TestMatrices(unittest.TestCase):

    def test_send_recv_imat(self):
        with MAD() as mad:
            mad.send("""
            local imat = py:recv()
            py:send(imat)
            py:send(MAD.imatrix(3, 5):seq())
            """)
            imat = np.random.randint(0, 255, (5, 5), dtype=np.int32)
            mad.send(imat)
            self.assertTrue(np.all(mad.recv() == imat))
            self.assertTrue(np.all(mad.recv() == np.arange(1, 16).reshape(3, 5)))

    def test_send_recv_mat(self):
        with MAD() as mad:
            mad.send("""
            local mat = py:recv()
            py:send(mat)
            py:send(MAD.matrix(3, 5):seq() / 2)
            """)
            mat = np.arange(1, 25).reshape(4, 6) / 4
            mad.send(mat)
            self.assertTrue(np.all(mad.recv() == mat))
            self.assertTrue(np.all(mad.recv() == np.arange(1, 16).reshape(3, 5) / 2))

    def test_send_recv_cmat(self):
        with MAD() as mad:
            mad.send("""
            local cmat = py:recv()
            py:send(cmat)
            py:send(MAD.cmatrix(3, 5):seq() / 2i)
            """)
            cmat = np.arange(1, 25).reshape(4, 6) / 4 + 1j * np.arange(1, 25).reshape(4, 6) / 4
            mad.send(cmat)
            self.assertTrue(np.all(mad.recv() == cmat))
            self.assertTrue(np.all(mad.recv() == (np.arange(1, 16).reshape(3, 5) / 2j)))

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
    
    def test_send_tpsa(self):
        with MAD() as mad:
            mad.send("""
            tab = py:recv()
            py:send(tab)
            """)
            monos = np.asarray([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [2, 0, 0], [1, 1, 0]], dtype=np.uint8)
            coefficients = [11, 6, 4, 2, 1, 1]
            mad.send_tpsa(monos, coefficients)
            self.assertTrue(mad.recv("tab"), ["000", "100", "010", "001", "200", "110"].extend(coefficients)) #intentional?
    
    def test_send_ctpsa(self):
        with MAD() as mad:
            mad.send("""
            tab = py:recv()
            py:send(tab)
            """)
            monos = np.asarray([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [2, 0, 0], [1, 1, 0]], dtype=np.uint8)
            coefficients = [10+6j, 2+14j, 2+9j, 2+4j, -3+4j, -3+4j]
            mad.send_cpx_tpsa(monos, coefficients)
            self.assertTrue(mad.recv("tab"), ["000", "100", "010", "001", "200", "110"].extend(coefficients)) #intentional?

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

        
class TestOutput(unittest.TestCase):

    def test_print(self):
        with MAD() as mad:
            mad.send("py:send('hello world')")
            self.assertEqual(mad.recv(), "hello world") # Check printing does not affect pipe

class TestDebug(unittest.TestCase):
    test_log1 = inputs_folder/"test.log"
    def test_logfile(self):
        example_log = inputs_folder/"example.log"
        test_log2 = inputs_folder/"test2.log"

        with MAD(stdout=self.test_log1, debug=True, raise_on_madng_error=False) as mad: 
            pass
        time.sleep(0.1) #Wait for file to be written
        with open(self.test_log1, "r") as f:
            with open(example_log, "r") as f2:
                self.assertEqual(f.read(), f2.read())
        
        with MAD(stdout=test_log2, debug=True) as mad:
            mad.send("!This is a line that does nothing")
            mad.send("print('hello world')")

        with open(test_log2) as f:
            text = f.read()
            self.assertTrue("[!This is a line that does nothing]" in text)
            self.assertTrue("hello world\n" in text)
            self.assertTrue("[print('hello world')]" in text)

        with MAD(stdout=test_log2, debug=False) as mad:
            mad.send("!This is a line that does nothing")
            mad.send("print('hello world')")
        
        with open(test_log2) as f:
            self.assertEqual(f.read(), "hello world\n")

        self.test_log1.unlink()
        test_log2.unlink()

    def test_err(self):
        # Run debug without stderr redirection
        with open(self.test_log1, "w") as f:
            with MAD(debug=True, stdout=f, raise_on_madng_error=False) as mad:
                mad.psend("a = nil/2")
                # receive the error before closing the pipe
                self.assertRaises(RuntimeError, mad.recv)
        with open(self.test_log1) as f:
            # Check command was sent
            file_text = f.read()
            self.assertTrue("[py:__err(true); a = nil/2; py:__err(false);]" in file_text)
            # Check error was not in stdout
            self.assertFalse("***pymad.run:" in file_text)

        # Run debug with stderr redirection
        with MAD(stdout=self.test_log1, redirect_sterr=True) as mad:
            mad.psend("a = nil/2")
            # receive the error before closing the pipe
            self.assertRaises(RuntimeError, mad.recv) 
        with open(self.test_log1) as f:
            # Check command was sent
            file_text = f.read()
            # Check error was in stdout
            self.assertEqual("***pymad.run:", file_text[:13])
        self.test_log1.unlink()




if __name__ == '__main__':
    unittest.main()
