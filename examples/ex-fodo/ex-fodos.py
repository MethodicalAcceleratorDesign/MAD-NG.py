import os

import matplotlib.pyplot as plt

from pymadng import MAD

original_dir = os.getcwd()
os.chdir(os.path.dirname(os.path.realpath(__file__)))

# The typical way to communicate with MAD-NG is to use the send and recv methods.
with MAD() as mad:
    mad.send("""
    MADX:load("fodo.seq", "fodo.mad")
    local seq in MADX
    seq.beam = beam -- use default beam
    mtbl, mflw = twiss {sequence=seq, implicit=true, nslice=10, save="atbody"}
    py:send(mtbl)
    """)
    mtbl = mad.recv("mtbl")
    plt.plot(mtbl.s, mtbl.beta11, "r-", label="Method 1")

    mad.send("""py:send(mtbl.s) ; py:send(mtbl.beta11)""")
    plt.plot(
        mad.recv(),
        mad.recv(),
        "g--",
        label="Method 2",
    )

    plt.plot(mad.mtbl.s, mad.mtbl.beta11, "b:", label="Method 3")

    plt.legend()
    plt.show()

# If you prefer to use pythonic syntax, the following code is equivalent to the above (- some plotting)(+ writing to a file)
with MAD() as mad:
    mad.MADX.load("'fodo.seq'", "'fodo.mad'")
    mad.load("MADX", "seq")
    mad.seq.beam = mad.beam()
    mad["mtbl", "mflw"] = mad.twiss(
        sequence=mad.seq, implicit=True, nslice=10, save="'atbody'"
    )
    cols = mad.quote_strings(
        ["name", "s", "beta11", "beta22", "mu1", "mu2", "alfa11", "alfa22"]
    )
    mad.mtbl.write("'twiss_py.tfs'", cols)

    for x in mad.seq:  # If an object is iterable, it is possible to loop over it
        print(x.name, x.kind)

    plt.plot(mad.mtbl.s, mad.mtbl.beta11)
    plt.show()

os.chdir(original_dir)
