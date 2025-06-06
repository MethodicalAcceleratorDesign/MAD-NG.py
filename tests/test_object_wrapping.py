import math
import os
import sys
import unittest

import numpy as np
import pandas as pd
import tfs

from pymadng import MAD
from pymadng.madp_classes import high_level_mad_ref, mad_high_level_last_ref

# TODO: Test the following functions:
# - __str__ on mad references (low priority)

class TestGetSet(unittest.TestCase):
    def test_get(self):
        with MAD(stdout="/dev/null", redirect_stderr=True) as mad:
            mad.load("element", "quadrupole")
            self.assertEqual(mad.asdfg, None)
            mad.send("""qd = quadrupole {knl={0,  0.25}, l = 1}""")
            mad.send("""qf = quadrupole {qd = qd}""")
            qd, qf = mad["qd", "qf"]
            self.assertEqual(qd._name, "qd")
            self.assertEqual(qd._parent, None)
            self.assertEqual(qd._mad, mad._MAD__process)
            self.assertEqual(qd.knl.eval(), [0, 0.25])
            self.assertEqual(qd.l, 1)
            self.assertRaises(AttributeError, lambda: qd.asdfg)
            self.assertRaises(KeyError, lambda: qd["asdfg"])
            self.assertRaises(IndexError, lambda: qd[1])
            self.assertTrue(isinstance(qf.qd, high_level_mad_ref))
            self.assertEqual(qf.qd.knl.eval(), [0, 0.25])
            self.assertEqual(qf.qd.l, 1)
            self.assertEqual(qf.qd, qd)

            mad.send("objList = {qd, qf, qd, qf, qd} py:send(objList)")
            objList = mad.recv("objList")
            for i in range(len(objList)):
                if i % 2 != 0:
                    self.assertTrue(isinstance(objList[i].qd, high_level_mad_ref))
                    self.assertEqual(objList[i].qd._parent, f"objList[{i + 1}]")
                    self.assertEqual(objList[i].qd.knl.eval(), [0, 0.25])
                    self.assertEqual(objList[i].qd.l, 1)
                    self.assertEqual(objList[i].qd, qd)

                else:
                    self.assertEqual(objList[i].knl.eval(), [0, 0.25])
                    self.assertEqual(objList[i].l, 1)
                    self.assertEqual(objList[i], qd)
                self.assertEqual(objList[i]._parent, "objList")

    def test_set(self):  # Need more?
        with MAD() as mad:
            mad.load("element", "quadrupole")
            mad.send("""qd = quadrupole {knl={0,  0.25}, l = 1} py:send(qd)""")
            mad["qd2"] = mad.recv("qd")
            self.assertEqual(mad.qd2._name, "qd2")
            self.assertEqual(mad.qd2._parent, None)
            self.assertEqual(mad.qd2._mad, mad._MAD__process)
            self.assertEqual(mad.qd2.knl.eval(), [0, 0.25])
            self.assertEqual(mad.qd2.l, 1)
            self.assertEqual(mad.qd2, mad.qd)
            mad["a", "b"] = mad.MAD.gmath.reim(9.75 + 1.5j)
            self.assertEqual(mad.a, 9.75)
            self.assertEqual(mad.b, 1.5)
            mad.send("f = \\-> (1, 2, 3, 9, 8, 7)")
            mad["r1", "r2", "r3", "r4", "r5", "r6"] = mad.f()
            self.assertEqual(mad.r1, 1)
            self.assertEqual(mad.r2, 2)
            self.assertEqual(mad.r3, 3)
            self.assertEqual(mad.r4, 9)
            self.assertEqual(mad.r5, 8)
            self.assertEqual(mad.r6, 7)

    def test_send_vars(self):
        with MAD() as mad:
            mad.send_vars(a=1, b=2.5, c="test", d=[1, 2, 3])
            self.assertEqual(mad.a, 1)
            self.assertEqual(mad.b, 2.5)
            self.assertEqual(mad.c, "test")
            self.assertEqual(mad.d.eval(), [1, 2, 3])

    def test_recv_vars(self):
        with MAD() as mad:
            mad.send_vars(a=1, b=2.5, c="test", d=[1, 2, 3])
            a, b, c, d = mad.recv_vars("a", "b", "c", "d")
            self.assertEqual(a, 1)
            self.assertEqual(b, 2.5)
            self.assertEqual(c, "test")
            self.assertEqual(d.eval(), [1, 2, 3])

    def test_quote_strings(self):
        with MAD() as mad:
            self.assertEqual(mad.quote_strings("test"), "'test'")
            self.assertEqual(mad.quote_strings(["a", "b", "c"]), ["'a'", "'b'", "'c'"])

    def test_create_deferred_expression(self):
        with MAD() as mad:
            deferred = mad.create_deferred_expression(a="x + y", b="x * y")
            mad.send_vars(x=2, y=3)
            self.assertEqual(deferred.a, 5)  # x + y = 2 + 3
            self.assertEqual(deferred.b, 6)  # x * y = 2 * 3
            mad.send_vars(x=5, y=10)
            self.assertEqual(deferred.a, 15)  # x + y = 5 + 10
            self.assertEqual(deferred.b, 50)

            mad["deferred"] = mad.create_deferred_expression(a="x - y", b="x / y")
            mad.send_vars(x=10, y=2)
            self.assertEqual(mad.deferred.a, 8)  # x - y = 10 - 2
            self.assertEqual(mad.deferred.b, 5)  # x / y = 10 / 2


class TestObjFun(unittest.TestCase):
    def test_call_obj(self):
        with MAD() as mad:
            mad.load("element", "quadrupole", "sextupole")
            qd = mad.quadrupole(knl=[0, 0.25], l=1)
            sd = mad.sextupole(knl=[0, 0.25, 0.5], l=1)

            mad["qd"] = qd
            self.assertEqual(mad.qd._name, "qd")
            self.assertEqual(mad.qd._parent, None)
            self.assertEqual(mad.qd._mad, mad._MAD__process)
            self.assertEqual(mad.qd.knl.eval(), [0, 0.25])
            self.assertEqual(mad.qd.l, 1)

            sdc = sd
            mad["sd"] = sd
            del sd
            self.assertEqual(mad.sd._name, "sd")
            self.assertEqual(mad.sd._parent, None)
            self.assertEqual(mad.sd._mad, mad._MAD__process)
            self.assertEqual(mad.sd.knl.eval(), [0, 0.25, 0.5])
            self.assertEqual(mad.sd.l, 1)

            # Reference counting
            qd = mad.quadrupole(knl=[0, 0.3], l=1)
            self.assertEqual(sdc._name, "_last[2]")
            self.assertEqual(qd._name, "_last[3]")
            self.assertEqual(qd.knl.eval(), [0, 0.3])
            qd = mad.quadrupole(knl=[0, 0.25], l=1)
            self.assertEqual(qd._name, "_last[1]")

    def test_call_last(self):
        with MAD() as mad:
            mad.send("func_test = \\a-> \\b-> \\c-> a+b*c")
            self.assertRaises(TypeError, lambda: mad.MAD())
            self.assertEqual(mad.func_test(1)(2)(3), 7)

    def test_call_fail(self):
        with MAD(stdout="/dev/null", redirect_stderr=True) as mad:
            mad.send("func_test = \\a-> \\b-> \\c-> 'a'+b")
            mad.func_test(1)(2)(3)
            self.assertRaises(RuntimeError, lambda: mad.recv())
            self.assertRaises(
                RuntimeError, lambda: mad.mtable.read("'abad.tfs'").eval()
            )

    def test_call_func(self):
        with MAD() as mad:
            mad.load("element", "quadrupole")
            mad["qd"] = mad.quadrupole(knl=[0, 0.25], l=1)
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

            mad["o11", "o12", "o13", "o2"] = mad._MAD__get_mad_ref("last_rtn")
            mad["p11", "p12", "p13", "p2"] = mad._MAD__get_mad_ref("notLast")
            mad["objCpy"] = mad._MAD__get_mad_ref(
                "lastobj"
            )  # Test single object in __mklast__
            self.assertEqual(mad.o11.a, 1)
            self.assertEqual(mad.o11.b, 2)
            self.assertEqual(mad.o12.a, 1)
            self.assertEqual(mad.o12.b, 2)
            self.assertEqual(mad.o13.a, 1)
            self.assertEqual(mad.o13.b, 2)
            self.assertEqual(mad.o2.a, 2)
            self.assertEqual(mad.o2.b, 3)
            self.assertEqual(mad.p11.a, 1)
            self.assertEqual(mad.p11.b, 2)
            self.assertEqual(mad.p12.a, 1)
            self.assertEqual(mad.p12.b, 2)
            self.assertEqual(mad.p13.a, 1)
            self.assertEqual(mad.p13.b, 2)
            self.assertEqual(mad.p2.a, 2)
            self.assertEqual(mad.p2.b, 3)
            self.assertEqual(mad.objCpy, mad.obj)

    def test_MADX(self):
        from pymadng import MAD

        mad = MAD()
        self.assertEqual(mad.MADX.abs(-1), 1)
        self.assertEqual(mad.MADX.ceil(1.2), 2)

        self.assertEqual(mad.MAD.MADX.abs(-1), 1)
        self.assertEqual(mad.MAD.MADX.ceil(1.2), 2)

        self.assertEqual(mad.MADX.MAD.MADX.abs(-1), 1)
        self.assertEqual(mad.MADX.MAD.MADX.ceil(1.2), 2)

        with open("test.seq", "w") as f:
            f.write("""
      qd: quadrupole, l=1, knl:={0, 0.25};
      """)
        mad.MADX.load("'test.seq'")
        self.assertEqual(mad.MADX.qd.l, 1)
        self.assertEqual(mad.MADX.qd.knl.eval(), [0, 0.25])
        os.remove("test.seq")

    def test_evaluate_in_madx_environment(self):
        with MAD() as mad:
            madx_code = """
            qd = quadrupole {l=1, knl:={0, 0.25}}
            """
            mad.evaluate_in_madx_environment(madx_code)
            self.assertEqual(mad.MADX.qd.l, 1)
            self.assertEqual(mad.MADX.qd.knl.eval(), [0, 0.25])


class TestOps(unittest.TestCase):
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

            mad["mat"] = mad.matrix(10).seq() + 2 / 3 * 4**3  # bidmas
            self.assertTrue(np.all(mad.mat == pyMat + 2 / 3 * 4**3))

            # conversions
            self.assertTrue(
                np.all(np.array(mad.MAD.matrix(10).seq()) == np.arange(1, 101))
            )
            self.assertTrue(np.all(list(mad.MAD.matrix(10).seq()) == np.arange(1, 101)))
            self.assertTrue(np.all(mad.MAD.matrix(10).seq().eval() == pyMat))
            self.assertEqual(np.sin(1), mad.math['sin'](1).eval())
            self.assertAlmostEqual(
                np.cos(0.5), mad.math['cos'](0.5).eval(), None, None, 4e-16
            )

            # temp vars
            res = (
                (
                    (mad.matrix(3).seq().emul(2) * mad.matrix(3).seq(3) + 3) * 2
                    + mad.matrix(3).seq(2)
                )
                - mad.matrix(3).seq(4)
            ).eval()
            np_mat = np.arange(9).reshape((3, 3)) + 1
            exp = ((np.matmul((np_mat * 2), (np_mat + 3)) + 3) * 2 + (np_mat + 2)) - (
                np_mat + 4
            )
            self.assertTrue(np.all(exp == res))


class TestArgsAndKwargs(unittest.TestCase):
    def test_args(self):
        with MAD() as mad:
            mad.load("MAD", "matrix", "cmatrix")
            mad["m1"] = mad.matrix(3).seq()
            mad["m2"] = mad.matrix(3).eye(2).mul(mad.m1)
            mad["m3"] = mad.matrix(3).seq().emul(mad.m1)
            mad["cm1"] = mad.cmatrix(3).seq(1j).map([1, 5, 9], "\\mn, n -> mn - 1i")
            self.assertTrue(np.all(mad.m2 == mad.m1 * 2))
            self.assertTrue(np.all(mad.m3 == (mad.m1 * mad.m1)))
            self.assertTrue(np.all(mad.cm1 == mad.m1 + 1j - np.eye(3) * 1j))
            # Add bool

    def test_kwargs(self):
        with MAD() as mad:
            mad.load("element", "sextupole")
            mad["m1"] = mad.MAD.matrix(3).seq()
            sd = mad.sextupole(
                knl=[0, 0.25j, 1 + 1j],
                l=1,
                alist=[1, 2, 3, 5],
                abool=True,
                opposite=False,
                mat=mad.m1,
            )
            self.assertEqual(sd.knl.eval(), [0, 0.25j, 1 + 1j])
            self.assertEqual(sd.l, 1)
            self.assertEqual(sd.alist.eval(), [1, 2, 3, 5])
            self.assertEqual(sd.abool, True)
            self.assertEqual(sd.opposite, False)
            self.assertTrue(np.all(sd.mat == np.arange(9).reshape((3, 3)) + 1))


class TestDir(unittest.TestCase):
    def test_dir(self):
        with MAD() as mad:
            mad.load("MAD", "gfunc", "element", "object")
            mad.load("element", "quadrupole")
            mad.load("gfunc", "functor")
            obj_dir = dir(mad.object)
            mad.send(
                "my_obj = object {a1 = 2, a2 = functor(\\s->s.a1), a3 = \\s->s.a1}"
            )
            obj_exp = sorted(["a1", "a2()", "a3"] + obj_dir)
            self.assertEqual(dir(mad.my_obj), obj_exp)
            self.assertEqual(mad.my_obj.a1, mad.my_obj.a3)

            quad_exp = dir(mad.quadrupole)
            self.assertEqual(
                dir(mad.quadrupole(knl=[0, 0.3], l=1)), quad_exp
            )  # Dir of instance of class should be the same as the class
            self.assertEqual(
                dir(mad.quadrupole(asd=10, qwe=20)), sorted(quad_exp + ["asd", "qwe"])
            )  # Adding to the instance should change the dir

    def test_dir_on_mad_object(self):
        with MAD() as mad:
            mad.load("MAD", "object")
            mad.send("my_obj = object {a = 1, b = 2, c = 3}")
            expected_dir = sorted(["a", "b", "c"] + dir(mad.object))
            self.assertGreater(len(expected_dir), 0)
            self.assertEqual(dir(mad.my_obj), expected_dir)

    def test_dir_on_last_object(self):
        with MAD() as mad:
            mad.load("MAD", "object")
            mad.send("last_obj = __mklast__(object {x = 10, y = 20})")
            mad["last"] = mad._MAD__get_mad_ref("last_obj")
            expected_dir = sorted(["x", "y"] + dir(mad.object))
            self.assertGreater(len(expected_dir), 0)
            self.assertEqual(dir(mad.last), expected_dir)

    def test_history(self):
        with MAD(debug=True, stdout="/dev/null") as mad:
            mad.send("a = 1")
            mad.send("b = 2")
            mad.send("c = a + b")
            history = mad.history()
            self.assertIn("a = 1", history)
            self.assertIn("b = 2", history)
            self.assertIn("c = a + b", history)


class TestDataFrame(unittest.TestCase):
    def generalDataFrame(self, headers, DataFrame, force_pandas=False):
        mad = MAD()
        mad.send("""
test = mtable{
    {"string"}, "number", "integer", "complex", "boolean", "list", "table", "range",! "generator",
    name     = "test",
    header   = {"string", "number", "integer", "complex", "boolean", "list", "table", "range"},
    string   = "string",
    number   = 1.234567890,
    integer  = 12345670,
    complex  = 1.3 + 1.2i,
    boolean  = true,
    list     = {1, 2, 3, 4, 5},
    table    = {1, 2, ["key"] = "value"},
    range    = MAD.range(1, 11),
}
    + {"a", 1.1, 1, 1 + 2i, true , {1, 2 }, {1 , 2 , ["3" ] = 3 }, MAD.range(1, 11),}
    + {"b", 2.2, 2, 2 + 3i, false, {3, 4 }, {4 , 5 , ["6" ] = 6 }, MAD.range(2, 12),}
    + {"c", 3.3, 3, 3 + 4i, true , {5, 6 }, {7 , 8 , ["9" ] = 9 }, MAD.range(3, 13),}
    + {"d", 4.4, 4, 4 + 5i, false, {7, 8 }, {10, 11, ["12"] = 12}, MAD.range(4, 14),}
    + {"e", 5.5, 5, 5 + 6i, true , {9, 10}, {13, 14, ["15"] = 15}, MAD.range(5, 15),}

test:addcol("generator", \\ri, m -> m:getcol("number")[ri] + 1i * m:getcol("number")[ri])
test:write("test")
             """)
        df = mad.test.to_df(force_pandas=force_pandas)
        self.assertTrue(isinstance(df, DataFrame))
        header = getattr(df, headers)
        self.assertEqual(header["name"], "test")
        self.assertEqual(header["string"], "string")
        self.assertEqual(header["number"], 1.234567890)
        self.assertEqual(header["integer"], 12345670)
        self.assertEqual(header["complex"], 1.3 + 1.2j)
        self.assertEqual(header["boolean"], True)
        self.assertEqual(header["list"], [1, 2, 3, 4, 5])
        tbl = getattr(df, headers)["table"]
        self.assertEqual(tbl[1], 1)
        self.assertEqual(tbl[2], 2)
        self.assertEqual(tbl["key"], "value")
        self.assertTrue(isinstance(tbl, dict))

        self.assertEqual(df["string"].tolist(), ["a", "b", "c", "d", "e"])
        self.assertEqual(df["number"].tolist(), [1.1, 2.2, 3.3, 4.4, 5.5])
        self.assertEqual(df["integer"].tolist(), [1, 2, 3, 4, 5])
        self.assertEqual(
            df["complex"].tolist(), [1 + 2j, 2 + 3j, 3 + 4j, 4 + 5j, 5 + 6j]
        )
        self.assertEqual(df["boolean"].tolist(), [True, False, True, False, True])
        lists = [the_list.eval() for the_list in df["list"]]
        self.assertEqual(lists, [[1, 2], [3, 4], [5, 6], [7, 8], [9, 10]])
        tbl = df["table"].tolist()
        for i in range(len(tbl)):
            lst = tbl[i]
            self.assertEqual([lst[0], lst[1]], [i * 3 + 1, i * 3 + 2])
            self.assertEqual(lst[str((i + 1) * 3)], (i + 1) * 3)
        self.assertEqual(
            df["range"].tolist(),
            [range(1, 12), range(2, 13), range(3, 14), range(4, 15), range(5, 16)],
        )

    def test_tfsDataFrame(self):
        self.generalDataFrame("headers", tfs.TfsDataFrame)

    def test_pandasDataFrame(self):
        sys.modules["tfs"] = None  # Remove tfs-pandas
        self.generalDataFrame("attrs", pd.DataFrame)
        del sys.modules["tfs"]

    def test_tfsDataFrame_force_pandas(self):
        self.generalDataFrame("attrs", pd.DataFrame, force_pandas=True)

    def test_failure(self):
        with MAD() as mad:
            mad.send("""
test = mtable{"string", "number"} + {"a", 1.1} + {"b", 2.2}
               """)
            pandas = sys.modules["pandas"]
            sys.modules["pandas"] = None
            self.assertRaises(ImportError, lambda: mad.test.to_df())
            sys.modules["pandas"] = pandas
            df = mad.test.to_df()
            self.assertTrue(isinstance(df, tfs.TfsDataFrame))
            self.assertEqual(df["string"].tolist(), ["a", "b"])
            self.assertEqual(df["number"].tolist(), [1.1, 2.2])


class TestEval(unittest.TestCase):
    def test_eval(self):
        with MAD() as mad:
            mad.send("a = 10; b = 20")
            result = mad.eval("a + b")
            self.assertEqual(result, 30)

            mad.send("c = {1, 2, 3, 4}")
            result = mad.eval("c[2]")  # Lua indexing starts at 1
            self.assertEqual(result, 2)

            mad.send("d = MAD.matrix(2, 2):seq()")
            result = mad.eval("d[2]")  # Accessing matrix element
            self.assertEqual(result, 2)

    def test_eval_class(self):
        with MAD() as mad:
            result = mad.math['sqrt'](2) + mad.math['log'](10)
            self.assertTrue(isinstance(result, mad_high_level_last_ref))
            self.assertEqual(result.eval(), math.sqrt(2) + math.log(10))


class TestIteration(unittest.TestCase):
    def test_iterate_through_object(self):
        with MAD() as mad:
            mad.send("""
            qd = MAD.element.quadrupole "qd" {knl = {0, 0.25}, l = 1.6}
            my_obj = sequence {qd, qd, qd, qd}
            """)
            for elem in mad.my_obj:
                if elem.name == "qd":
                    self.assertEqual(elem.l, 1.6)
                    for i in range(2):
                        self.assertEqual(elem.knl[i], 0.25 if i == 1 else 0)
                else:
                    self.assertEqual(elem.kind, "marker")


if __name__ == "__main__":
    unittest.main()
