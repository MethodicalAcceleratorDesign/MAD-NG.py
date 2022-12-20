FODO Examples Explained
=======================

The file `ex-fodo/ex-fodos.py <https://github.com/MethodicalAcceleratorDesign/MADpy/blob/main/examples/ex-fodo/ex-fodos.py>`_ has several methods of loading the same FODO cell and then plotting :math:`s` and :math:`\beta_{xx}` (known as beta11 in MAD-NG).

For the simplest low level example, see :ref:`here <low-level>`

Simple (higher level) example
-----------------------------

The first example (below) shows how to load a MADX sequence, perform a twiss on it in MAD-NG and then plot :math:`s` and :math:`\beta_{xx}`. A minor potential confusing bit is the use of ``{current_dir}``, now this just ensures MAD-NG gets the full correct path to the file, if your terminal is in the folder with the python files and sequence files, this is not required, but I have included it so that you can run the python file from anywhere on your device.

Important points to note are the use of double quotations in the ``mad.MADX.load(...)`` and ``mad[*args]`` notation. The double quotes are required because strings are interpreted by MAD-NG as scripts, which we believe is powerful enough that we will accept the minor annoyance of using double quotes. The notation ``mad[*args]`` is how to define variables within the MAD-NG environment.

So going through line by line;

    1. Open MAD-NG and name the communication object ``mad``
    2. Load the MADX sequence in the file `fodo.seq <https://github.com/MethodicalAcceleratorDesign/MADpy/blob/main/examples/ex-fodo/fodo.seq>`_ and store the translation into `fodo.mad <https://github.com/MethodicalAcceleratorDesign/MADpy/blob/main/examples/ex-fodo/fodo.mad>`_.
    3. Grab the variable ``seq`` from the MADX environment and give it the name ``seq`` in the MAD-NG environment.
    4. Create the default beam object and attach this to the sequence ``seq``.
    5. Run a twiss (the last three arguments are equivalent to the MADX ``plot "interpolate"``) and name the return values ``mtbl`` and ``mflw`` in the MAD-NG environment.
    6. Create the plot of :math:`s` and :math:`\beta_{xx}`.
    7. Display the plot.

.. literalinclude:: ../../examples/ex-fodo/ex-fodos.py
    :lines: 6-12
    :linenos:

Different (higher level) example
--------------------------------

Going through the example line by line;


    3. Equivalent to line 3 in the example above, yet this time you have no control on the name in MAD-NG environment.

    6. Create a variable cols, for use in the next line
    7. Write the columns above to the file twiss_py.tfs
    8. Loop through the elements of the sequence
    9. Print the name and kind of element in the sequence


.. literalinclude:: ../../examples/ex-fodo/ex-fodos.py
    :lines: 14-24
    :linenos:

Lines 8 - 9 are equivalent to 

.. code-block::

    for i in range(len(mad.seq)): 
        x = mad.seq[i]
        print(x.name, x.kind)

Creating a sequence from Python
-------------------------------

In this example, we demonstrate, why double quotations may be a decent compromise to make, by being able to completely utilise MAD-NG.
 
Going through the example line by line;

    2. Load the element ``quadrupole`` from the module ``element`` in MAD-NG, making it available directly, equivalent to ``from element import quadrupole``.
    3. Create two variables in the MAD-NG environment, ``circum = 60``, ``lcell = 20``.

    5. Create two variables in the MAD-NG environment, ``sin = math.sin``, ``pi = math.pi`` (in Python this is equivalent to ``from math import sin, pi``).
    6. Create a deferred expression equivalent to ``v := 1/(lcell/sin(pi/4)/4)``.

    8. Create a quadrupole named ``qf`` with ``k1 = v.k`` and length of 1.
    9. Create a quadrupole named ``qd`` with ``k1 = -v.k`` and length of 1.
    10. Create a sequence using ``qf`` and ``qd``, specifying the positions and a length of 60.

    18. Attach a default beam to the sequence.
    19. Run a twiss and name the return values ``mtbl`` and ``mflw`` in the MAD-NG environment.

    21. Write the columns ``col`` to the file twiss_py.tfs.

    23. Plot the result (``mad.mtbl["beta11"]`` is equivalent to ``mad.mtbl.beta11``).

.. literalinclude:: ../../examples/ex-fodo/ex-fodos.py
    :lines: 27-53
    :linenos:


.. _low-level:

Pure low level example
----------------------

This is the simplest way to communicate with MAD-NG, but it requires the user to actively, deal with references. In this example, three methods of receiving data are shown.

Going through the example line by line;

    2. Send the entire instructions from the above examples, loading the sequence, attaching the default beam and performing the twiss, then send to Python ``mtbl``.

    9. Recieve the object ``mtbl`` from MAD-NG. As this is an object that cannot be replicated in Python, you receive a **reference**. This **reference** must be named the name of the variable in the MAD-NG environment, so that you can use the reference to communicate with MAD-NG.
    10. Using the **reference**, grab the attributes ``s`` and ``beta11`` and plot them

    12. Ask MAD-NG to send the attributes ``s`` and ``beta11``.
    13. Receive and plot the attributes ``s`` and ``beta11``.

    15. Using the MAD-NG object, grab the variable ``mtbl`` and then the attributes ``s`` and ``beta11`` to plot them (as above)

.. literalinclude:: ../../examples/ex-fodo/ex-fodos.py
    :lines: 55-72
    :linenos: