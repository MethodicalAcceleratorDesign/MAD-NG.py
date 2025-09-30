from pathlib import Path

current_dir = str(Path(__file__).resolve().parent) + "/"

filenames = [
    "ex-benchmark-and-fork/ex-benchmark-and-fork.py",
    "ex-fodo/ex-fodos.py",
    "ex-lhc-couplingLocal/ex-lhc-couplingLocal.py",
    "ex-managing-refs/ex-managing-refs.py",
    "ex-LowLevel/ex-send-multypes.py",
    "ex-LowLevel/ex-send-recv.py",
    "ex-ps-twiss/ex-ps-twiss.py",
    "ex-recv-lhc/ex-defexpr.py",
]
for name in filenames:
    print(name)
    env = {"__file__": current_dir + name}
    with Path(name).open("r") as f:
        exec(f.read(), env)


# Cleanup tfs tables (comment out if you would like to read)
for x in Path().iterdir():
    if x.suffix == ".tfs":
        x.unlink()
