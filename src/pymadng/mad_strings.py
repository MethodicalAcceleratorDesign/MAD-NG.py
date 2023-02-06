from typing import Any
from .mad_classes import mad_ref

# Should this be a class or a set of functions, py_name is the only issue here?
# For now, it's a class and this gives the option to add more functionality later

class mad_strings:
    def __init__(self, py_name: str):
        self.py_name = py_name

    def get_kwargs_string(self, **kwargs):
        # Keep an eye out for failures when kwargs is empty, shouldn't occur in current setup
        """Convert a keyword argument input to a string used by MAD-NG"""
        kwargsString = "{"
        vars_to_send = []
        for key, item in kwargs.items():
            keyString = str(key).replace("'", "")
            itemString, var = self.to_MAD_string(item)
            kwargsString += keyString + " = " + itemString + ", "
            vars_to_send.extend(var)
        return kwargsString + "}", vars_to_send

    def get_args_string(self, *args):
        """Convert an argument input to a string used by MAD-NG"""
        mad_string = ""
        vars_to_send = []
        for arg in args:
            string, var = self.to_MAD_string(arg)
            mad_string += string + ", "
            vars_to_send.extend(var)
        return mad_string[:-2], vars_to_send

    def to_MAD_string(self, var: Any):
        """Convert a list of objects into the required string for MAD-NG. 
        Converting string instead of sending more data is up to 2x faster (therefore last resort)."""
        if isinstance(var, list):
            string, vars_to_send = self.get_args_string(*var)
            return "{" + string + "}", vars_to_send
        elif var is None:
            return "nil", []
        elif isinstance(var, str):
            return var, []
        elif isinstance(var, complex):
            string = str(var)
            return (string[0] == "(" and string[1:-1] or string).replace("j", "i"), []
        elif isinstance(var, mad_ref):
            return var.__name__, []
        elif isinstance(var, dict):
            return self.get_kwargs_string(**var)
        elif isinstance(var, bool):
            return str(var).lower(), []
        elif isinstance(var, (float, int)):
            return str(var), []
        else:
            return f"{self.py_name}:recv()", [var]