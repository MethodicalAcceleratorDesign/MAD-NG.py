from pymadng import MAD
import time
import os

# NOTE: Kwargs looks horrible
# NOTE: call methdod is horrific
# NOTE: MADX, open environement is not fun
# NOTE: lamdba is a quick fix and would prefer, actual usability in script rather than just string

current_dir = os.path.dirname(__file__)

with MAD(readTimeout=None) as mad:
    mad.importVariables("MAD.element.flags", ["observed"])
    mad.importVariables("MAD.utility", ["assertf", "printf"])
    mad.importVariables("MAD.gphys", ["mchklost"])

    filepath = current_dir + "/"
    mad.MADX.method(
        "load", None, f"'{filepath}lhc_as-built.seq'", f"'{filepath}lhc_as-built.mad'"
    )
    mad.MADX.method(
        "load", None, f"'{filepath}opticsfile.21'", f"'{filepath}opticsfile.21.mad'"
    )
    mad.MADX.method("load", None, f"'{filepath}lhc_unset_vars.mad'")

    mad.importVariables("MADX", ["lhcb1", "nrj"])

    mad.assertf(
        None,
        "#lhcb1 == 6694",
        "'invalid number of elements %d in LHCB1 (6694 expected)'",
        "#lhcb1",
    )
    mad.beam("lhcb1beam", particle="proton", energy=mad.nrj)
    mad.lhcb1.beam = mad.lhcb1beam
    mad.MADXInput(
        """
    ktqx1_r2 = -ktqx1_l2 ! remove the link between these 2 vars
    kqsx3_l2 = -0.0015
    kqsx3_r2 = +0.0015
    """
    )
    t0 = time.time()
    mad.twiss("tbl", sequence=mad.lhcb1, method=4, chrom=True)
    mad.tbl.method("write", None, "'before_tune_correction_n'")

    print("Values before matching")
    print("dQx.b1=", mad.MADX.dqx_b1)
    print("dQy.b1=", mad.MADX.dqy_b1)

    mad.match(
        ["status", "fmin", "ncall"],
        mad.defExpr(command="mchklost(twiss {sequence=lhcb1, method=4, observe=1})"),
        mad.MADKwargs(
            "variables",
            mad.MADKwargs(None, var="MADX.dqx_b1", name="dQx.b1"),
            mad.MADKwargs(None, var="MADX.dqy_b1", name="dQy.b1"),
            rtol=1e-6,
        ),
        mad.MADKwargs(
            "equalities",
            mad.MADKwargs(
                None, mad.MADLambda("expr", ["t", "s"], "t.q1 - 62.30980"), name="q1"
            ),
            mad.MADKwargs(
                None, mad.MADLambda("expr", ["t", "s"], "t.q2 - 60.32154"), name="q2"
            ),
            tol=1e-3,
        ),
        objective={"fmin": 1e-3},
        maxcall=100,
        info=2,
    )

    print("Values after matching")
    print("dQx.b1=", mad.MADX.dqx_b1)
    print("dQy.b1=", mad.MADX.dqy_b1)

    mad.twiss("tbl", sequence=mad.lhcb1, method=4, chrom=True)
    mad.tbl.method("write", None, "'after_tune_correction_n'")
    t1 = time.time()
    print("pre-tracking time: " + str(t1 - t0) + "s")
