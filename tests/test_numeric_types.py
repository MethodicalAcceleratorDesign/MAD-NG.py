import unittest
import numpy as np
from pymadng import MAD

class TestList(unittest.TestCase):
    def test_send_recv(self):
        with MAD() as mad:
            myList = [[1, 2, 3, 4, 5, 6, 7, 8, 9]] * 2
            mad.send("""
            list = py:recv()
            list[1][1] = 10
            list[2][1] = 10
            py:send(list)
            """)
            mad.send(myList)
            myList[0][0] = 10
            myList[1][0] = 10
            mad_list = mad.recv("list")
            for i, inner_list in enumerate(mad_list):
                for j, val in enumerate(inner_list):
                    self.assertEqual(val, myList[i][j], f"Mismatch at index [{i}][{j}]: {val} != {myList[i][j]}")

    def test_send_recv_wref(self):
        with MAD() as mad:
            python_dict = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, "a": 10, "b": 3, "c": 4}
            mad.send("""
            list = {MAD.object "a" {a = 2}, MAD.object "b" {b = 6}}
            list2 = py:recv()
            py:send(list)
            py:send(list2)
            """).send(python_dict)
            list1 = mad.recv("list")
            list2 = mad.recv("list2")
            self.assertEqual(len(list1), 2)
            
            self.assertEqual(list2.eval().keys(), python_dict.keys())
            self.assertEqual(sorted(list2.eval().values()), sorted(python_dict.values()))

            self.assertEqual(list1[0].a, 2)
            self.assertEqual(list1[1].b, 6)

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

if __name__ == "__main__":
    unittest.main()