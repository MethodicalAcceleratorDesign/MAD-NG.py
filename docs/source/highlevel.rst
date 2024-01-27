High-Level PyMAD-NG
===================

This page describes how the pythonic interface to MAD-NG works. This way of using PyMAD-NG is far more limited than the low-level interface, and everything that can be done with the high-level interface can also be done with the low-level interface, usually with more flexibility and better performance. However, the high-level interface is much easier to use for people used to python. 

The "high-level" describes essentially every function, method, class, variable, etc. accessible from the top-level namespace of the `pymadng` module not listed in the :class:`API Reference <pymadng.MAD>`. 

When a user initialises a :class:`MAD <pymadng.MAD>` object, as follows, we say that the user has created a "MAD object", which creates a new instance of the MAD-NG program, and from this object we can interact with the MAD-NG program.

.. code-block:: python

    import pymadng
    mad = pymadng.MAD()

The MAD object is used to access the global environment of the MAD instance, there does not exist a significant amount within the global environment, the full list of variables can be found on the `MAD-NG GitHub <https://github.com/MethodicalAcceleratorDesign/MAD-NG/blob/dev/src/madl_main.mad#L397>`_, but a few of the more important ones are listed below, for a better understanding and examples see the `MAD-NG manual <http://madx.web.cern.ch/madx/releases/madng/html/mad_gen_script.html>`_.

Global Libraries
----------------

- :class:`io` - A lua library for reading and writing files.
- :class:`os` - A lua library for interacting with the operating system.
- :class:`math` - A lua library for mathematical functions.
- :class:`table` - A lua library for manipulating tables.
- :class:`string` - A lua library for manipulating strings.
- :class:`MAD` - The main library for accessing all the modules and functions of MAD-NG.
- :class:`MADX` - The MAD-X environment in MAD-NG - explicitly not MAD-X and so cannot be used to run MAD-X code, used for importing MAD-X sequences and adjusting variables and knobs.

Global Functions
----------------

- :func:`assert` - A lua function for asserting a condition.
- :func:`print` - A lua function for printing to the console.
- :func:`error` - A lua function for throwing an error.
- :func:`ipairs` - A lua function for iterating over the indexed part of a table (the array part). 
- :func:`pairs` - A lua function for iterating over the whole table, including indices and keys (the array and hash parts).
- :func:`tonumber` - A lua function for converting a string to a number.
- :func:`tostring` - A lua function for converting a number to a string.
- :func:`type` - A lua function for getting the type of a variable.

Other Global Variables - Specific to PyMAD-NG
---------------------------------------------

The functions that are required for physics are all contained within the :class:`MAD` library, a few of the more important ones are immediately exposed to the user, only in PyMAD-NG, and are listed below:

- :class:`beam` - See `Beams <http://madx.web.cern.ch/madx/releases/madng/html/mad_gen_beam.html>`_
- :class:`beta0` - See `Beta0 <http://madx.web.cern.ch/madx/releases/madng/html/mad_gen_beta0.html>`_
- :class:`element` - See `Elements <http://madx.web.cern.ch/madx/releases/madng/html/mad_gen_elements.html>`_
- :class:`match` - See `Match <http://madx.web.cern.ch/madx/releases/madng/html/mad_cmd_match.html>`_
- :class:`mtable` - See `MTables <http://madx.web.cern.ch/madx/releases/madng/html/mad_gen_mtable.html>`_
- :class:`object` - See `Objects <http://madx.web.cern.ch/madx/releases/madng/html/mad_gen_object.html>`_
- :class:`sequence` - See `Sequences <http://madx.web.cern.ch/madx/releases/madng/html/mad_gen_sequence.html>`_
- :class:`survey` - See `Survey <http://madx.web.cern.ch/madx/releases/madng/html/mad_cmd_survey.html>`_
- :class:`track` - See `Track <http://madx.web.cern.ch/madx/releases/madng/html/mad_cmd_track.html>`_
- :class:`twiss` - See `Twiss <http://madx.web.cern.ch/madx/releases/madng/html/mad_cmd_twiss.html>`_

Accessing the Global Environment
--------------------------------

To access anything in the global environment, we can use the :class:`MAD <pymadng.MAD>` object, for example, to access the :class:`math` library, we can use the following:

.. code-block:: python

    import pymadng
    mad = pymadng.MAD()
    print(mad.math.sin(1).eval(), mad.math.cos(1).eval()) # 0.8414709848078965 0.5403023058681398

The reason we have to use the :func:`eval` function is because when a function is called from python and executed in MAD-NG, it will always return a reference, allowing us to continue to use the returned value in MAD-NG and it is not automatically converted to a python object. See :doc:`/ex-managing-refs` for more information on these references and how to use/deal with them. This evaulation can also be done using the low level interface, as follows:

.. code-block:: python

    import pymadng
    mad = pymadng.MAD()
    mad.send("py:send(math.sin(1)):send(math.cos(1))")
    print(mad.recv(), mad.recv()) # 0.8414709848078965 0.5403023058681398

To conclude, the global environment is accessed through the :class:`MAD <pymadng.MAD>` object, several of libraries and functions are listed above, most of the other necessary functions required can be accessed through the :class:`MAD` library in MAD-NG, by doing ``mad.MAD``. With knowledge of MAD-NG, the user can access and interact with almost everything in MAD-NG through the high-level interface, however, the low-level interface is much more flexible and powerful, so it is recommended to use for more complex tasks. 