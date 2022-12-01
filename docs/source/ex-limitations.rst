Limitations
===========

Here I will show an example of potential limitations of the current setup to help show how not to use pymadng.

Here, we perform a twiss to start with (we assume all the correct variables have been defined an setup, so that the twiss runs successfully (see `ex-limitations/ex-limitations.py <https://github.com/MethodicalAcceleratorDesign/MADpy/blob/main/examples/ex-limitations/ex-limitations.py>`_))

However, instead of using the MAD object to define the variable, we simply store the returned variable into a python variable.
The important thing to note here is that when the twiss is evaluated, the function on python returns a **reference**. 
This reference is to a variable that is created whenever you use a high level mad object as a function. Therefore this variable is **very** easy to overwrite, and that is what we are doing in the example below.

The twiss function creates the variable ``__last__`` as the return of twiss, python knows this occurs so returns a **reference** to this variable from the python function. Then when we perform ``reim(1.42 + 0.62j)``, this function also stores the result into ``__last__``, so when ``mad["mtbl", "mflw"] = twissrtrn`` is performed, it sets ``mtbl`` and ``mflw`` to the variables within ``__last__``, which is the return of the most recent function.
Therefore the only way to guarantee that your variable is not overwritten, it must be declared within the MAD-NG environment with ``mad[*args]``

.. literalinclude:: ../../examples/ex-limitations/ex-limitations.py
    :lines: 2, 7-8, 16-27


To remove this protentially problematic method, we would have to always return a unique reference, or within the function call, have to the name of the variable yourself. 

For cases such as the ``reim`` function, you might expect, since it only returns plain data, for the function to return plain data and not a **reference** as this plain data can be replicated very easily in python. However, in this case the function used is extremely generic and has not clue and does not care about the input and output data types. For python to know about the data types, python is required to ask MAD-NG about the return values. If this was done automatically, then one of the more powerful parts of pymadng, receiving information during function calls, would not be possible as python instead would be waiting for details on what the variable type is from MAD-NG, and MAD-NG would not be able to tell python anything until it had completed the function.

Another curious case in which this leads to unexepected behaviour is below.

Here, we create a matrix, however, it has the same problem in that we are calling a function, matrix, which python only returns a **reference**. A benefit of this scenario is that, as we get a reference, not a numpy array, we can still perform MAD-NG functions on this reference. 

It is for cases like this that the ``eval()`` function has been created. For any plain data type, this will return the plain data, however if it is any other object in MAD that cannot be transferred normally, you will still receive a reference.

If we use, the normal syntax of ``mad["myMatrix"] = mad.MAD.matrix(4).seq()``, then we run into no unexepected issues, as ``myMatrix`` is set to the variable ``__last__`` returned by the functions on the right, then, when we retrieve ``myMatrix`` from the MAD environment, we get the plain data as expected.

.. literalinclude:: ../../examples/ex-limitations/ex-limitations.py
    :lines: 29-