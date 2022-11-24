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
    
class TestInt(unittest.TestCase):

    def test_send_recv(self):
        with MAD() as mad:
            myInt = 4
            mad.send("""
            local myInt = py:recv()
            py:send(myInt+2)
            """)
            mad.send(myInt)
            self.assertEqual(mad.recv(), 6)

class TestFloat(unittest.TestCase):

    def test_send_recv(self):
        with MAD() as mad:
            myFloat = 6.612
            mad.send("""
            local myFloat = py:recv()
            py:send(myFloat + 0.56)
            """)
            mad.send(myFloat)
            self.assertEqual(mad.recv(), 6.612 + 0.56)

class TestComplex(unittest.TestCase):

    def test_send_recv(self):
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
            py:send(3..11..2)
            py:send(MAD.nrange(3.5, 21.4, 12))
            py:send(MAD.nlogrange(1, 20, 20))
            """)
            self.assertEqual(mad.recv(), range(3  , 12  , 2)) #MAD is inclusive, python is exclusive (on stop)
            self.assertTrue (np.allclose(mad.recv(), np.linspace(3.5, 21.4, 12)))
            self.assertTrue (np.allclose(mad.recv(), np.logspace(1, 20, 20)))

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
            mad.send_rng(np.linspace(3.5, 21.4, 14))
            mad.send_lrng(np.logspace(1, 20, 20))
            self.assertEqual(mad.recv(), list(range(4, 12, 1)))
            self.assertTrue (np.allclose(mad.recv(), np.linspace(5.5, 23.4, 14)))
            self.assertTrue (np.allclose(mad.recv(), np.logspace(1, 20, 20)))

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


if __name__ == '__main__':
    unittest.main()