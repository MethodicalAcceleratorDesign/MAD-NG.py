from pymadng import MAD
import time

#NOTE: Kwargs looks horrible
#NOTE: call methdod is horrific
#NOTE: MADX, open environement is not fun
#NOTE: lamdba is a quick fix and would prefer, actual usability in script rather than just string


with MAD("/home/joshua/Documents/MAD-NGFork/MAD/src/pyMAD/src", log = True) as mad:
    mad.importVariables("MAD.element.flags", ["observed"])
    mad.importVariables("MAD.utility", ["assertf", "printf"])
    mad.importVariables("MAD.gphys", "mchklost")

    filepath = "/home/joshua/Documents/MAD-NGFork/MAD/examples/ex-lhc-couplingLocal/"
    mad.callMethod(None, "MADX", "load", f"'{filepath}lhc_as-built.seq'", f"'{filepath}lhc_as-built.mad'")
    mad.callMethod(None, "MADX", "load", f"'{filepath}opticsfile.21'", f"'{filepath}opticsfile.21.mad'")
    mad.callMethod(None, "MADX", "load", f"'{filepath}lhc_unset_vars.mad'")

    mad.importVariables("MADX", ["lhcb1", "nrj"])

    mad.assertf(None, "#lhcb1 == 6694", "'invalid number of elements %d in LHCB1 (6694 expected)'", "#lhcb1")
    mad.beam("lhcb1beam", particle = 'proton', energy = mad.nrj) #Do i want functions to be able to be passed as strings?
    mad.lhcb1.beam = mad.lhcb1beam
    mad.sendScript("""
    MADX:open_env()
    ktqx1_r2 = -ktqx1_l2 ! remove the link between these 2 vars
    kqsx3_l2 = -0.0015
    kqsx3_r2 = +0.0015
    MADX:close_env()
    """) #Is this a common occurence; does this want a separate function?
    t0 = time.time()
    mad.twiss("tbl", sequence = mad.lhcb1, method = 4, chrom = True)
    mad.callMethod(None, mad.tbl, "write", "'data/before_tune_correction_n'")

    print("Values before matching")
    print("dQx.b1=", mad.MADX.dqx_b1)
    print("dQy.b1=", mad.MADX.dqy_b1)

    mad.match(["status", "fmin", "ncall"], 
            mad.deferedExpr(command = "mchklost(twiss {sequence=lhcb1, method=4, observe=1})"), 
            mad.MADKwargs("variables", mad.MADKwargs(None, var = 'MADX.dqx_b1', name='dQx.b1'), mad.MADKwargs(None, var = 'MADX.dqy_b1', name='dQy.b1'), rtol = 1E-6), 
            mad.MADKwargs("equalities", mad.MADKwargs(None, mad.MADLambda("expr", ["t", "s"], "t.q1 - 62.30980"), name = 'q1'), mad.MADKwargs(None, mad.MADLambda("expr", ["t", "s"], "t.q2 - 60.32154"), name = 'q2'), tol=1e-3), 
            objective = {"fmin": 1e-3}, 
            maxcall = 100, info = 2
    )

    print("Values after matching")
    print("dQx.b1=", mad.MADX.dqx_b1)
    print("dQy.b1=", mad.MADX.dqy_b1)

    mad.twiss("tbl", sequence = mad.lhcb1, method = 4, chrom = True)
    mad.callMethod(None, mad.tbl, "write", "'data/after_tune_correction_n'")
    t1 = time.time()
    print("pre-tracking time: " + str(t1-t0) + 's')