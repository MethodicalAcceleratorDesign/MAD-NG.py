Low-Level Example Explained
===========================


Sending Multiple types
----------------------

To start, the file `ex-LowLevel/ex-send-multypes.py <https://github.com/MethodicalAcceleratorDesign/MADpy/blob/main/examples/ex-LowLevel/ex-send-multypes.py>`_ imports all the necessary modules, creates a large numpy array, setups the ``mad`` object to communicate with MAD-NG, and then creates a string to send to MAD.

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

The rest of the file shows and tests sending and receiving some of the available types.

Sending and Receiving Large Datasets
------------------------------------

The file `ex-LowLevel/ex-send-recv.py <https://github.com/MethodicalAcceleratorDesign/MADpy/blob/main/examples/ex-LowLevel/ex-send-recv.py>`_ shows sending 960 MB arrays and then receiving manipulated versions of these arrays and verifies the manipulations.

Sending and Receiving Scripts
"""""""""""""""""""""""""""""

Finally we test the receiving scripts and execution, where we find the first script sent to MAD-NG must be executed twice by python, as the first command sends a command back to MAD-NG, which sends a command to be executed by python.

Then the second script explicitly sent to MAD-NG, extends the first script, so that python is required to execute the script 3 times. 

.. literalinclude:: ../../examples/ex-LowLevel/ex-send-recv.py
    :lines: 59-68

On success of both scripts, the print command sent by MAD-NG will only be executed after the explicit print commands, visible in python
