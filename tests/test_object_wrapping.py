from __future__ import annotations

import copy
import math
import sys

import numpy as np
import pandas as pd
import pytest
import tfs

from pymadng import MAD
from pymadng.madp_classes import MadLastRef, MadRef


def test_get():
    with MAD(stdout="/dev/null", redirect_stderr=True) as mad:
        mad.load("element", "quadrupole")
        assert mad.asdfg is None
        mad.send("""qd = quadrupole {knl={0,  0.25}, l = 1}""")
        mad.send("""qf = quadrupole {qd = qd}""")
        qd, qf = mad["qd", "qf"]
        assert qd._name == "qd"
        assert qd._parent is None
        assert qd._mad == mad._MAD__process
        assert qd.knl.eval() == [0, 0.25]
        assert qd.l == 1
        with pytest.raises(AttributeError):
            qd.asdfg
        with pytest.raises(KeyError):
            qd["asdfg"]
        with pytest.raises(IndexError):
            qd[1]
        assert isinstance(qf.qd, MadRef)
        assert qf.qd.knl.eval() == [0, 0.25]
        assert qf.qd.l == 1
        assert qf.qd == qd

        mad.send("objList = {qd, qf, qd, qf, qd} py:send(objList)")
        obj_list = mad.recv("objList")
        for i, item in enumerate(obj_list):
            if i % 2 != 0:
                assert isinstance(item.qd, MadRef)
                assert item.qd._parent == f"objList[{i + 1}]"
                assert item.qd.knl.eval() == [0, 0.25]
                assert item.qd.l == 1
                assert item.qd == qd
            else:
                assert item.knl.eval() == [0, 0.25]
                assert item.l == 1
                assert item == qd
            assert item._parent == "objList"

        assert "knl" in dir(qd)
        assert all(not name.startswith("_") for name in dir(qd))


def test_deepcopy_warning():
    with MAD(stdout="/dev/null", redirect_stderr=True) as mad:
        mad.load("element", "quadrupole")
        mad.send("""qd = quadrupole {knl={0, 0.25}, l = 1}""")
        qd = mad.qd

        with pytest.warns(UserWarning, match="An attempt to deepcopy a MadRef"):
            qd_copy = copy.deepcopy(qd)

        assert qd_copy == qd


def test_invalid_reference_setitem_type():
    with MAD(stdout="/dev/null", redirect_stderr=True) as mad:
        mad.load("element", "quadrupole")
        mad.send("""qd = quadrupole {knl={0, 0.25}, l = 1}""")

        with pytest.raises(TypeError, match="expected string or int"):
            mad.qd[1.5] = 2


def test_set():
    with MAD() as mad:
        mad.load("element", "quadrupole")
        mad.send("""qd = quadrupole {knl={0,  0.25}, l = 1} py:send(qd)""")
        mad["qd2"] = mad.recv("qd")
        assert mad.qd2._name == "qd2"
        assert mad.qd2._parent is None
        assert mad.qd2._mad == mad._MAD__process
        assert mad.qd2.knl.eval() == [0, 0.25]
        assert mad.qd2.l == 1
        assert mad.qd2 == mad.qd
        mad["a", "b"] = mad.MAD.gmath.reim(9.75 + 1.5j)
        assert mad.a == 9.75
        assert mad.b == 1.5
        mad.send("f = \\-> (1, 2, 3, 9, 8, 7)")
        mad["r1", "r2", "r3", "r4", "r5", "r6"] = mad.f()
        assert (mad.r1, mad.r2, mad.r3, mad.r4, mad.r5, mad.r6) == (1, 2, 3, 9, 8, 7)


def test_send_vars():
    with MAD() as mad:
        mad.send_vars(a=1, b=2.5, c="test", d=[1, 2, 3])
        assert mad.a == 1
        assert mad.b == 2.5
        assert mad.c == "test"
        assert mad.d.eval() == [1, 2, 3]


def test_recv_vars():
    with MAD() as mad:
        mad.send_vars(a=1, b=2.5, c="test", d=[1, 2, 3])
        a, b, c, d = mad.recv_vars("a", "b", "c", "d")
        assert a == 1
        assert b == 2.5
        assert c == "test"
        assert d.eval() == [1, 2, 3]


def test_quote_strings():
    with MAD() as mad:
        assert mad.quote_strings("test") == "'test'"
        assert mad.quote_strings(["a", "b", "c"]) == ["'a'", "'b'", "'c'"]


def test_create_deferred_expression():
    with MAD() as mad:
        deferred = mad.create_deferred_expression(a="x + y", b="x * y")
        mad.send_vars(x=2, y=3)
        assert deferred.a == 5
        assert deferred.b == 6
        mad.send_vars(x=5, y=10)
        assert deferred.a == 15
        assert deferred.b == 50

        mad["deferred"] = mad.create_deferred_expression(a="x - y", b="x / y")
        mad.send_vars(x=10, y=2)
        assert mad.deferred.a == 8
        assert mad.deferred.b == 5


def test_call_obj():
    with MAD(py_name="python") as mad:
        mad.load("element", "quadrupole", "sextupole")
        qd = mad.quadrupole(knl=[0, 0.25], l=1)
        sd = mad.sextupole(knl=[0, 0.25, 0.5], l=1)

        mad["qd"] = qd
        assert mad.qd._name == "qd"
        assert mad.qd._parent is None
        assert mad.qd._mad == mad._MAD__process
        assert mad.qd.knl.eval() == [0, 0.25]
        assert mad.qd.l == 1

        sdc = sd
        mad["sd"] = sd
        del sd
        assert mad.sd._name == "sd"
        assert mad.sd._parent is None
        assert mad.sd._mad == mad._MAD__process
        assert mad.sd.knl.eval() == [0, 0.25, 0.5]
        assert mad.sd.l == 1

        qd = mad.quadrupole(knl=[0, 0.3], l=1)
        assert sdc._name == "_last[2]"
        assert qd._name == "_last[3]"
        assert qd.knl.eval() == [0, 0.3]
        qd = mad.quadrupole(knl=[0, 0.25], l=1)
        assert qd._name == "_last[1]"


def test_call_last():
    with MAD() as mad:
        mad.send("func_test = \\a-> \\b-> \\c-> a+b*c")
        with pytest.raises(TypeError):
            mad.MAD()
        assert mad.func_test(1)(2)(3) == 7


def test_call_fail():
    with MAD(stdout="/dev/null", redirect_stderr=True) as mad:
        mad.send("func_test = \\a-> \\b-> \\c-> 'a'+b")
        mad.func_test(1)(2)(3)
        with pytest.raises(RuntimeError):
            mad.recv()
        with pytest.raises(RuntimeError):
            mad.mtable.read("'abad.tfs'").eval()


def test_call_func():
    with MAD(py_name="python") as mad:
        mad.load("element", "quadrupole")
        mad["qd"] = mad.quadrupole(knl=[0, 0.25], l=1)
        mad.qd.select()
        mad["qdSelected"] = mad.qd.is_selected()
        assert mad.qdSelected
        mad.qd.deselect()
        mad["qdSelected"] = mad.qd.is_selected()
        assert not mad.qdSelected
        mad.qd.set_variables({"l": 2})
        assert mad.qd.l == 2


def test_mult_rtrn():
    with MAD() as mad:
        mad.send(
            """
      obj = MAD.object "obj" {a = 1, b = 2}
      local function mult_rtrn ()
        obj2 = MAD.object "obj2" {a = 2, b = 3}
        return obj, obj, obj, obj2
      end
      last_rtn = __mklast__(mult_rtrn())
      lastobj = __mklast__(obj)
      notLast = {mult_rtrn()}
      """
        )

        mad["o11", "o12", "o13", "o2"] = mad._MAD__get_MadRef("last_rtn")
        mad["p11", "p12", "p13", "p2"] = mad._MAD__get_MadRef("notLast")
        mad["objCpy"] = mad._MAD__get_MadRef("lastobj")
        assert mad.o11.a == 1
        assert mad.o11.b == 2
        assert mad.o12.a == 1
        assert mad.o12.b == 2
        assert mad.o13.a == 1
        assert mad.o13.b == 2
        assert mad.o2.a == 2
        assert mad.o2.b == 3
        assert mad.p11.a == 1
        assert mad.p11.b == 2
        assert mad.p12.a == 1
        assert mad.p12.b == 2
        assert mad.p13.a == 1
        assert mad.p13.b == 2
        assert mad.p2.a == 2
        assert mad.p2.b == 3
        assert mad.objCpy == mad.obj


def test_madx(tmp_path):
    with MAD() as mad:
        assert mad.MADX.abs(-1) == 1
        assert mad.MADX.ceil(1.2) == 2

        assert mad.MAD.MADX.abs(-1) == 1
        assert mad.MAD.MADX.ceil(1.2) == 2

        assert mad.MADX.MAD.MADX.abs(-1) == 1
        assert mad.MADX.MAD.MADX.ceil(1.2) == 2
        seq_file = tmp_path / "test.seq"
        seq_file.write_text(
            """
      qd: quadrupole, l=1, knl:={0, 0.25};
      """
        )
        mad.MADX.load(f"'{seq_file}'")
        assert mad.MADX.qd.l == 1
        assert mad.MADX.qd.knl.eval() == [0, 0.25]


def test_evaluate_in_madx_environment():
    with MAD() as mad:
        madx_code = """
            qd = quadrupole {l=1, knl:={0, 0.25}}
            """
        mad.evaluate_in_madx_environment(madx_code)
        assert mad.MADX.qd.l == 1
        assert mad.MADX.qd.knl.eval() == [0, 0.25]


def test_matrix():
    with MAD(py_name="python") as mad:
        mad.load("MAD", "matrix")
        py_mat = np.arange(1, 101).reshape((10, 10))

        mad["mat"] = mad.matrix(10).seq(2) + 2
        assert np.all(mad.mat == py_mat + 4)

        mad["mat"] = mad.matrix(10).seq() / 3
        assert np.allclose(mad.mat, py_mat / 3)

        mad["mat"] = mad.matrix(10).seq() * 4
        assert np.all(mad.mat == py_mat * 4)

        mad["mat"] = mad.matrix(10).seq() ** 3
        assert np.all(mad.mat == np.linalg.matrix_power(py_mat, 3))

        mad["mat"] = mad.matrix(10).seq() + 2 / 3 * 4**3
        assert np.all(mad.mat == py_mat + 2 / 3 * 4**3)

        assert np.all(np.array(mad.MAD.matrix(10).seq()) == np.arange(1, 101))
        assert np.all(list(mad.MAD.matrix(10).seq()) == np.arange(1, 101))
        assert np.all(mad.MAD.matrix(10).seq().eval() == py_mat)
        assert np.sin(1) == mad.math["sin"](1).eval()
        assert mad.math["cos"](0.5).eval() == pytest.approx(np.cos(0.5), abs=4e-16)

        res = (
            ((mad.matrix(3).seq().emul(2) * mad.matrix(3).seq(3) + 3) * 2 + mad.matrix(3).seq(2))
            - mad.matrix(3).seq(4)
        ).eval()
        np_mat = np.arange(9).reshape((3, 3)) + 1
        exp = ((np.matmul((np_mat * 2), (np_mat + 3)) + 3) * 2 + (np_mat + 2)) - (np_mat + 4)
        assert np.all(exp == res)


def test_args():
    with MAD() as mad:
        mad.load("MAD", "matrix", "cmatrix")
        mad["m1"] = mad.matrix(3).seq()
        mad["m2"] = mad.matrix(3).eye(2).mul(mad.m1)
        mad["m3"] = mad.matrix(3).seq().emul(mad.m1)
        mad["cm1"] = mad.cmatrix(3).seq(1j).map([1, 5, 9], "\\mn, n -> mn - 1i")
        assert np.all(mad.m2 == mad.m1 * 2)
        assert np.all(mad.m3 == (mad.m1 * mad.m1))
        assert np.all(mad.cm1 == mad.m1 + 1j - np.eye(3) * 1j)


def test_kwargs():
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
        assert sd.knl.eval() == [0, 0.25j, 1 + 1j]
        assert sd.l == 1
        assert sd.alist.eval() == [1, 2, 3, 5]
        assert sd.abool
        assert not sd.opposite
        assert np.all(sd.mat == np.arange(9).reshape((3, 3)) + 1)


def test_dir():
    with MAD(py_name="python") as mad:
        mad.load("MAD", "gfunc", "element", "object")
        mad.load("element", "quadrupole")
        mad.load("gfunc", "functor")
        obj_dir = dir(mad.object)
        mad.send("my_obj = object {a1 = 2, a2 = functor(\\s->s.a1), a3 = \\s->s.a1}")
        obj_exp = sorted(["a1", "a2()", "a3"] + obj_dir)
        assert dir(mad.my_obj) == obj_exp
        assert mad.my_obj.a1 == mad.my_obj.a3

        quad_exp = dir(mad.quadrupole)
        assert dir(mad.quadrupole(knl=[0, 0.3], l=1)) == quad_exp
        assert dir(mad.quadrupole(asd=10, qwe=20)) == sorted(quad_exp + ["asd", "qwe"])


def test_dir_on_mad_object():
    with MAD(py_name="python") as mad:
        mad.load("MAD", "object")
        mad.send("my_obj = object {a = 1, b = 2, c = 3}")
        expected_dir = sorted(["a", "b", "c"] + dir(mad.object))
        assert len(expected_dir) > 0
        assert dir(mad.my_obj) == expected_dir


def test_dir_on_last_object():
    with MAD() as mad:
        mad.load("MAD", "object")
        mad.send("last_obj = __mklast__(object {x = 10, y = 20})")
        mad["last"] = mad._MAD__get_MadRef("last_obj")
        expected_dir = sorted(["x", "y"] + dir(mad.object))
        assert len(expected_dir) > 0
        assert dir(mad.last) == expected_dir


def test_history():
    with MAD(debug=True, stdout="/dev/null") as mad:
        mad.send("a = 1")
        mad.send("b = 2")
        mad.send("c = a + b")
        history = mad.history()
        assert "a = 1" in history
        assert "b = 2" in history
        assert "c = a + b" in history


def _generate_data_frame(headers_attr, dataframe_type, force_pandas=False):
    with MAD() as mad:
        mad.send(
            """
test = mtable{
    {"string"}, "number", "integer", "complex", "boolean", "list", "table", "range",
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
             """
        )
        df = mad.test.to_df(force_pandas=force_pandas)
        assert isinstance(df, dataframe_type)
        header = getattr(df, headers_attr)
        assert header["name"] == "test"
        assert header["string"] == "string"
        assert header["number"] == 1.234567890
        assert header["integer"] == 12345670
        assert header["complex"] == 1.3 + 1.2j
        assert header["boolean"]
        assert header["list"] == [1, 2, 3, 4, 5]
        tbl = header["table"]
        assert tbl[1] == 1
        assert tbl[2] == 2
        assert tbl["key"] == "value"
        assert isinstance(tbl, dict)

        assert df["string"].tolist() == ["a", "b", "c", "d", "e"]
        assert df["number"].tolist() == [1.1, 2.2, 3.3, 4.4, 5.5]
        assert df["integer"].tolist() == [1, 2, 3, 4, 5]
        assert df["complex"].tolist() == [1 + 2j, 2 + 3j, 3 + 4j, 4 + 5j, 5 + 6j]
        assert df["boolean"].tolist() == [True, False, True, False, True]
        lists = [the_list.eval() for the_list in df["list"]]
        assert lists == [[1, 2], [3, 4], [5, 6], [7, 8], [9, 10]]
        tables = df["table"].tolist()
        for i, table in enumerate(tables):
            assert [table[0], table[1]] == [i * 3 + 1, i * 3 + 2]
            assert table[str((i + 1) * 3)] == (i + 1) * 3
        assert df["range"].tolist() == [
            range(1, 12),
            range(2, 13),
            range(3, 14),
            range(4, 15),
            range(5, 16),
        ]


def test_generate_tfs_data_frame():
    _generate_data_frame("headers", tfs.TfsDataFrame)


def test_data_frame_without_tfs(monkeypatch):
    monkeypatch.setitem(sys.modules, "tfs", None)
    _generate_data_frame("attrs", pd.DataFrame)


def test_force_pandas_data_frame():
    _generate_data_frame("attrs", pd.DataFrame, force_pandas=True)


def test_data_frame_failure(monkeypatch):
    with MAD() as mad:
        mad.send(
            """
test = mtable{"string", "number"} + {"a", 1.1} + {"b", 2.2}
               """
        )
        monkeypatch.setitem(sys.modules, "pandas", None)
        with pytest.raises(ImportError):
            mad.test.to_df()
        monkeypatch.setitem(sys.modules, "pandas", pd)
        df = mad.test.to_df()
        assert isinstance(df, tfs.TfsDataFrame)
        assert df["string"].tolist() == ["a", "b"]
        assert df["number"].tolist() == [1.1, 2.2]


def test_eval():
    with MAD() as mad:
        mad.send("a = 10; b = 20")
        assert mad.eval("a + b") == 30

        mad.send("c = {1, 2, 3, 4}")
        assert mad.eval("c[2]") == 2

        mad.send("d = MAD.matrix(2, 2):seq()")
        assert mad.eval("d[2]") == 2


def test_eval_class():
    with MAD() as mad:
        result = mad.math["sqrt"](2) + mad.math["log"](10)
        assert isinstance(result, MadLastRef)
        assert result.eval() == math.sqrt(2) + math.log(10)


def test_iterate_through_object():
    with MAD() as mad:
        mad.send(
            """
            qd = MAD.element.quadrupole "qd" {knl = {0, 0.25}, l = 1.6}
            my_obj = sequence {qd, qd, qd, qd}
            """
        )
        for elem in mad.my_obj:
            if elem.name == "qd":
                assert elem.l == 1.6
                for i in range(2):
                    assert elem.knl[i] == (0.25 if i == 1 else 0)
            else:
                assert elem.kind == "marker"
