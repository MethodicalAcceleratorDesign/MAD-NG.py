# pymadng
Python interface to MAD-NG running as subprocess

Install using below, see [The Python Package Index (PyPi)](https://pypi.org/project/pymadng/);

`pip install pymadng`

Familiarising yourself with pymadng
===================================

First, we recommend familiarising yourself with MAD-NG, documentation can be found [here](https://mad.web.cern.ch/mad/releases/madng/html/). 

Then reading through the Low-Level Example Explained on the [pymadng documentation](https://pymadng.readthedocs.io/en/latest/) should be sufficient (alongside knowledge of MAD-NG), assuming you are not planning to use any "syntactic sugar". If you plan to use the available pythonic looking code, there are plenty of examples to look at. 

In the documentation, [FODO Examples Explained](https://pymadng.readthedocs.io/en/latest/ex-fodo.html), is a chapter that goes into detail on what is happening on each line of the [FODO example](https://github.com/MethodicalAcceleratorDesign/MADpy/blob/main/examples/ex-fodo/ex-fodos.py), while [LHC Example](https://pymadng.readthedocs.io/en/latest/ex-lhc-couplingLocal.html) gives an example of loading the LHC and how to grab intermediate results from a match. 

The only other example that may be of use is the [ps-twiss](https://github.com/MethodicalAcceleratorDesign/MADpy/blob/main/examples/ex-ps-twiss/ps-twiss.py) example. This is an extremely simple example, extending the FODO example to perform a twiss on the PS sequence.
If anything does not seem fully explained, initially check the [API Reference](https://pymadng.readthedocs.io/en/latest/pymadng.html#module-pymadng) and/or the [MAD-NG Documentation](https://mad.web.cern.ch/mad/releases/madng/html/), then feel free to open an [issue](https://github.com/MethodicalAcceleratorDesign/MADpy/issues) so improvements can be made.

Documentation
=============

Documentation, including explanation of a couple of examples and the limitations of the API can be found [here](https://pymadng.readthedocs.io/en/latest/). 

The API reference is also included in [this documentation](https://pymadng.readthedocs.io/en/latest/). You can also compile to documentation yourself by cloning the repository and running ``make html`` in the docs folder.

Getting the examples working
============================

You can run the example with `python3 EXAMPLE_NAME.py`
