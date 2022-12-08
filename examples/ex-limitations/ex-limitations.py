#Code that does not necessarily work as expected
from pymadng import MAD
import os, numpy as np

current_dir = os.path.dirname(os.path.realpath(__file__)) + "/"

mad = MAD() #Not being in context manager makes not difference.

#Just boring setup (in lots of other examples)
mad.MADX.load(f"'{current_dir}fodo.seq'", f"'{current_dir}fodo.mad'")
mad["seq"] = mad.MADX.seq
mad.seq.beam = mad.beam()

#Interesting bit!!

#Only one thing is returned from the twiss, a reference (Nothing in python is ever received from MAD after telling MAD-NG to execute)
twissrtrn = mad.twiss(sequence=mad.seq, method=4)

#Do any function (specificially I chose an example with 2 return values)
mad.MAD.gmath.reim(1.42 + 0.62j)

#Try to receive from twiss
mad["mtbl", "mflw"] = twissrtrn

# mtbl and mflow actually become result of reim function!   
print(mad.mtbl, mad.mtbl == 1.42)
print(mad.mflw, mad.mflw == 0.62)

myMatrix = mad.MAD.matrix(4).seq() #Create 4x4 matrix

print(type(myMatrix)) #Not a 4x4 matrix!
print(type(myMatrix.eval())) #A 4x4 matrix!

myMatrix = myMatrix.eval() #Store the matrix permanantly

mad["myMatrix"] = mad.MAD.matrix(4).seq()
print(mad.myMatrix, np.all(myMatrix == mad.myMatrix))