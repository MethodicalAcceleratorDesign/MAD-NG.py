from pymadng import MAD
import numpy as np
import time

arr0 = np.zeros((10000, 1000)) + 1j  # 2*10000*1000*8 -> 160 MB

mad = MAD()

## Create a matrix in MAD and send it to Python
mad.send("""
    local m1 = MAD.matrix(1000, 1000):seq()
    py:send(m1)
    """)

## Create a complex matrix in MAD
mad.send("cm1 = (MAD.cmatrix(10000, 1000) + 1i)")

# Create a string the manipulates the complex matrix in MAD and sends the result it to Python
cmatrixString = """
    {0} = cm1 {1} {2}
    py:send({0})"""

mad.send(cmatrixString.format("cm4", "*", 1)) ## Set cm4 to cm1 * 1 and send it to Python
mad.send(cmatrixString.format("cm1", "*", 2)) ## Set cm1 to cm1 * 2 and send it to Python
mad.send(cmatrixString.format("cm2", "*", 2)) ## Set cm2 to cm1 * 2 and send it to Python
mad.send(cmatrixString.format("cm3", "/", 3)) ## Set cm3 to cm1 / 3 and send it to Python

## Create a vector in MAD and send it to Python
mad.send("""
    local v1 = (MAD.vector(45):seq()*2 + 1)/3
    py:send(v1)
    """)
start_time = time.time() # Start timer

# Receive the matrices and vectors
m1 = mad.recv() 
cm4 = mad.recv()
cm1 = mad.recv()
cm2 = mad.recv()
cm3 = mad.recv()
v1 = mad.recv()

print(time.time() - start_time) # Print time

# Check if the matrices have been correctly sent
print(np.all(cm1 == arr0*2)) 
print(np.all(cm2 == arr0*2*2))
print(np.all(cm3 == arr0*2/3))
print(np.all(cm4 == arr0))

# Send a list to MAD and receive a changed version back
myList = [[1, 2, 3, 4, 5, 6, 7, 8, 9]] * 2
mad.send("""
local list = py:recv()
list[1][1] = 10
list[2][1] = 10
py:send(list)
""")
mad.send(myList)
myList[0][0] = 10
myList[1][0] = 10
print("receiving lists", mad.recv() == myList)

# Send an integer to MAD and receive a changed version back
myInt = 4
mad.send("""
local myInt = py:recv()
py:send(myInt+2)
""")
mad.send(myInt)
print("Integers", mad.recv() == 6)

# Send a float to MAD and receive a changed version back
myFloat = 6.612
mad.send("""
local myFloat = py:recv()
py:send(myFloat + 0.56)
""")
mad.send(myFloat)
print("Floats", mad.recv() == 6.612 + 0.56)

# Send a complex number to MAD and receive a changed version back
myCpx = 6.612 + 4j
mad.send("""
local myCpx = py:recv()
py:send(myCpx + 0.5i)
""")
mad.send(myCpx)
print("Complex", mad.recv() == 6.612 + 4.5j)

# Send None to MAD and it back
mad.send("""
local myNil = py:recv()
py:send(myNil)
""")
mad.send(None)
print("Nil/None", mad.recv() == None)

# Receive ranges from MAD
mad.send("""
py:send(3..11..2)
py:send(MAD.nrange(3.5, 21.4, 12))
py:send(MAD.nlogrange(1, 20, 20))
""")
print("irng", mad.recv() == range(3  , 12  , 2)) #Py not inclusive, mad is
print("rng", mad.recv() == np.linspace(3.5, 21.4, 12))
print("lrng", np.allclose(mad.recv(), np.geomspace(1, 20, 20)))