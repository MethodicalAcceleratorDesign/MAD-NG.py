from pymadng import MAD
import matplotlib.pyplot as plt
import os 
current_dir = os.path.dirname(__file__) + "/"

with MAD() as mad:
    mad.MADX.load(f"'{current_dir}fodo.seq'", f"'{current_dir}fodo.mad'")
    mad["seq"] = mad.MADX.seq
    mad.seq.beam = mad.beam()
    mad["mtbl", "mflw"] = mad.twiss(sequence=mad.seq, method=4, implicit=True, nslice=10, save="atbody")
    plt.plot(mad.mtbl.s, mad.mtbl.beta11)
    plt.show()

with MAD() as mad:
    mad.MADX.load(f"'{current_dir}fodo.seq'", f"'{current_dir}fodo.mad'")
    mad.importVariables("MADX", ["seq"])
    mad.seq.beam = mad.beam()
    mad["mtbl", "mflw"] = mad.twiss(sequence=mad.seq, method=4, implicit=True, nslice=10, save="atbody")
    cols = ["name", "s", "beta11", "beta22", "mu1", "mu2", "alfa11", "alfa22"]
    mad.mtbl.write("'twiss_py.tfs'", cols)
    for x in mad.seq:
        print(x.name, x.kind)
    plt.plot(mad.mtbl.s, mad.mtbl.beta11)
    plt.show()


with MAD() as mad:
    mad["circum", "lcell"] = 60, 20

    mad.importVariables("math", ["sin", "pi"])
    mad["v"] = mad.deferred(k="1/(lcell/sin(pi/4)/4)")

    mad["qf"] = mad.quadrupole(mad.defExpr(knl=[0, " v.k"]), l=1)
    mad["qd"] = mad.quadrupole(mad.defExpr(knl=[0, "-v.k"]), l=1)
    mad.send("""
        seq = sequence 'seq' { refer='entry', l=circum, -- assign to seq in scope!
        qf { at = 0 },
        qd { at = 0.5 * lcell },
        qf { at = 1.0 * lcell },
        qd { at = 1.5 * lcell },
        qf { at = 2.0 * lcell },
        qd { at = 2.5 * lcell },
        }""")
    mad.seq.beam = mad.beam()
    mad["mtbl"] = mad.twiss(sequence=mad.seq, method=4, implicit=True, nslice=10, save="atbody")
    cols = ["name", "s", "beta11", "beta22", "mu1", "mu2", "alfa11", "alfa22"]
    mad.mtbl.write("'twiss_py.tfs'", cols)

    plt.plot(mad.mtbl.s, mad.mtbl["beta11"])
    plt.title("FODO Cell")
    plt.xlabel("s")
    plt.ylabel("beta11")
    plt.show()

with MAD() as mad:
    mad.send("""
    MADX:load("fodo.seq", "fodo.mad")
    local seq in MADX
    seq.beam = beam -- use default beam
    mtbl, mflw = twiss {sequence=seq, method=4, implicit=true, nslice=10, save="atbody"}
    """)
    plt.plot(mad.mtbl.s, mad.mtbl.beta11)
    plt.show()
