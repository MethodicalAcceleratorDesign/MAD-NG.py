from pymadng import MAD
import matplotlib.pyplot as plt

with MAD() as mad:
    mad.loadsequence("seq", "fodo.seq", "fodo.mad")
    mad.beam("beam1")
    mad.seq.beam = mad.beam1
    mad.twiss(["mtbl", "mflw"], sequence=mad.seq, method=4)
    cols = ["name", "s", "beta11", "beta22", "mu1", "mu2", "alfa11", "alfa22"]
    mad.mtbl.method("write", None, "'twiss_py.tfs'", cols)
    plt.plot(mad.mtbl.s, mad.mtbl["beta11"])
    plt.show()


with MAD() as mad:
    mad["circum", "lcell"] = 60, 20

    mad.importVariables("math", ["sin", "pi"])
    mad.deferred("v", k = "1/(lcell/sin(pi/4)/4)")

    mad.quadrupole("qf", mad.defExpr(knl=[0, " v.k"]), l=1)
    mad.quadrupole("qd", mad.defExpr(knl=[0, "-v.k"]), l=1)
    mad.sequence("seq",
        mad.qf.set(at=0   * mad.lcell),
        mad.qd.set(at=0.5 * mad.lcell),
        mad.qf.set(at=1   * mad.lcell),
        mad.qd.set(at=1.5 * mad.lcell),
        mad.qf.set(at=2   * mad.lcell),
        mad.qd.set(at=2.5 * mad.lcell),
        refer="entry", l=mad.circum,
    )
    mad.beam("beam1")
    mad.seq.beam = mad.beam1
    mad.twiss("mtbl", sequence=mad.seq, method=4, nslice=10, implicit=True, save="atbody")
    cols = ["name", "s", "beta11", "beta22", "mu1", "mu2", "alfa11", "alfa22"]
    mad.callMethod(None, "mtbl", "write", "'twiss_py.tfs'", cols)

    plt.plot(mad.mtbl.s, mad.mtbl["beta11"])
    plt.title("FODO Cell")
    plt.xlabel("s")
    plt.ylabel("beta11")
    plt.show()
with MAD() as mad:
    sharedData = mad.sendScript("""
    local beam, twiss in MAD
    MADX:load("fodo.seq", "fodo.mad")
    local seq in MADX
    seq.beam = beam -- use default beam
    local cols = {'name', 's', 'beta11', 'beta22', 'mu1', 'mu2', 'alfa11', 'alfa22'}
    mtbl = twiss {sequence=seq, method=4, implicit=true, nslice=10, save="atbody"}
    mtbl:write("twiss_mad_tfs", cols)
    sharedata({mtbl})
    """)
    mad.mtbl = sharedData[0]
    mad.mtbl.__name__ = "mtbl"
    plt.plot(mad.mtbl.s, mad.mtbl["beta11"])
    plt.show()


with MAD() as mad:
    mad.sendScript("""
    local beam, twiss in MAD
    MADX:load("fodo.seq", "fodo.mad")
    local seq in MADX
    seq.beam = beam -- use default beam
    local cols = {'name', 's', 'beta11', 'beta22', 'mu1', 'mu2', 'alfa11', 'alfa22'}
    mtbl = twiss {sequence=seq, method=4, implicit=true, nslice=10, save="atbody"}
    mtbl:write("twiss_mad_tfs", cols)
    """)
    mad.importVariables("_G", ["mtbl"])
    plt.plot(mad.mtbl.s, mad.mtbl["beta11"])
    plt.show()