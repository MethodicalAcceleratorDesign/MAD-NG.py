from pymadng import MAD

with MAD("/home/joshua/Documents/MAD-NGFork/MAD/src/pyMAD/src") as mad:
    mad["circum", "lcell"] = 60, 20
    mad.sendall()

    mad.deferred("v", f = "lcell/math.sin(math.pi/4)/4", k = "1/v.f")
    mad.quadrupole("qf", mad.deferedExpr(k1 = "v.k"), l = 1)
    mad.quadrupole("qd", mad.deferedExpr(k1 = "-v.k"), l = 1)
    mad.sequence("seq", mad.qfSet(at = 0 * mad.lcell),
                        mad.qdSet(at = 0.5 * mad.lcell),
                        mad.qfSet(at = 1 * mad.lcell),
                        mad.qdSet(at = 1.5 * mad.lcell),
                        mad.qfSet(at = 2 * mad.lcell),
                        mad.qdSet(at = 2.5 * mad.lcell), 
                        refer = 'entry', l=mad.circum )
    mad.beam("beam1")
    mad.seq.beam = mad.beam1
    mad.twiss("mtbl", sequence = mad.seq, method = 4, chrom=True, nslice = 10, implicit = True, save = "atbody")
    mad.callMethod(None, "mtbl", "write", "'twiss_py.tfs'", ['name', 's', 'beta11', 'beta22', 'mu1', 'mu2', 'alfa11', 'alfa22'])
    
    import matplotlib.pyplot as plt
    plt.plot(mad.mtbl.s, mad.mtbl["beta11"]) 
    plt.title("FODO Cell")
    plt.xlabel("s")
    plt.ylabel("beta11")
    plt.show()

with MAD("/home/joshua/Documents/MAD-NGFork/MAD/src/pyMAD/src") as mad:
    mad["circum", "lcell"] = 60, 20
    mad.sendVariables(["circum", "lcell"])
    mad.deferred("v", f = "lcell/math.sin(math.pi/4)/4", k = "1/v.f")
    mad.multipole("qf", mad.deferedExpr(knl = {0,  mad.v.k})) #Evaluates deferred expression before function
    mad.multipole("qd", mad.deferedExpr(knl = {0, -mad.v.k}))
    mad.sequence("seq", mad.qfSet(at = 0 * mad.lcell),
                        mad.qdSet(at = 0.5 * mad.lcell),
                        mad.qfSet(at = 1 * mad.lcell),
                        mad.qdSet(at = 1.5 * mad.lcell),
                        mad.qfSet(at = 2 * mad.lcell),
                        mad.qdSet(at = 2.5 * mad.lcell), 
                        refer = 'centre', l=mad.circum)
    mad.beam("beam1")
    mad.seq.beam = mad.beam1
    mad.twiss("mtbl2", sequence = mad.seq, method = 4, chrom=True)
    plt.plot(mad.mtbl2.s, mad.mtbl2["beta11"]) #Showing both methods of retrieving variables
    plt.title("FODO Cell")
    plt.xlabel("s")
    plt.ylabel("beta11")
    plt.show()

with MAD("/home/joshua/Documents/MAD-NGFork/MAD/src/pyMAD/src") as mad:
    filepath = "/home/joshua/Documents/MAD-NGFork/MAD/examples/ex-fodo-madx/"
    mad.loadsequence("seq", filepath + "fodo.seq", filepath + "fodo.mad")
    mad.beam("beam1")
    mad.seq.beam = mad.beam1
    mad.twiss("mtbl", sequence = mad.seq, method = 4, chrom=True)
    mad.callMethod(None, "mtbl", "write", "'twiss_py.tfs'", ['name', 's', 'beta11', 'beta22', 'mu1', 'mu2', 'alfa11', 'alfa22'])
