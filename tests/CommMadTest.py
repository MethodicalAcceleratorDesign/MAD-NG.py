from sympy import var
from pymadng import MAD
import numpy as np
import os
import matplotlib.pyplot as plt
import time

#TODO: Make it so writing to variables is easy

pid = os.fork()

# #Test 1
if pid > 0:
    with MAD(os.getcwd(), log = False, copyOnRetreive=False, ram_limit=2**30 + 2**12) as mad: # open mad process, if you just use mad = MAD(), then be sure to close it afterwords; for multiprocessing, os.fork() can work with the with statement
        arr0 = np.zeros((10000, 1000)) + 1j #2*10000*1000*8 -> 160 MB
        # mad["arr"] = arr0 + 1
        # mad.sendVariables(["arr"]*100)

        #Set variables within the mad class
        start_time = time.time()
        mad["arr"] = arr0
        # print(mad.arr)
        mad["arr2", "arr3", "arr4"] = arr0, arr0, arr0
        print("receive large array", time.time() - start_time)

        #Directly send to mad
        # mad.writeToProcess("arr = arr * 2")
        mad.callMethod("arr", "arr", "mul", 2)
        print((mad["arr"] == arr0*2).all())
        mad.eval("arr2 = arr * 2")
        mad.eval("arr3 = arr / 3")
        # mad["arr", "arr2"])

        #Recieving variables: update retrieves all the variables within the mad class or just send a string and the variable of that name will be retrieved
        start_time = time.time()
        mad.updateVariables()
        print("send large array", time.time() - start_time)
        print((mad["arr"] == arr0*2).all())
        print((mad["arr2"] == arr0*2*2).all())
        print((mad["arr3"] == arr0*2/3).all())

    with MAD(os.getcwd(), log = False, copyOnRetreive=False, ram_limit=2**30 + 2**12) as mad: # open mad process, if you just use mad = MAD(), then be sure to close it afterwords; for multiprocessing, os.fork() can work with the with statement
        numVars = 25000
        varNameList = []
        values = [12345] * numVars
        for i in range(numVars):
            varNameList.append(f"var{i}")
        
        start_time = time.time()
        mad[tuple(varNameList)] = values
        print(f"send {numVars} vals", time.time() - start_time)
        start_time = time.time()
        
        start_time = time.time()
        mad.sendVariables(list(varNameList), values)
        print(f"send {numVars} vals v2", time.time() - start_time)

        start_time = time.time()
        mad.receiveVariables(list(varNameList))
        print(f"receive {numVars} vals", time.time() - start_time)
        input()
        
        # arr = None
    print("proc1 ended", time.time() - start_time)
else:
    with MAD(os.getcwd(), log=True) as mad:
        
        #METHOD 1
        filepath = "/home/joshua/Documents/MAD-NGFork/MAD/examples/ex-fodo-madx/"
        mad.loadsequence("seq", filepath + "fodo.seq")
        mad.beam("beam1")
        mad.seq.beam = mad.beam1
        mad.twiss("mtbl", sequence = mad.seq, method = 4, chrom=True)
        plt.plot(mad.mtbl.s, mad.mtbl["beta11"]) #Showing both methods of retrieving variables
        print(mad.mtbl.header)
        plt.show()

        #METHOD 2
        mad["circum", "lcell"] = 60, 20
        mad.sendVariables(["circum", "lcell"])
        #WIll add a search into mad for variable in the future
        mad.deferred("v", f = "lcell/math.sin(math.pi/4)/4", k = "1/v.f")
        # mad.multipole("qf", mad.defExpr(knl = {0,  mad.v.k}))
        mad.multipole("qf", mad.defExpr(knl = "{0,  v.k}"))
        # mad.quadrupole("qf", mad.defExpr(k1 = "v.k"), l = 1)
        
        # mad.multipole("qd", mad.defExpr(knl = {0, -mad.v.k}))
        mad.multipole("qd", mad.defExpr(knl = "{0, -v.k}"))

        # mad.quadrupole("qd", mad.defExpr(k1 = "-v.k"), l = 1)
        mad.sequence("seq2", mad.qf.set(at = 0 * mad.lcell),
                            mad.qd.set(at = 0.5 * mad.lcell),
                            mad.qf.set(at = 1 * mad.lcell),
                            mad.qd.set(at = 1.5 * mad.lcell),
                            mad.qf.set(at = 2 * mad.lcell),
                            mad.qd.set(at = 2.5 * mad.lcell), 
                            refer = 'entry', l=mad.circum )
        mad.beam("beam1")
        mad.seq2.beam = mad.beam1
        mad.twiss("mtbl2", sequence = mad.seq2, method = 4, chrom=True, nslice = 10, implicit = True, save = "atbody")
        plt.plot(mad.mtbl2.s, mad.mtbl2["beta11"]) #Showing both methods of retrieving variables
        print(mad.mtbl2.header)
        plt.show()

        
        