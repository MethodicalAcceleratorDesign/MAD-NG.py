LHC Example
===========

The file :ref:`ex-lhc-couplingLocal/lhc-couplingLocal.py <ex-lhc>` contains an example of loading the required files to use and run the LHC, while including a method to receive and plot intermediate results of a match.

Loading the LHC 
---------------

The following lines loads the required variables and files for the example. ``assertf`` is not required, but it is used to check if the loading of the LHC is successful. The two string inputs to ``mad.MADX.load`` is also not required, but it is used to specify the final destination of the translated files from MAD-X to MAD-NG. Also, line 5 is not required as this is just to prevent MAD-NG from reporting warnings of unset variables from loading the LHC. Once again, in this extract, the important point to note is that to input strings into functions in MAD-NG, they must be enclosed in quotes. This is because any string input from the side of python is evaluated by MAD-NG, therefore the input can be a variable or expressions.

To grab variables from the MAD-X environment, we use ``mad.load("MADX", ...)``.

.. literalinclude:: ../../examples/ex-lhc-couplingLocal/lhc-couplingLocal.py
    :lines: 12-22
    :linenos:

Receving intermediate results
-----------------------------

The most complicated part of the example includes the following set of lines. 

From lines 4 - 8 below, we define a function that will be invoked during the optimization process at each iteration. Within this function, we perform a twiss for the match function to use, while also sending some information on the twiss to python, on line 6. 

From lines 10 - 21, we run a match, with a **reference** to the match result returned to the variable ``match_rtrn``. Line 22 is a very important line, as this is something you place in the pipe to MAD-NG for MAD-NG to execute once the match is done. Lines 23-25 receive the first result returned during the match, so that we can start plotting the results.

The plotting occurs between lines 27 - 36, wtih the while loop continuing until twiss result is ``None``, which occurs when the match is done, as requested on line 22.

Finally, on lines 38 and 39, we retrieve the results of the match from the variable ``match_rtrn``. Since ``match_rtrn`` is a *temporary variable*, there is a limit to how many of these that can be stored (see :doc:`ex-managing-refs` for more information on these), we delete the reference in python to clear the temporary variable so that is is available for future use.

.. important::
    As MAD-NG is running in the background, the variable ``match_rtrn`` contains *no* information and instead must be queried for the results. During the query, python will then have to wait for MAD-NG to finish the match, and then return the results. On the other hand, if we do not query for the results, the match will continue to run in the background, we can do other things in python, and then query for the results later.

.. literalinclude:: ../../examples/ex-lhc-couplingLocal/lhc-couplingLocal.py
    :lines: 39-77
    :linenos: