# Code that does not necessarily work as expected
import os
from pathlib import Path

import numpy as np

from pymadng import MAD

original_dir = Path.cwd()
os.chdir(Path(__file__).parent)

mad = MAD()  # Not being in context manager makes not difference.

# Just boring setup (in lots of other examples)
mad.MADX.load("'fodo.seq'", "'fodo.mad'")
mad["seq"] = mad.MADX.seq
mad.seq.beam = mad.beam()


# Only one thing is returned from the twiss, a reference (Nothing in python is ever received from MAD after telling MAD-NG to execute)
twissrtrn = mad.twiss(sequence=mad.seq)

# Any high level MAD-NG function will create a reference
mad.MAD.gmath.reim(1.42 + 0.62j)

# Try to receive from twiss
mad["mtbl", "mflw"] = twissrtrn

# mtbl and mflow correctly stored!
print(mad.mtbl)
print(mad.mflw[0])
mad.send(
    "print(mtbl, mflw[1])"
)  # This will print the table and the particle stored in mflw[1] (lua table)

a_matrix = mad.MAD.matrix(4).seq()  # Create 4x4 matrix

print(type(a_matrix))  # Not a 4x4 matrix!
print(type(a_matrix.eval()))  # A 4x4 matrix!

a_matrix = a_matrix.eval()  # Store the matrix permanantly

mad["myMatrix"] = mad.MAD.matrix(4).seq()
print(mad.myMatrix, np.all(a_matrix == mad.myMatrix))

os.chdir(original_dir)
