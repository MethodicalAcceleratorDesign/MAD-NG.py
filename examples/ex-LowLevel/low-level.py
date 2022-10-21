from pymadng import MAD
import numpy as np
import time

mad = MAD()

mad.process.send("""
function madMatrixToPyList(m)
    return "[" .. string.gsub(m:tostring(",", ","), "i", "j") .. "]"
end
""")

matrixString = """
    local m1 = MAD.matrix(1000, 1000):seq()
    py:send(string.format([[
m1 = np.array(%s).reshape(1000, 1000) #Indents can be annoying...
    ]], madMatrixToPyList(m1)))"""

mad.process.send(matrixString)

cmatrixString = """
    local cm1 = MAD.cmatrix(1000, 1000):seq()
    py:send(string.format([[
cm1 = np.array(%s).reshape(1000, 1000) #Indents can be annoying...
    ]], madMatrixToPyList(cm1)))"""

mad.process.send(cmatrixString)

vectorString = """
local v1 = (MAD.vector(45):seq()*2 + 1)/3
py:send(string.format([[
v1 = np.array(%s).reshape(45, 1)
    ]], madMatrixToPyList(v1)))
"""
mad.process.send(vectorString)


mad.process.read()
print(m1)

mad.process.read()
print(cm1)

mad.process.read()
print(v1)