from pymadng import MAD
import numpy as np
import os
import matplotlib.pyplot as plt
import time

#TODO: Make it so writing to variables is easy

pid = os.fork()

#Test 1
if pid > 0:
    with MAD(log = True, copyOnRetreive=False) as mad: # open mad process, if you just use mad = MAD(), then be sure to close it afterwords; for multiprocessing, os.fork() can work with the with statement
        arr0 = np.zeros((10000, 1000)) + 1j #2*10000*1000*8 -> 160 MB
        # mad["arr"] = arr0 + 1
        # mad.sendVariables(["arr"]*100)

        #Set variables within the mad class
        mad["arr"] = arr0
        # print(mad.arr)
        mad["arr2", "arr3", "arr4"] = arr0, arr0, arr0


        #Three ways to send multiple variables: sendall, send variables just using name, send variables not within mad class, giving name and variable
        start_time = time.time()
        print(mad.userVars)
        mad.sendall()
        print(time.time() - start_time)
        # mad.sendVariables(["arr", "arr2", "arr3","arr4"])
        # mad.sendVariables(["arr", "arr2", "arr3","arr4"], [arr0, arr0, arr0, arr0])
        #Directly send to mad
        # mad.writeToProcess("arr = arr * 2")
        mad.callMethod("arr", "arr", "mul", 2)
        mad.writeToProcess("arr2 = arr * 2")
        mad.writeToProcess("arr3 = arr / 3")
        # mad["arr", "arr2"])

        #Recieving variables: update retrieves all the variables within the mad class or just send a string and the variable of that name will be retrieved
        start_time = time.time()
        mad.updateVariables()
        print(time.time() - start_time)
        # mad.receiveVariables(["arr"]*1000)

        # print((mad["arr"] == arr0*2).all())
        # print(mad["arr"])
        # print(mad.variables)

        # arr, arr2, arr3 = mad.receiveVariables(["arr", "arr2", "arr3"])
        # arr, arr2, arr3 = mad["arr", "arr2", "arr3"]
        print((mad["arr"] == arr0*2).all())
        print((mad["arr2"] == arr0*2*2).all())
        print((mad["arr3"] == arr0*2/3).all())
        # arr = None
    print("proc1 ended", time.time() - start_time)
else:
    with MAD(log=False) as mad:
        
        #METHOD 1
        filepath = "/home/joshua/Documents/MAD-NGFork/MAD/examples/ex-fodo-madx/"
        mad.loadsequence("seq", filepath + "fodo.seq")
        mad.beam("beam1")
        mad.seq.beam = mad.beam1
        mad.twiss("mtbl", sequence = mad.seq, method = 4, chrom=True)
        plt.plot(mad.mtbl.s, mad.mtbl["beta11"]) #Showing both methods of retrieving variables
        plt.show()

        #METHOD 2
        mad["circum", "lcell"] = 60, 20
        mad.sendVariables(["circum", "lcell"])
        #WIll add a search into mad for variable in the future
        mad.deferred("v", f = "lcell/math.sin(math.pi/4)/4", k = "1/v.f")
        # mad.multipole("qf", mad.deferedExpr(knl = {0,  mad.v.k}))
        mad.multipole("qf", mad.deferedExpr(knl = "{0,  v.k}"))
        # mad.quadrupole("qf", mad.deferedExpr(k1 = "v.k"), l = 1)
        
        # mad.multipole("qd", mad.deferedExpr(knl = {0, -mad.v.k}))
        mad.multipole("qd", mad.deferedExpr(knl = "{0, -v.k}"))

        # mad.quadrupole("qd", mad.deferedExpr(k1 = "-v.k"), l = 1)
        mad.sequence("seq2", mad.qfSet(at = 0 * mad.lcell),
                            mad.qdSet(at = 0.5 * mad.lcell),
                            mad.qfSet(at = 1 * mad.lcell),
                            mad.qdSet(at = 1.5 * mad.lcell),
                            mad.qfSet(at = 2 * mad.lcell),
                            mad.qdSet(at = 2.5 * mad.lcell), 
                            refer = 'entry', l=mad.circum )
        mad.beam("beam1")
        mad.seq2.beam = mad.beam1
        mad.twiss("mtbl2", sequence = mad.seq2, method = 4, chrom=True, nslice = 10, implicit = True, save = "atbody")
        plt.plot(mad.mtbl2.s, mad.mtbl2["beta11"]) #Showing both methods of retrieving variables
        # print(mad.mtbl2.beta11)
        plt.show()

    
    