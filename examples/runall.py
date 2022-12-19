import os
current_dir = os.path.dirname(os.path.realpath(__file__)) + "/"

filenames = [
    "ex-benchmark-and-fork/ex-benchmark-and-fork.py", "ex-fodo/ex-fodos.py", "ex-lhc-couplingLocal/lhc-couplingLocal.py",
    "ex-managing-refs/ex-managing-refs.py", "ex-LowLevel/ex-send-multypes.py", "ex-LowLevel/ex-send-recv.py", 
    "ex-ps-twiss/ps-twiss.py", "ex-recv-lhc/ex-defexpr.py"
    ]
for name in filenames:
    print(name)
    env = {"__file__": current_dir + name}
    with open(name, "r") as f:
        exec(f.read(), env)


#Cleanup tfs tables (comment out if you would like to read)
for x in os.listdir():
    if x.split(".")[-1] == "tfs":
        os.remove(x)