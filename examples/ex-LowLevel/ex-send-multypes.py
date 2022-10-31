from pymadng import MAD
import numpy as np
import time

arr0 = np.zeros((10000, 1000)) + 1j  # 2*10000*1000*8 -> 160 MB

mad = MAD(debug = False)

matrixString = """
    local m1 = MAD.matrix(1000, 1000):seq()
    py:send_data(m1, 'm1')"""
mad.send(matrixString)

mad.send("cm1 = (MAD.cmatrix(10000, 1000) + 1i)")

cmatrixString = """
    {0} = cm1 {1} {2}
    py:send_data({0}, '{0}')"""

mad.send(cmatrixString.format("cm4", "*", 1))
mad.send(cmatrixString.format("cm1", "*", 2))
mad.send(cmatrixString.format("cm2", "*", 2))
mad.send(cmatrixString.format("cm3", "/", 3))

vectorString = """
local v1 = (MAD.vector(45):seq()*2 + 1)/3
py:send_data(v1, 'v1')"""
mad.send(vectorString)
start_time = time.time()

m1 = mad.read()["m1"]
cm4 = mad.read()["cm4"]
cm1 = mad.read()["cm1"]
cm2 = mad.read()["cm2"]
cm3 = mad.read()["cm3"]
v1 = mad.read()["v1"]



print(time.time() - start_time)
print(np.all(cm1 == arr0*2))
print(np.all(cm2 == arr0*2*2))
print(np.all(cm3 == arr0*2/3))
print(np.all(cm4 == arr0))
# print(v1, m1)