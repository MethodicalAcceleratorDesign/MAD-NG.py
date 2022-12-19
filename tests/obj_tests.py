import unittest
from pymadng import MAD
from pymadng.pymadClasses import madReference, madObject, madFunction

import numpy as np
import time

# TODO: test setting variables inside classes
# TODO: test __dir__
class TestObjects(unittest.TestCase):
    
    def test_get(self):
        with MAD() as mad:
            mad.load("element", "quadrupole")
            self.assertEqual(mad.asdfg, None)
            mad.send("""qd = quadrupole {knl={0,  0.25}, l = 1} py:send(qd) """) 
            mad.send("""qf = quadrupole {qd = qd} py:send(qf) """) 
            qd = mad.recv("qd")
            qf = mad.recv("qf")
            self.assertEqual(qd.__name__, "qd")
            self.assertEqual(qd.__parent__, None)
            self.assertEqual(qd.__mad__, mad)
            self.assertEqual(qd.knl, [0, 0.25])
            self.assertEqual(qd.l, 1)
            self.assertRaises(AttributeError, lambda: qd.asdfg)
            self.assertRaises(KeyError, lambda: qd["asdfg"])
            self.assertRaises(IndexError, lambda: qd[1])
            self.assertTrue(isinstance(qf.qd, madReference))
            self.assertEqual(qf.qd.knl, [0, 0.25])
            self.assertEqual(qf.qd.l, 1)
            self.assertEqual(qf.qd, qd)

            mad.send("objList = {qd, qf, qd, qf, qd} py:send(objList)")
            objList = mad.recv("objList")
            for i in range(len(objList)):
                if i % 2 != 0:
                    self.assertTrue(isinstance(objList[i].qd, madReference))
                    self.assertEqual(objList[i].qd.__parent__, f"objList[{i+1}]")
                    self.assertEqual(objList[i].qd.knl, [0, 0.25])
                    self.assertEqual(objList[i].qd.l, 1)
                    self.assertEqual(objList[i].qd, qd)

                else:
                    self.assertEqual(objList[i].knl, [0, 0.25])
                    self.assertEqual(objList[i].l, 1)
                    self.assertEqual(objList[i], qd)
                self.assertEqual(objList[i].__parent__, f"objList")
            
    
    def test_set(self): #Need more?
        with MAD() as mad:
            mad.load("element", "quadrupole")
            mad.send("""qd = quadrupole {knl={0,  0.25}, l = 1} py:send(qd)""") 
            mad["qd2"] = mad.recv("qd")
            self.assertEqual(mad.qd2.__name__, "qd2")
            self.assertEqual(mad.qd2.__parent__, None)
            self.assertEqual(mad.qd2.__mad__, mad)
            self.assertEqual(mad.qd2.knl, [0, 0.25])
            self.assertEqual(mad.qd2.l, 1)
            self.assertEqual(mad.qd2, mad.qd)
    
    def test_call_obj(self):
        with MAD() as mad:
            mad.load("element", ["quadrupole", "sextupole"])
            qd = mad.quadrupole(knl=[0, 0.25], l = 1)
            sd = mad.sextupole(knl=[0, 0.25, 0.5], l = 1)

            mad["qd"] = qd
            self.assertEqual(mad.qd.__name__, "qd")
            self.assertEqual(mad.qd.__parent__, None)
            self.assertEqual(mad.qd.__mad__, mad)
            self.assertEqual(mad.qd.knl, [0, 0.25])
            self.assertEqual(mad.qd.l, 1)

            sdc = sd
            mad["sd"] = sd
            del sd
            self.assertEqual(mad.sd.__name__, "sd")
            self.assertEqual(mad.sd.__parent__, None)
            self.assertEqual(mad.sd.__mad__, mad)
            self.assertEqual(mad.sd.knl, [0, 0.25, 0.5])
            self.assertEqual(mad.sd.l, 1)

            #Reference counting
            qd = mad.quadrupole(knl=[0, 0.3], l = 1)
            self.assertEqual(sdc.__name__, "__last__[2]")
            self.assertEqual(qd.__name__, "__last__[3]")
            self.assertEqual(qd.knl, [0, 0.3])
            qd = mad.quadrupole(knl=[0, 0.25], l = 1)
            self.assertEqual(qd.__name__, "__last__[1]") 

    def test_call_func(self):
        with MAD() as mad:
            mad.load("element", "quadrupole")
            mad["qd"] = mad.quadrupole(knl=[0, 0.25], l = 1)
            mad.qd.select()
            mad["qdSelected"] = mad.qd.is_selected()
            self.assertTrue(mad.qdSelected)
            mad.qd.deselect()
            mad["qdSelected"] = mad.qd.is_selected()
            self.assertFalse(mad.qdSelected)
            mad.qd.set_variables({"l": 2})
            self.assertEqual(mad.qd.l, 2)
    
    def test_mult_rtrn(self):
        with MAD() as mad:
            mad.send("""
            obj = MAD.object "obj" {a = 1, b = 2}
            local function mult_rtrn ()
                obj2 = MAD.object "obj2" {a = 2, b = 3}
                return obj, obj, obj, obj2
            end
            last_rtn = __mklast__(mult_rtrn())
            lastobj = __mklast__(obj)
            notLast = {mult_rtrn()}
            """)
            mad["o11", "o12", "o13", "o2"] = madReference("last_rtn", mad)
            mad["p11", "p12", "p13", "p2"] = madReference("notLast", mad)
            mad["objCpy"] = madReference("lastobj", mad) #Test single object in __mklast__
            self.assertEqual(mad.o11.a, 1)
            self.assertEqual(mad.o11.b, 2)
            self.assertEqual(mad.o12.a, 1)
            self.assertEqual(mad.o12.b, 2)
            self.assertEqual(mad.o13.a, 1)
            self.assertEqual(mad.o13.b, 2)
            self.assertEqual(mad.o2.a , 2)
            self.assertEqual(mad.o2.b , 3)
            self.assertEqual(mad.p11.a, 1)
            self.assertEqual(mad.p11.b, 2)
            self.assertEqual(mad.p12.a, 1)
            self.assertEqual(mad.p12.b, 2)
            self.assertEqual(mad.p13.a, 1)
            self.assertEqual(mad.p13.b, 2)
            self.assertEqual(mad.p2.a , 2)
            self.assertEqual(mad.p2.b , 3)
            self.assertEqual(mad.objCpy, mad.obj)


    def test_matrix(self):
        with MAD() as mad:
            mad.load("MAD", "matrix")
            pyMat = np.arange(1, 101).reshape((10, 10))

            mad["mat"] = mad.matrix(10).seq(2) + 2 
            self.assertTrue(np.all(mad.mat == pyMat + 4))

            mad["mat"] = mad.matrix(10).seq() / 3 
            self.assertTrue(np.allclose(mad.mat, pyMat / 3))

            mad["mat"] = mad.matrix(10).seq() * 4 
            self.assertTrue(np.all(mad.mat == pyMat * 4))

            mad["mat"] = mad.matrix(10).seq() ** 3 
            self.assertTrue(np.all(mad.mat == np.linalg.matrix_power(pyMat, 3)))

            mad["mat"] = mad.matrix(10).seq() + 2 / 3 * 4 ** 3 #bidmas
            self.assertTrue(np.all(mad.mat == pyMat + 2 / 3 * 4 ** 3))

            #conversions
            self.assertTrue(np.all(np.array(mad.MAD.matrix(10).seq()) == np.arange(1, 101)))
            self.assertTrue(np.all(list(mad.MAD.matrix(10).seq()) == np.arange(1, 101)))
            self.assertTrue(np.all(mad.MAD.matrix(10).seq().eval() == pyMat))
            self.assertEqual(np.sin(1), mad.math.sin(1).eval())
            self.assertEqual(np.cos(0.5), mad.math.cos(0.5).eval())

            # temp vars
            res = (((mad.matrix(3).seq().emul(2) * mad.matrix(3).seq(3) + 3) * 2 + mad.matrix(3).seq(2)) - mad.matrix(3).seq(4)).eval()
            np_mat = np.arange(9).reshape((3,3)) + 1
            exp = (((np.matmul((np_mat * 2), (np_mat+3)) + 3) * 2 + (np_mat+2)) - (np_mat+4))
            self.assertTrue(np.all(exp == res))


    def test_args(self):
        with MAD() as mad:
            mad.load("MAD", ["matrix", "cmatrix"])
            mad["m1"] = mad.matrix(3).seq()
            mad["m2"] = mad.matrix(3).eye(2).mul(mad.m1)
            mad["m3"] = mad.matrix(3).seq().emul(mad.m1)
            mad["cm1"] = mad.cmatrix(3).seq(1j).map([1, 5, 9], "\mn, n -> mn - 1i")
            self.assertTrue(np.all(mad.m2 == mad.m1 * 2))
            self.assertTrue(np.all(mad.m3 == (mad.m1 * mad.m1)))
            self.assertTrue(np.all(mad.cm1 == mad.m1 + 1j - np.eye(3)*1j))
            #Add bool

    def test_kwargs(self):
        with MAD() as mad:
            mad.load("element", "sextupole")
            mad["m1"] = mad.MAD.matrix(3).seq()
            sd = mad.sextupole(knl=[0, 0.25j, 1 + 1j], l = 1, alist = [1, 2, 3, 5], abool = True, opposite = False, mat = mad.m1)
            self.assertEqual(sd.knl, [0, 0.25j, 1 + 1j])
            self.assertEqual(sd.l, 1)
            self.assertEqual(sd.alist, [1, 2, 3, 5])
            self.assertEqual(sd.abool, True)
            self.assertEqual(sd.opposite, False)
            self.assertTrue(np.all(sd.mat == np.arange(9).reshape((3, 3)) + 1))


    def test_benchmark(self):
        with MAD() as mad:
            mad.load("element", "quadrupole")
            mad.send("""
            qd = quadrupole {knl={0,  0.25}, l = 1}
            py:send(qd)
            """) 
            qd = mad.recv("qd")
            start = time.time()
            for i in range(int(1e5)):
                mad["qf"] = qd
            mad.qd
            total = time.time() - start
            self.assertAlmostEqual(total, 0.5, None, None, 0.5)

if __name__ == '__main__':
    unittest.main()