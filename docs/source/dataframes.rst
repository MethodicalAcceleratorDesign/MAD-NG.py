Converting TFS tables to Pandas DataFrames
------------------------------------------

The package `pandas` is an optional module, that has an inbuilt function to convert TFS tables (called ``mtable`` in MAD-NG) to a `pandas` ``DataFrame`` or a ``TfsDataFrame`` if you have `tfs-pandas` installed. In the example below, we generate an ``mtable`` by doing a survey and twiss on the Proton Synchrotron lattice, and then convert these to a ``DataFrame`` (or ``TfsDataFrame``).

.. literalinclude:: ../../examples/ex-ps-twiss/ps-twiss.py
    :lines: 18, 24, 41-49
    :linenos:

In this script, we create the variables ``srv`` and ``mtbl`` which are ``mtable``\ s created by ``survey`` and ``twiss`` respectively. Then first, we convert the ``mtbl`` to a ``DataFrame`` and print it, before checking if you have `tfs-pandas` installed to check if we need to print out the header of the TFS table, which is stored in the attrs attribute of the ``DataFrame``, but is automatically printed when using `tfs-pandas`. Then we convert the ``srv`` to a ``DataFrame`` and print it.

Note: If your object is not an ``mtable`` then this function will raise a ``TypeError``, but it is available to call on all ``object`` types in MAD-NG.