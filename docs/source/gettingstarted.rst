Getting Started
===============

Installation
------------

.. code-block:: 

    pip install pymadng

Each example can run by executing ``python3 ex-name.py``, using a console with the same working directory as the example. These examples give a range of available uses and show some techniques that are available with MAD-NG and pymadng. You can also run all the examples with ``runall.py``

To begin communication with MAD-NG, you simply are required to do:

.. code-block::

    from pymadng import MAD
    mad = MAD()

Communication protocol
----------------------

.. important:: **Before you send data to MAD-NG, you must always send MAD-NG the instructions to read the data. Before you receive any data from MAD-NG, you must always ask MAD-NG to send the data.**

.. code-block:: 
    :caption: An example of using the MAD object to communicate with MAD-NG
    
    #Load MAD from pymadng
    from pymadng import MAD
    mad = MAD()

    #Tell mad that it should expect data and then place it in 'a'
    mad.send("a = py:recv()")
    
    #Send the data
    mad.send(42)

    #Ask mad to send the data back
    mad.send("py:send(a)")

    #Read the data
    mad.recv() #-> 42


:meth:`mad.send() <pymadng.MAD.send>` and :meth:`mad.recv() <pymadng.MAD.recv>` are the main ways to communicate with MAD-NG and is extremely simple, for specific details on what data can be sent see the :class:`API Reference <pymadng.MAD>`.

For types that are not naturally found in numpy or python, you will be required to use a different function to *send* data (see below). The functions used in these specific cases can be found in the :mod:`MAD <pymadng.MAD>` documentation. To *receive* any data just use :meth:`mad.recv() <pymadng.MAD.recv>`.

+----------------------------------------+------------------------+----------------------------------------------+
| Type in Python                         | Type in MAD            | Function to send from Python                 |
+========================================+========================+==============================================+
| None                                   | nil                    | :meth:`send <pymadng.MAD.send>`              |
+----------------------------------------+------------------------+----------------------------------------------+
| str                                    | string                 | :meth:`send <pymadng.MAD.send>`              |
+----------------------------------------+------------------------+----------------------------------------------+
| int                                    | number :math:`<2^{31}` | :meth:`send <pymadng.MAD.send>`              |
+----------------------------------------+------------------------+----------------------------------------------+
| float                                  | number                 | :meth:`send <pymadng.MAD.send>`              |
+----------------------------------------+------------------------+----------------------------------------------+
| complex                                | complex                | :meth:`send <pymadng.MAD.send>`              |
+----------------------------------------+------------------------+----------------------------------------------+
| list                                   | table                  | :meth:`send <pymadng.MAD.send>`              |
+----------------------------------------+------------------------+----------------------------------------------+
| bool                                   | bool                   | :meth:`send <pymadng.MAD.send>`              |
+----------------------------------------+------------------------+----------------------------------------------+
| NumPy ndarray (dtype = np.float64)     | matrix                 | :meth:`send <pymadng.MAD.send>`              |
+----------------------------------------+------------------------+----------------------------------------------+
| NumPy ndarray (dtype = np.complex128)  | cmatrix                | :meth:`send <pymadng.MAD.send>`              |
+----------------------------------------+------------------------+----------------------------------------------+
| NumPy ndarray (dtype = np.int32)       | imatrix                | :meth:`send <pymadng.MAD.send>`              |
+----------------------------------------+------------------------+----------------------------------------------+
| range                                  | irange                 | :meth:`send <pymadng.MAD.send>`              |
+----------------------------------------+------------------------+----------------------------------------------+
| start(float), stop(float), size(int)   | range                  | :meth:`send_rng <pymadng.MAD.send_rng>`      |
+----------------------------------------+------------------------+----------------------------------------------+
| start(float), stop(float), size(int)   | logrange               | :meth:`send_lrng <pymadng.MAD.send_lrng>`    |
+----------------------------------------+------------------------+----------------------------------------------+
|| NumPy ndarray (dtype = np.uint8) and  || TPSA                  || :meth:`send_tpsa <pymadng.MAD.send_tpsa>`   |
|| NumPy ndarray (dtype = np.float64)    ||                       ||                                             |
+----------------------------------------+------------------------+----------------------------------------------+
|| NumPy ndarray (dtype = np.uint8) and  || CTPSA                 || :meth:`send_ctpsa <pymadng.MAD.send_ctpsa>` |
|| NumPy ndarray (dtype = np.complex128) ||                       ||                                             |
+----------------------------------------+------------------------+----------------------------------------------+

Customising your environment
----------------------------

Few things can be changed about the setup of your communication with MAD-NG, below lists a couple of use cases that may be of use. See also :meth:`__init__<pymadng.MAD.__init__>`.

To change how you refer to your python prcess from within MAD-NG, by default, we use ``py`` (which may conflict with some variables you intend to define):

.. code-block::
    
    from pymadng import MAD
    mad = MAD(py_name = "python")

To change the MAD-NG executable used when pymadng is run:

.. code-block::

    from pymadng import MAD
    mad = MAD(mad_path = r"/path/to/mad")

To enable debugging mode:

.. code-block::

    from pymadng import MAD
    mad = MAD(debug = True)