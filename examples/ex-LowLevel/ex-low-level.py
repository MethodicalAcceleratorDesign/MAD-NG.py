from pymadng import MAD
import numpy as np
import time

mad = MAD(debug = True)

mad.send("""
function madMatrixToPyList(m)
    return "[" .. string.gsub(m:tostring(",", ","), "i", "j") .. "]"
end
""")

matrixString = """
    local m1 = MAD.matrix(1000, 1000):seq()
    py:send(string.format([[
m1 = np.array(%s).reshape(1000, 1000)
    ]], madMatrixToPyList(m1)))"""

mad.send(matrixString)

cmatrixString = """
    local cm1 = MAD.cmatrix(1000, 1000):seq()
    py:send(string.format([[
cm1 = np.array(%s).reshape(1000, 1000) 
    ]], madMatrixToPyList(cm1)))"""

mad.send(cmatrixString)

vectorString = """
local v1 = (MAD.vector(45):seq()*2 + 1)/3
py:send(string.format([[
v1 = np.array(%s).reshape(45, 1)
    ]], madMatrixToPyList(v1)))
"""
mad.send(vectorString)

m1 = mad.read()["m1"]
# print(m1)

cm1 = mad.read()["cm1"]
# print(cm1)

v1 = mad.read()["v1"]
# print(v1)