Breaking Sequencing
===================

Here I will show two examples of problems caused by the breaking of sequencing and so show how not to use pymadng.

Overwriting variables
---------------------

Here, we perform a twiss to start with (we assume all the correct variables have been defined an setup, so that the twiss runs successfully (see `ex-breaking-sequencing/ex-breaking-sequencing.py <https://github.com/MethodicalAcceleratorDesign/MADpy/blob/main/examples/ex-breaking-sequencing/ex-breaking-sequencing.py>`_))

However, instead of using the MAD object to define the variable, with ``mad[*args] = twiss(...)``, we simply store the returned variable into a Python variable.

.. important:: When a function is called from python and executed in MAD-NG, it will **always** return a **reference**. 

When we evaluate the twiss, we create a reference to the return variable, as is the case whenever you use a high level mad object as a function. Therefore, this variable is **very** easy to overwrite (see below).

The twiss function creates the variable ``__last__`` as the return of twiss in the MAD-NG environment, then Python returns a **reference** to this variable from the Python function. Then when we perform ``reim(1.42 + 0.62j)``, this function also stores the result into ``__last__`` in MAD-NG, so when ``mad["mtbl", "mflw"] = twissrtrn`` is performed, in the MAD-NG environment, ``mtbl`` and ``mflw`` are set to the variables within ``__last__``, which is the return of the most recently called function.

.. important:: The only way to guarantee that the variable is not overwritten, it must be declared within the MAD-NG environment with ``mad[*args]``

.. literalinclude:: ../../examples/ex-breaking-sequencing/ex-breaking-sequencing.py
    :lines: 2, 7-8, 16-27

To remove this protentially problematic method, we would have to always return a unique reference or have an argument for the function name within the function call. 

For cases such as the ``reim`` function, you might expect, since it only returns plain data, for the function to return plain data (data that has an identical type in Python) and not a **reference**. However, in this case the function used is extremely generic and is unaware of the input and output data types. *For Python to know about the data types, Python is required to ask MAD-NG about the return values.* If this was done automatically, then one of the more powerful parts of pymadng, receiving data during function calls, would not be possible as Python instead would be waiting for details on what the variable type is from MAD-NG, and MAD-NG would not be able to tell Python anything until it had completed the function.

Retreiving plain data variables from reference
----------------------------------------------

Here, we create a matrix, however, here we are calling a function, ``matrix``, so Python only returns a **reference**. A benefit of this scenario is that, as we get a reference, not a numpy array, we can still perform MAD-NG functions on this reference. 

It is for cases like this that the ``eval()`` function has been created. For any plain data type, this will return the plain data from a function call, however if it is any other object in MAD that cannot be transferred normally, you will still receive a reference.

If we use, the normal syntax of ``mad["myMatrix"] = mad.MAD.matrix(4).seq()``, then we run into no issues, as ``myMatrix`` is set to the variable ``__last__`` returned by the functions on the right, then, when we retrieve ``myMatrix`` from the MAD environment, we get the plain data as expected.

.. important:: The use of ``eval()`` and ``mad[*args] = ...`` requires communication with MAD-NG, so Python will have to wait until MAD-NG has finished executing the function.

.. literalinclude:: ../../examples/ex-breaking-sequencing/ex-breaking-sequencing.py
    :lines: 29-