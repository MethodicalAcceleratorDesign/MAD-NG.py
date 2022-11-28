Low-Level Example Explained
===========================


Sending Multiple types
----------------------

To start, we import all the necessary modules, create a large numpy array, setup the ``mad`` object to communicate with MAD-NG, and then create a string to send to MAD.

.. literalinclude:: ../../examples/ex-LowLevel/ex-send-multypes.py
    :lines: 1-12
    :linenos:

The string ``matrixString`` creates a 1000x1000 matrix within MAD-NG and generates the matrix into a sequence, see MAD-NG documentation on :seq for more details. Then on line 11, MAD-NG is asked to send the matrix back.

The next section creates a complex matrix in MAD-NG named ``cm1``. Then creates and sends back to python multiple variations of this complex matrix with calculations performed on them.

.. literalinclude:: ../../examples/ex-LowLevel/ex-send-multypes.py
    :lines: 14-23
    :linenos:


Then the same is done for a single vector of length 45.

.. literalinclude:: ../../examples/ex-LowLevel/ex-send-multypes.py
    :lines: 25-28
    :linenos:

We then receive all of the variables in the same order they were sent, time the transfer and check that the correct calculations we performed. If everything goes well, a time will be followed by four ``True``\ s

.. literalinclude:: ../../examples/ex-LowLevel/ex-send-multypes.py
    :lines: 29-42
    :linenos:

