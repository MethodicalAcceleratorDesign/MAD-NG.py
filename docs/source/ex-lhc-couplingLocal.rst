LHC Example
===========

.. contents::
   :local:
   :depth: 2

The file :ref:`ex-lhc-couplingLocal/ex-lhc-couplingLocal.py <ex-lhc>` contains an example of loading the required files to use and run the LHC, while including a method to receive and plot intermediate results of a match.

Loading the LHC 
---------------

The following lines loads the required variables and files for the example. ``assertf`` is not required, but it is used to check if the loading of the LHC is successful. The two string inputs to ``mad.MADX.load`` is also not required, but it is used to specify the final destination of the translated files from MAD-X to MAD-NG. Also, line 5 is not required as this is just to prevent MAD-NG from reporting warnings of unset variables from loading the LHC. Once again, in this extract, the important point to note is that to input strings into functions in MAD-NG, they must be enclosed in quotes. This is because any string input from the side of python is evaluated by MAD-NG, therefore the input can be a variable or expressions.

To grab variables from the MAD-X environment, we use ``mad.load("MADX", ...)``.

.. literalinclude:: ../../examples/ex-lhc-couplingLocal/ex-lhc-couplingLocal.py
    :lines: 20-28
    :linenos:

Receving intermediate results
-----------------------------

The most complicated part of the example includes the following set of lines. 

From lines 4 - 8 below, we define a function that will be invoked during the optimization process at each iteration. Within this function, we perform a twiss for the match function to use, while also sending some information on the twiss to python, on line 6. 

From lines 10 - 23, we run a match, with a **reference** to the match result returned to the variable ``match_rtrn``. Line 24 is a very important line, as this is something you place in the pipe to MAD-NG for MAD-NG to execute once the match is done. Lines 23-25 receive the first result returned during the match, so that we can start plotting the results.

The plotting occurs between lines 29 - 38, wtih the while loop continuing until twiss result is ``None``, which occurs when the match is done, as requested on line 24.

Finally, on lines 40 and 41, we retrieve the results of the match from the variable ``match_rtrn``. Since ``match_rtrn`` is a *temporary variable*, there is a limit to how many of these that can be stored (see :doc:`/advanced_features` for more information on these), we delete the reference in python to clear the temporary variable so that is is available for future use.

.. important::
    As MAD-NG is running in the background, the variable ``match_rtrn`` contains *no* information and instead must be queried for the results. During the query, python will then have to wait for MAD-NG to finish the match, and then return the results. On the other hand, if we do not query for the results, the match will continue to run in the background, we can do other things in python, and then query for the results later.

.. literalinclude:: ../../examples/ex-lhc-couplingLocal/ex-lhc-couplingLocal.py
    :lines: 50-90
    :linenos:

.. LHC Speed Tests
.. ---------------

.. This file creates functions within MAD-NG, ``LHC_load``, which loads the LHC and ``reg_expr``, which looks through the MADX environment and places anything that is a deferred expression into the table ``expr``.

.. The ``LHC_load`` function sends a string ``"done"`` afterwards, so that Python can stay in sync and time the LHC correctly.

.. The code below just runs the function and times it.

.. .. literalinclude:: ../../examples/ex-recv-lhc/ex-defexpr.py
..     :lines: 44-47


.. The ``reg_expr`` fucntion is recursive so, after calling the function, to ensure Python stays in sync, Python is required to ask MAD-NG for the string ``"done"``.

.. .. literalinclude:: ../../examples/ex-recv-lhc/ex-defexpr.py
..     :lines: 50-53

.. Next, we have the first of two methods to evaluate every deferred expression in the LHC and receive them, where Python performs a loop through the number of deferred expressions and has to ask MAD-NG everytime to receive the result.

.. .. literalinclude:: ../../examples/ex-recv-lhc/ex-defexpr.py
..     :lines: 60-64

.. The second method involves making MAD-NG do a loop at the same time as python and therefore does not require back on forth communication, which speeds up the transfer of data

.. .. literalinclude:: ../../examples/ex-recv-lhc/ex-defexpr.py
..     :lines: 67-71

.. The two methods above do not store the data, so the next bit of code is identical to above, but uses list comprehension to store the data into a list automatically, storing the lists into variables ``exprList1`` and ``exprList2``. The main point of seperating the methods above and below was to identify if storing the variables into a list was a bottleneck.

.. .. literalinclude:: ../../examples/ex-recv-lhc/ex-defexpr.py
..     :lines: 74-77, 79-83


.. While we have the LHC loaded, the next example grabs the name of every element in the sequence ``lhcb1``, demonstrating the ability and speed of pymadng and MAD-NG, other attributes could also be grabbed, but for simplicity this code just gets the names. This bit of code also uses list comprehension while making MAD-NG loop at the same time as Python.

.. .. literalinclude:: ../../examples/ex-recv-lhc/ex-defexpr.py
..     :lines: 89-99

.. Another method, not shown above could be to create an entire list on the side of MAD-NG and then send the entire list to python. Which is done below, where instead all the names from the sequence ``lhcb2`` are taken from MAD-NG.

.. .. literalinclude:: ../../examples/ex-recv-lhc/ex-defexpr.py
..     :lines: 104-114

.. You can run the file yourself to retrieve the timings, but below is one run on an Intel® Core™ i7-8550U CPU @ 1.80GHz × 8 in Ubuntu 22.04.1 LTS

.. .. code-block:: console

..     Load time: 0.3955872058868408  sec
..     reg_expr time: 0.034337759017944336  sec

.. For evaluating the deferred expressions

.. .. code-block:: console

..     eval time method 1: 0.5888900756835938  sec
..     eval time method 2: 0.2224569320678711  sec
..     eval time method 3: 0.6652431488037109  sec
..     eval time method 4: 0.21885156631469727  sec

.. .. code-block:: console
    
..     time to retrieve every element name in lhcb1 sequence 0.024236202239990234 sec
..     time to retrieve every element name in lhcb2 sequence 0.0245511531829834 sec