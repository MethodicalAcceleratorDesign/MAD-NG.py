from pymadng import MAD
import numpy as np
import time, sys

arr0 = np.zeros((10000, 1000)) + 1j# 2*10000*1000*8 -> 160 MB

start_time = time.time()
mad = MAD(debug = False)

strArr0 = arr0.tobytes()
mad.send(f"cm1 = py:read_cmat({arr0.shape[0]}, {arr0.shape[1]}, {len(strArr0)})")
mad.process.process.stdin.write(strArr0)

cmatrixString = """
    {0} = cm1 {1} {2}
    py:send_mat({0}, '{0}')
    """

mad.send(cmatrixString.format("cm4", "*", 1))
mad.send(cmatrixString.format("cm4", "*", 1))
mad.send(cmatrixString.format("cm4", "*", 1))
mad.send(cmatrixString.format("cm1", "*", 2))
mad.send(cmatrixString.format("cm2", "*", 2))
mad.send(cmatrixString.format("cm3", "/", 3))

cm4 = mad.read()["cm4"]
cm4 = mad.read()["cm4"]
cm4 = mad.read()["cm4"]
cm1 = mad.read()["cm1"]
cm2 = mad.read()["cm2"]
cm3 = mad.read()["cm3"]

# # v1 = mad.read()["v1"]
# # print(v1)
print(time.time() - start_time)
# # print(m1)
print(np.all(cm1 == arr0*2))
print(np.all(cm2 == arr0*2*2))
print(np.all(cm3 == arr0*2/3))
print(np.all(cm4 == arr0))
