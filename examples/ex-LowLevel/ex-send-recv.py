from pymadng import MAD
import numpy as np
import time, sys

arr0 = np.zeros((10000, 1000)) + 1j# 2*10000*1000*8 -> 160 MB

start_time = time.time()
mad = MAD(debug = False)
# Number one rule! If you ask mad to send you something, read it!
# Don't ask mad to send you data, then try to send more data, this will lead to a deadlock!
mad.send("cm1 = py:recv()")
mad.send(arr0)

mad.send("cm2 = py:recv()")
mad.send(arr0)

mad.send("cm3 = py:recv()")
mad.send(arr0)

mad.send("cm4 = py:recv()")
mad.send(arr0)

mad.send("cm4 = py:recv()")
mad.send(arr0)

mad.send("cm4 = py:recv()")
mad.send(arr0)

print("time to write to MAD 960 MB", time.time() - start_time)
start_time = time.time()

cmatrixString = """
    {0} = {0} {1} {2}
    py:send({0})
    """

start_time = time.time()
mad.send(cmatrixString.format("cm1", "*", 2))
cm1 = mad.recv()
mad.send(cmatrixString.format("cm2", "*", 2))
cm2 = mad.recv()
mad.send(cmatrixString.format("cm3", "/", 3))
cm3 = mad.recv()
mad.send(cmatrixString.format("cm4", "*", 1))
cm4 = mad.recv()
mad.send(cmatrixString.format("cm4", "*", 2))
cm4 = mad.recv()
mad.send(cmatrixString.format("cm4", "*", 2))
cm4 = mad.recv()
print("time to read 960 MB from MAD", time.time() - start_time)


print(np.all(cm1 == arr0*2))
print(np.all(cm2 == arr0*2))
print(np.all(cm3 == arr0/3))
print(np.all(cm4 == arr0*4))


mad.send("""py:send([=[mad.send("py:send([[print('pymad success')]])")]=])""")
mad.recv_and_exec()
print("On second read:")
mad.recv_and_exec()

mad.send("""py:send([==[mad.send('''py:send([=[mad.send("py:send([[print('Another pymad success')]])")]=])''')]==])""")
mad.recv_and_exec()
mad.recv_and_exec()
print("On third read:")
mad.recv_and_exec()
