.. _introduction:

========================
Introduction to PyMAD-NG
========================

What is PyMAD-NG?
-----------------
PyMAD-NG is a **Python interface** for **MAD-NG** (Methodical Accelerator Design - Next Generation), a powerful software for simulating and analysing particle accelerators. PyMAD-NG enables seamless communication between Python and MAD-NG, allowing users to **script, automate, and interactively control** MAD-NG simulations from Python.

PyMAD-NG provides a **pythonic API** that simplifies interaction with MAD-NG while maintaining high performance. Whether you're performing **optics calculations, beam dynamics simulations, or machine tuning**, PyMAD-NG offers the flexibility to work efficiently with MAD-NG from within Python.

Why Use PyMAD-NG?
-----------------
PyMAD-NG is designed for **scientists, engineers, and researchers** working on accelerator physics and beam dynamics. It offers several advantages over traditional MAD-NG workflows:

- **Pythonic Interface** - Write MAD-NG scripts using intuitive Python commands.
- **Efficient Communication** - Uses **pipes** for fast data exchange between Python and MAD-NG.
- **Seamless Data Handling** - Convert MAD-NG tables into **Pandas DataFrames** for analysis.
- **High Performance** - Designed for handling **large datasets** and computationally intensive simulations.
- **Flexible APIs** - Use either a **high-level API** (more Pythonic) or a **low-level API** (more control).
- **Jupyter Notebook Support** - Work interactively with MAD-NG in a Python notebook.
- **MAD-X Compatibility** - Load MAD-X sequences and interact with them in MAD-NG.

How PyMAD-NG Works
------------------
PyMAD-NG operates by **launching a MAD-NG process** in the background and establishing a **two-way communication channel** between Python and MAD-NG.

- **Sending Commands** - You can send MAD-NG commands as **Python strings**.
- **Receiving Results** - Data from MAD-NG can be retrieved into Python for further analysis.
- **MAD Objects in Python** - PyMAD-NG exposes MAD-NG objects as Python objects for easy manipulation.

Example Workflow
----------------

1. **Initialise PyMAD-NG**::

    from pymadng import MAD
    mad = MAD()

2. **Load a Sequence & Perform Calculations**::

    mad.MADX.load("'lhc_as-built.seq'", "'lhc_as-built.mad'")
    mad["tbl", "flw"] = mad.twiss(sequence=mad.MADX.lhcb1)

3. **Retrieve Data from MAD-NG**::

    df = mad.tbl.to_df()  # Convert twiss table to a Pandas DataFrame
    print(df.head())

4. **Visualise Results in Python**::

    import matplotlib.pyplot as plt
    plt.plot(df["s"], df["beta11"])
    plt.xlabel("s (m)")
    plt.ylabel("$\beta_x$-function")
    plt.show()

Key Features of PyMAD-NG
-------------------------

+--------------------------------+----------------------------------------------------------+
| Feature                        | Description                                              |
+================================+==========================================================+
| **Pythonic Interface**         | Interact with MAD-NG using Python objects.               |
+--------------------------------+----------------------------------------------------------+
| **High-Level & Low-Level API** | Choose between a simple or customisable approach.        |
+--------------------------------+----------------------------------------------------------+
| **Efficient Data Handling**    | Convert MAD-NG tables (`mtable`) into Pandas DataFrames. |
+--------------------------------+----------------------------------------------------------+
| **Two-Way Communication**      | Send commands to MAD-NG and retrieve results.            |
+--------------------------------+----------------------------------------------------------+
| **MAD-X Compatibility**        | Import and work with MAD-X sequences.                    |
+--------------------------------+----------------------------------------------------------+
| **MAD-8 Compatibility**        | Import and work with MAD-8 sequences.                    |
+--------------------------------+----------------------------------------------------------+
| **Performance Optimised**      | Supports large datasets and numerical computations.      |
+--------------------------------+----------------------------------------------------------+
| **Jupyter Notebook Support**   | Use PyMAD-NG interactively within Jupyter.               |
+--------------------------------+----------------------------------------------------------+

Who Should Use PyMAD-NG?
-------------------------
If you work with MAD-NG and want to **leverage Python's ecosystem (NumPy, Pandas, Matplotlib, etc.),** PyMAD-NG is the perfect tool for you.

Next Steps
----------
Now that you have an overview of PyMAD-NG, you can dive into:

- :doc:`Installation </installation>` - Set up PyMAD-NG on your system.
- :doc:`Quick Start Guide</quickstartguide>` - Run your first PyMAD-NG script in minutes.
- :doc:`API Reference</reference>` - Explore the available functions and classes.
