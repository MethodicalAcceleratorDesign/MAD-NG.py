from pymadng import MAD
import numpy as np
import os, sys, time
import matplotlib.pyplot as plt

current_dir = os.path.dirname(os.path.realpath(__file__)) + "/"

pid = os.fork()
#Test 1
if pid > 0:
    with MAD() as mad:  # open mad process, if you just use mad = MAD(), then be sure to close it afterwords; for multiprocessing, os.fork() can work with the with statement
        arr0 = np.zeros((10000, 1000)) + 1j  # 2*10000*1000*8 -> 160 MB

        # Set variables within the mad class
        start_time = time.time()
        mad["arr"] = arr0
        # print(mad.arr)
        mad["arr2", "arr3", "arr4"] = arr0, arr0, arr0
        print("send large array", time.time() - start_time)

        # Directly send to mad
        # mad.writeToProcess("arr = arr * 2")
        mad.send("arr = arr:mul(2)")
        print((mad["arr"] == arr0 * 2).all())
        mad.send("arr2 = arr * 2")
        mad.send("arr3 = arr / 3")

        # Recieving variables: update retrieves all the variables within the mad class or just send a string and the variable of that name will be retrieved
        start_time = time.time()
        print((mad["arr"] == arr0 * 2).all())
        print((mad["arr2"] == arr0 * 2 * 2).all())
        print((mad["arr3"] == arr0 * 2 / 3).all())
        print("receive large array", time.time() - start_time)

    with MAD() as mad:  # open mad process, if you just use mad = MAD(), then be sure to close it afterwords; for multiprocessing, os.fork() can work with the with statement
        numVars = 25000
        varNameList = []
        values = [12345.0] * numVars
        for i in range(numVars):
            varNameList.append(f"var{i}")

        mad.send(f"myvector = MAD.vector({numVars})")
        start_time = time.time()
        for i in range(numVars):
            mad.send(f"myvector[{i+1}] = py:recv()")
            mad.send(12345.0)
        print(f"send {numVars} vals", time.time() - start_time)

        start_time = time.time()
        mad.send_vars(list(varNameList), values)
        print(f"send {numVars} vals v2", time.time() - start_time)

        start_time = time.time()
        for i in range(numVars):
            mad.send(f"py:send(myvector[{i+1}])")
            mad.recv()
        print(f"receive {numVars} vals", time.time() - start_time)

        start_time = time.time()
        mad.recv_vars(list(varNameList))
        print(f"receive {numVars} vals v2", time.time() - start_time)
    print("proc1 ended", time.time() - start_time)
else:
    with MAD() as mad:
        mad.load("element", "quadrupole")
        # METHOD 1
        mad.MADX.load(f"'{current_dir}fodo.seq'",f"'{current_dir}fodo.mad'")
        mad["seq"] = mad.MADX.seq
        mad.seq.beam = mad.beam()
        mad["mtbl", "mflw"] = mad.twiss(sequence=mad.seq, method=4, chrom=True)
        plt.plot(mad.mtbl.s, mad.mtbl["beta11"])
        plt.show()

        # METHOD 2
        mad["circum", "lcell"] = 60, 20
        mad["deferred"] = mad.MAD.typeid.deferred
        mad["v"] = mad.deferred(f = "lcell/math.sin(math.pi/4)/4", k = "1/v.f")

        mad["qf"] = mad.quadrupole("knl:={0,  v.k}", l = 1)
        mad["qd"] = mad.quadrupole("knl:={0,  -v.k}", l = 1)

        mad.send("""
        seq2 = sequence 'seq2' { refer='entry', l=circum, -- assign to seq in scope!
        qf { at = 0 },
        qd { at = 0.5 * lcell },
        qf { at = 1.0 * lcell },
        qd { at = 1.5 * lcell },
        qf { at = 2.0 * lcell },
        qd { at = 2.5 * lcell },
        }""")
        mad.seq2.beam = mad.beam()
        mad["mtbl2", "mflw2"] = mad.twiss(sequence=mad.seq2, method=4, nslice=10, implicit=True, save="'atbody'")
        plt.plot(mad.mtbl2.s, mad.mtbl2["beta11"])
        plt.show()
        print(mad.mtbl2.header)
    sys.exit()