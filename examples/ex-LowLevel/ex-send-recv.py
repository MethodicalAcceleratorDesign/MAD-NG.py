from pymadng import MAD
import numpy as np
import time, sys

arr0 = np.zeros((10000, 1000)) + 1j# 2*10000*1000*8 -> 160 MB

start_time = time.time()
mad = MAD(debug = False)
# Number one rule! If you ask mad to send you something, read it!
# Don't ask mad to send you data, then try to send more data, this will lead to a deadlock!

mad.send("cm1 = py:recv()") # Tell MAD to receive something 
mad.send(arr0)              # Send the data to MAD

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

# Create a string the manipulates the complex matrix in MAD and sends the result it to Python
cmatrixString = """
    {0} = {0} {1} {2}
    py:send({0})
    """

start_time = time.time()
mad.send(cmatrixString.format("cm1", "*", 2)) # Set cm1 to cm1 * 2 and send it to Python
cm1 = mad.recv()
mad.send(cmatrixString.format("cm2", "*", 2)) # Set cm2 to cm1 * 2 and send it to Python
cm2 = mad.recv()
mad.send(cmatrixString.format("cm3", "/", 3)) # Set cm3 to cm1 / 3 and send it to Python 
cm3 = mad.recv()
mad.send(cmatrixString.format("cm4", "*", 1)) # Set cm4 to cm1 * 1 and send it to Python
cm4 = mad.recv()
mad.send(cmatrixString.format("cm4", "*", 2)) # Set cm4 to cm1 * 1 and send it to Python
cm4 = mad.recv()
mad.send(cmatrixString.format("cm4", "*", 2)) # Set cm4 to cm1 * 1 and send it to Python
cm4 = mad.recv()
print("time to read 960 MB from MAD", time.time() - start_time)

# Check that the data is correct
print(np.all(cm1 == arr0*2))
print(np.all(cm2 == arr0*2))
print(np.all(cm3 == arr0/3))
print(np.all(cm4 == arr0*4))


# Send a string to MAD that will send a string back to Python
mad.send("""
    py:send([=[
mad.send("py:send([[print('pymad success')]])") # Needs to lack indent for python
    ]=])""")
mad.recv_and_exec()
print("On second read:")
mad.recv_and_exec()

mad.send("""
    py:send([==[
mad.send('''py:send([=[
mad.send("py:send([[print('Another pymad success') #This MAD string is executed in Python]])")
    ]=])''')
    ]==])
    """)
mad.recv_and_exec()
mad.recv_and_exec()
print("On third read:")
mad.recv_and_exec()
