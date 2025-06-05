# Code that does not necessarily work as expected
import os

import numpy as np

from pymadng import MAD

original_dir = os.getcwd()
os.chdir(os.path.dirname(os.path.realpath(__file__)))

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

myMatrix = mad.MAD.matrix(4).seq()  # Create 4x4 matrix

print(type(myMatrix))  # Not a 4x4 matrix!
print(type(myMatrix.eval()))  # A 4x4 matrix!

myMatrix = myMatrix.eval()  # Store the matrix permanantly

mad["myMatrix"] = mad.MAD.matrix(4).seq()
print(mad.myMatrix, np.all(myMatrix == mad.myMatrix))

os.chdir(original_dir)
