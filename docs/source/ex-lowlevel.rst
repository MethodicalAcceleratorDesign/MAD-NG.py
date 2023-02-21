Low-Level Example Explained
===========================


Sending and Receiving Multiple types
------------------------------------

To start, the file :ref:`ex-LowLevel/ex-send-multypes.py <ex-send-multypes>` imports all the necessary modules, creates a large numpy array, setups the ``mad`` object to communicate with MAD-NG, and then creates a string to send to MAD.

The string starting on line 9 below creates a 1000x1000 matrix within MAD-NG and generates the matrix into a sequence, see MAD-NG documentation on `mat:seq <https://madx.web.cern.ch/madx/releases/madng/html/linalg.html#mat:seq>`_ for more details. Then on line 11, MAD-NG is asked to send the matrix back.

.. literalinclude:: ../../examples/ex-LowLevel/ex-send-multypes.py
    :lines: 1-13
    :linenos:


The next section creates a complex matrix in MAD-NG named ``cm1``, then creates and asks MAD-NG to send back to python multiple variations of this complex matrix with calculations performed on them.

.. literalinclude:: ../../examples/ex-LowLevel/ex-send-multypes.py
    :lines: 15-26
    :linenos:


Then the same is done for a single vector of length 45.

.. literalinclude:: ../../examples/ex-LowLevel/ex-send-multypes.py
    :lines: 28-32
    :linenos:

We then receive all of the variables in the same order they were sent, time the transfer and check that the correct calculations we performed. If everything goes well, a time will be followed by four ``True``\ s

.. literalinclude:: ../../examples/ex-LowLevel/ex-send-multypes.py
    :lines: 33-49
    :linenos:

.. important:: The examples above break what we describe as *sequencing*, therefore, if you are not careful with the procedure, you may end up with a **deadlock**. This is because both MAD-NG and python can wait for the other to receive the data that is being sent. See :ref:`below <deadlock>` for more details.

The rest of the ex-send-multypes.py file shows and tests sending and receiving some of the available types.

.. _deadlock:

Creating Deadlocks
------------------

To cause a deadlock, the easiest way is to send and ask for lots of large data without handling the data in python. For example, if we were to ask for a large matrix, and then send another large matrix, without handling the first matrix, then MAD-NG will be waiting for python to receive the first matrix, while python is waiting for MAD-NG to send the second matrix (see below).
 
.. code-block:: python
    
    # Create an array much bigger than 65 kB buffer
    arr0 = np.zeros((10000, 1000)) + 1j
    # Ask MAD-NG to receive data from python
    mad.send('arr = py:recv()') 
    # Send data to MAD-NG
    mad.send(arr0)               

    # Ask MAD-NG to send data back to python.
    # Since this fills the buffer, it will hang until python receives the data
    mad.send('py:send(arr)')     # Danger starts here, as MAD-NG is hanging, waiting for python to receive the data
    arr2 = arr0 * 2              # Manipulate data in python
    
    # Ask MAD-NG to receive more data from python 
    # (this will not be executed until python receives the data from MAD-NG)
    mad.send('arr2 = py:recv()') 
    
    # DEADLOCK! You have now filled the buffer on both sides, 
    # and both are waiting for the other to receive the data, so nothing happens
    mad.send(arr2)               


Sending and Receiving Large Datasets
------------------------------------

The file :ref:`ex-LowLevel/ex-send-recv.py <ex-send-recv>` shows sending 960 MB arrays and then receiving manipulated versions of these arrays and verifies the manipulations. 
This example uses very large datasets, that, if not careful, can cause a deadlock. 

On the first line below, we ask MAD-NG to receive some data from python, and then on the second line, we send the data, if we forget to do this, MAD-NG will error or receive gobbledygook as the contents of the matrix, as it tries to interpret the string on line 4 as a matrix.

.. literalinclude:: ../../examples/ex-LowLevel/ex-send-recv.py
    :lines: 12-16
    :linenos:

.. important::

    Therefore from this and the previous section, the general rules are:
    
    * If you ask MAD-NG to receive data from python, you must immediately send the data to MAD-NG 
    * If you ask MAD-NG to send data to python, you should immediately receive the data from MAD-NG

Sending and Receiving Scripts
"""""""""""""""""""""""""""""

Finally we test the receiving scripts and execution, where we find the first script sent to MAD-NG must be executed twice by python, as the first command sends a command back to MAD-NG, which sends a command to be executed by python.

Then the second script explicitly sent to MAD-NG, extends the first script, so that python is required to execute the script 3 times. 

.. literalinclude:: ../../examples/ex-LowLevel/ex-send-recv.py
    :lines: 61-80

On success of both scripts, the print command sent by MAD-NG will only be executed after the explicit print commands, visible in python
