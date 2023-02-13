FODO Examples Explained
=======================

The file :ref:`ex-fodo/ex-fodos.py <ex-fodo>` has several methods of loading the same FODO cell and then plotting :math:`s` and :math:`\beta_{xx}` (known as beta11 in MAD-NG).

For the simplest low level example, see :ref:`here <low-level>`

Simple (higher level) example
-----------------------------

The first example (below) shows how to load a MADX sequence, perform a twiss on it in MAD-NG and then plot :math:`s` and :math:`\beta_{xx}`.

Important points from this examples includes the ``mad[*args]`` notation and the use of double quotations in the function call ``mad.MADX.load(...)``. The notation ``mad[*args]`` is a method of creating variables within the MAD-NG environment from python variables. The double quotes in the load function are required because strings are interpreted by MAD-NG as scripts, allowing the use of variables in the string.

So going through the example line by line;

    1. Start MAD-NG and name the communication object ``mad``
    2. Load the MADX sequence in the file `fodo.seq <https://github.com/MethodicalAcceleratorDesign/MADpy/blob/main/examples/ex-fodo/fodo.seq>`_ and store the translation into `fodo.mad <https://github.com/MethodicalAcceleratorDesign/MADpy/blob/main/examples/ex-fodo/fodo.mad>`_.
    3. Grab the variable ``seq`` from the MADX environment and give it the name ``seq`` in the MAD-NG environment.
    4. Create the default beam object and attach this to the sequence ``seq``.
    5. Run a twiss (the last three arguments are equivalent to the MADX ``plot "interpolate"``) and name the return values ``mtbl`` and ``mflw`` in the MAD-NG environment.
    6. Create the plot of :math:`s` and :math:`\beta_{xx}`.
    7. Display the plot.

.. literalinclude:: ../../examples/ex-fodo/ex-fodos.py
    :lines: 7-13
    :linenos:

Different (higher level) example
--------------------------------

Going through the example line by line (ignoring lines that have been explained above);


    3. Essentially the same as line 3 in the example above, yet this time you don't control the naming in the MAD-NG environment, equivalent to ``seq = MADX.seq`` in MAD-NG.

    6. Create a variable cols, for use in the next line. The use of ``py_strs_to_mad_strs`` adds quotes around every string in the list, so that they are interpreted as strings in MAD-NG.
    7. Write the columns above to the file twiss_py.tfs
    8. Loop through the elements of the sequence
    9. Print the name and kind of element in the sequence


.. literalinclude:: ../../examples/ex-fodo/ex-fodos.py
    :lines: 15-25
    :linenos:

Lines 8 - 9 are equivalent to 

.. code-block::

    for i in range(len(mad.seq)): 
        x = mad.seq[i]
        print(x.name, x.kind)

Creating a sequence from Python
-------------------------------

In this example, we demonstrate creating a sequence from scratch in MAD-NG from python.
 
Going through the example line by line;

    1. Load the element ``quadrupole`` from the module ``element`` in MAD-NG, making it available directly, equivalent to the python syntax ``from element import quadrupole``.
    2. Create two variables in the MAD-NG environment, ``circum = 60``, ``lcell = 20``.

    3. Create two variables in the MAD-NG environment, ``sin = math.sin``, ``pi = math.pi`` (in Python this is equivalent to ``from math import sin, pi``).
    4. Create a deferred expression equivalent to ``v := 1/(lcell/sin(pi/4)/4)`` in MAD-X.

    5. Create a quadrupole named ``qf`` with ``k1 = v.k`` and length of 1.
    6. Create a quadrupole named ``qd`` with ``k1 = -v.k`` and length of 1.
    7. Create a sequence using ``qf`` and ``qd``, specifying the positions and a length of 60.

    8.  Attach a default beam to the sequence.
    9.  Run a twiss and name the return values ``mtbl`` and ``mflw`` in the MAD-NG environment.

    10. Write the columns ``col`` to the file twiss_py.tfs.

    11. Plot the result (``mad.mtbl["beta11"]`` is equivalent to ``mad.mtbl.beta11``).

.. literalinclude:: ../../examples/ex-fodo/ex-fodos.py
    :lines: 28-54
    :linenos:


.. _low-level:

Pure low level example
----------------------

This is the simplest way to communicate with MAD-NG, but it requires the user to actively, deal with references and sending and receiving of specific data. In this example, three methods of receiving data are shown.

Going through the example line by line;

    2. Send a string with the instructions (from the above examples) to load a sequence, attach the default beam and perform a twiss, then send to Python ``mtbl``.

    9. Recieve the object ``mtbl`` from MAD-NG. As this is an object that cannot be replicated in Python, you receive a **reference**. This **reference** must be named the name of the variable in the MAD-NG environment (done within the call of the ``recv`` function), so that you can use the reference to communicate with MAD-NG.
    10. Using the **reference**, grab the attributes ``s`` and ``beta11`` and plot them

    12. Ask MAD-NG to send the attributes ``s`` and ``beta11``. (Instead of dealing with the reference, we send the attributes that can be received in Python directly, see this :ref:`table <typestbl>` for more information on these types)
    13. Receive and plot the attributes ``s`` and ``beta11``.

    15. Using the MAD-NG object, grab the variable ``mtbl`` and then the attributes ``s`` and ``beta11`` to plot them (as above)

.. literalinclude:: ../../examples/ex-fodo/ex-fodos.py
    :lines: 56-73
    :linenos: