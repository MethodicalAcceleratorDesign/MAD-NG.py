"""
This script demonstrates the usage of the MAD class to perform a local coupling correction in the LHC.

The aim of this script is demonstrate a combination of pythonic and MAD-NG syntax.
Also, it demonstrates how you can retrieve data from MAD-NG and plot it in real-time, as it is being calculated, preventing the need to store it in memory.
"""

import os
import time

import matplotlib.pyplot as plt

from pymadng import MAD

original_dir = os.getcwd()
os.chdir(os.path.dirname(os.path.realpath(__file__)))


with MAD() as mad:
    mad.load("MAD.utility", "assertf")

    mad.MADX.load("'lhc_as-built.seq'", "'lhc_as-built.mad'")
    mad.MADX.load("'opticsfile.21'", "'opticsfile.21.mad'")
    mad.MADX.load(
        "'lhc_unset_vars.mad'"
    )  # Load a list of unset variables to prevent warnings

    mad.load("MADX", "lhcb1", "nrj")

    mad.assertf(
        "#lhcb1 == 6694",
        "'invalid number of elements %d in LHCB1 (6694 expected)'",
        "#lhcb1",
    )

    mad.lhcb1.beam = mad.beam(particle="'proton'", energy=mad.nrj)
    mad.evaluate_in_madx_environment("""
    ktqx1_r2 = -ktqx1_l2 ! remove the link between these 2 vars
    kqsx3_l2 = -0.0015
    kqsx3_r2 = +0.0015
    """)
    t0 = time.time()
    mad["tbl", "flw"] = mad.twiss(sequence=mad.lhcb1)
    mad.tbl.write("'before_tune_correction_n'")

    print("Values before matching")
    print("dQx.b1=", mad.MADX.dqx_b1)
    print("dQy.b1=", mad.MADX.dqy_b1)

    mad.send("""
    expr1 = \\t, s -> t.q1 - 62.30980
    expr2 = \\t, s -> t.q2 - 60.32154
    function twiss_and_send()
        local mtbl, mflow = twiss {sequence=lhcb1}
        py:send({mtbl.s, mtbl.beta11}, true) -- True means that the data table is sent as a shallow copy
        return mtbl, mflow
    end
    """)
    match_rtrn = mad.match(
        command=mad.twiss_and_send,
        variables=[
            {"var": "'MADX.dqx_b1'", "name": "'dQx.b1'", "'rtol'": 1e-6},
            {"var": "'MADX.dqy_b1'", "name": "'dQy.b1'", "'rtol'": 1e-6},
        ],
        equalities=[
            {"expr": mad.expr1, "name": "'q1'", "tol": 1e-3},
            {"expr": mad.expr2, "name": "'q2'", "tol": 1e-3},
        ],
        objective={"fmin": 1e-3},
        maxcall=100,
        info=2,
    )
    mad.send("py:send(nil)")
    tws_result = mad.recv()
    x = tws_result[0]
    y = tws_result[1]

    plt.ion()
    fig = plt.figure()
    ax = fig.add_subplot(111)
    (line1,) = ax.plot(x, y, "b-")
    while tws_result:
        line1.set_xdata(tws_result[0])
        line1.set_ydata(tws_result[1])
        fig.canvas.draw()
        fig.canvas.flush_events()
        tws_result = mad.recv()

    mad["status", "fmin", "ncall"] = match_rtrn
    del match_rtrn

    print("Values after matching")
    print("dQx.b1=", mad.MADX.dqx_b1)
    print("dQy.b1=", mad.MADX.dqy_b1)

    mad.twiss("tbl", sequence=mad.lhcb1)
    mad.tbl.write("'after_tune_correction_n'")
    t1 = time.time()
    print("Matching time: " + str(t1 - t0) + "s")

os.chdir(original_dir)
