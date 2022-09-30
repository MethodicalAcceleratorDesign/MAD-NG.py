# pymadng
Python interface to MAD-NG running as subprocess and using Pexpect 

Getting the examples working
============================

To run the examples you will need a mad executable which can be found here; http://mad.web.cern.ch/mad/releases/madng/0.9/
You will also need the memory mapping mad file, which in the future will be packaged with the mad executable, this can be downloaded here: https://cernbox.cern.ch/index.php/s/eReVquPhXHZzUYX

Place these files in the folder with the python example that you would like to run and rename the mad exectuable to `mad`.

You can then run the example with `python3 EXAMPLE_NAME.py`
