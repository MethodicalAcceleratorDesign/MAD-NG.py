Managing References
===================

Creating temporary variables
----------------------------

Within :numref:`init-listing`, we perform a twiss to begin with (we assume all the correct variables have been defined and setup, so that the twiss runs successfully (see :ref:`ex-managing-refs/ex-managing-refs.py <ex-managing-refs>`)

However, in this example, instead of using the MAD object to define the variable, with ``mad[*args] = twiss(...)``, we simply store the returned variable into a Python variable.

.. important:: When a function is called from python and executed in MAD-NG, it will **always** return a **reference**. 

When we evaluate the twiss, we create a reference to a temporary return variable (a temporary reference), as is the case whenever you use a high level mad object as a function. [#f1]_ There is only a limited amount of these temporary references, by default the limit is set to 8, this should be plenty, yet it is possibleto increase this number with setting ``num_temp_vars`` in the ``__init__``. The more temporary variables you use at once, the slower MAD will become to retreive and set variables, therefore 8 is only a limit so you cannot slow the code by creating too many temporary variables. 

The twiss function creates the temporary variable as the return of twiss in the MAD-NG environment, then Python returns a **reference** to this temporary variable from the Python function. When we perform ``reim(1.42 + 0.62j)``, the result is stored in a different temporary variable, but is cleared immediately since it has no python reference. When ``mad["mtbl", "mflw"] = twissrtrn`` is performed, in the MAD-NG environment, ``mtbl`` and ``mflw`` are set to the variables returned from the twiss. However, in Python, ``twissrtrn`` is still a reference to the temporary variable created by the twiss function, so it is recommended to clear the temporary variable by deleting the python object with ``del twissrtrn``.

.. important:: In general, we recommend not storing temporary variables in python, instead set them in the MAD-NG environment using the syntax ``mad[*args]``. Temporary variables are only useful when you wish to delay communication with MAD-NG, see an example on line 48 `here <ex-lhc>`_.

.. literalinclude:: ../../examples/ex-managing-refs/ex-managing-refs.py
    :lines: 2, 7-8, 16-27
    :caption: Initializing MAD-NG and performing a twiss
    :name: init-listing

For cases such as the ``reim`` function, you might expect, since it only returns plain data, for the function to return plain data (data that has an identical type in Python) and not a **reference**. However, in pymadng, the functions used are extremely generic and are unaware of the input and output data types. *For Python to know about the data types, Python is required to ask MAD-NG about the return values.* If this was done automatically, then one of the more powerful parts of pymadng, receiving data during function calls, would not be possible as Python instead would be waiting for details on what the variable type is from MAD-NG, and MAD-NG would not be able to tell Python anything until it had completed the function.

Retreiving plain data variables from reference
----------------------------------------------

In this part, we create a matrix, where we are calling a function, ``matrix``, therefore, Python only returns a **reference**. A benefit of this scenario is that, as we get a reference, not a numpy array, we can still perform MAD-NG functions on this reference. 

It is for cases like this that the ``eval()`` function has been created. For any plain data type, this will return the plain data from a function call, however if it is any other object in MAD that cannot be transferred normally, you will still receive a reference that you can continue to use to communicate with MAD-NG.

If we use the normal syntax of ``mad["myMatrix"] = mad.MAD.matrix(4).seq()``, then ``myMatrix`` is set to the temporary variable returned by the functions on the right (which is cleared immediately due to the lack of python reference), then, when we retrieve ``myMatrix`` from the MAD environment, we get the plain data as expected.

.. important:: The use of ``eval()`` and ``mad[*args] = ...`` requires communication with MAD-NG, so Python will have to wait until MAD-NG has finished executing the function.

.. literalinclude:: ../../examples/ex-managing-refs/ex-managing-refs.py
    :lines: 29-
    :caption: Creating a matrices and retrieving the data

.. [#f1] This reference has **no** information on the result of the function call, instead, we receive the information when the reference is queried.