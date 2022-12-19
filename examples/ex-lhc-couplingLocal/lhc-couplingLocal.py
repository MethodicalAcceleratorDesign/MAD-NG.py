from pymadng import MAD
import time
import os

import matplotlib.pyplot as plt
import numpy as np
current_dir = os.path.dirname(os.path.realpath(__file__)) + "/"


with MAD() as mad:
    mad.load("MAD.element.flags", ["observed"])
    mad.load("MAD.utility", ["assertf", "printf"])
    mad.load("MAD.gphys", ["mchklost"])

    mad.MADX.load(f"'{current_dir}lhc_as-built.seq'", f"'{current_dir}lhc_as-built.mad'")
    mad.MADX.load(f"'{current_dir}opticsfile.21'", f"'{current_dir}opticsfile.21.mad'")
    mad.MADX.load(f"'{current_dir}lhc_unset_vars.mad'")

    mad.load("MADX", ["lhcb1", "nrj"])

    mad.assertf("#lhcb1 == 6694",
        "'invalid number of elements %d in LHCB1 (6694 expected)'", "#lhcb1")
    
    mad.lhcb1.beam = mad.beam(particle="'proton'", energy=mad.nrj)
    mad.MADX_env_send("""
    ktqx1_r2 = -ktqx1_l2 ! remove the link between these 2 vars
    kqsx3_l2 = -0.0015
    kqsx3_r2 = +0.0015
    """)
    t0 = time.time()
    mad["tbl", "flw"] = mad.twiss(sequence=mad.lhcb1, method=4)
    # plt.plot(mad.tbl.s, mad.tbl.beta11)
    # plt.show()
    mad.tbl.write("'before_tune_correction_n'")

    print("Values before matching")
    print("dQx.b1=", mad.MADX.dqx_b1)
    print("dQy.b1=", mad.MADX.dqy_b1)

    mad.send("""
    expr1 = \\t, s -> t.q1 - 62.30980
    expr2 = \\t, s -> t.q2 - 60.32154
    function twiss_and_send()
        local mtbl, mflow = twiss {sequence=lhcb1, method=4}
        py:send({mtbl.s, mtbl.beta11})
        return mtbl, mflow
    end
    """)
    match_rtrn = mad.match(
        command=mad.twiss_and_send,
        variables = [
            {"var":"'MADX.dqx_b1'", "name":"'dQx.b1'", "'rtol'":1e-6},
            {"var":"'MADX.dqy_b1'", "name":"'dQy.b1'", "'rtol'":1e-6},
        ],
        equalities = [
            {"expr": mad.expr1, "name": "'q1'", "tol":1e-3},
            {"expr": mad.expr2, "name": "'q2'", "tol":1e-3},
        ],
        objective={"fmin": 1e-3}, maxcall=100, info=2,
    )
    mad.send("py:send(nil)")
    tws_result = mad.recv ()
    x = tws_result[0]
    y = tws_result[1]

    plt.ion()
    fig = plt.figure()
    ax = fig.add_subplot(111)
    line1, = ax.plot(x, y, 'b-')
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

    mad.twiss("tbl", sequence=mad.lhcb1, method=4, chrom=True)
    mad.tbl.write("'after_tune_correction_n'")
    t1 = time.time()
    print("pre-tracking time: " + str(t1 - t0) + "s")