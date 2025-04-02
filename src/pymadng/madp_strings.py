from typing import Any

from .madp_pymad import mad_ref


# Keep an eye out for failures when kwargs is empty, shouldn't occur in current setup (jgray 2023)
def format_kwargs_to_string(py_name, **kwargs):
    """Convert a keyword argument input to a string used by MAD-NG

    The function produces a Lua table-like string representation of the arguments and
    gathers any non-string items in a list for separate sending.

    Args:
        py_name (str): The name of the Python reference variable in MAD-NG.
        **kwargs: Arbitrary keyword arguments to be converted.

    Returns:
        tuple: A tuple with the formatted string and a list of variables to send.
    """
    formatted_kwargs = "{"
    vars_to_send = []
    for key, item in kwargs.items():
        formatted_key = str(key).replace("'", "")
        formatted_item, var_to_send = create_mad_string(py_name, item)
        formatted_kwargs += formatted_key + " = " + formatted_item + ", "
        vars_to_send.extend(var_to_send)

    # Add the closing bracket and return
    return formatted_kwargs + "}", vars_to_send


def format_args_to_string(py_name, *args):
    """Convert an argument input to a string used by MAD-NG

    Convert positional arguments into a MAD-NG formatted string.

    Each argument is processed to produce a string suitable for MAD-NG while collecting any
    additional variables that require separate sending.

    Args:
        py_name (str): The Python reference name used in MAD-NG.
        *args: Positional arguments to be formatted.

    Returns:
        tuple: A tuple containing the composed argument string and a list of variables to send.
    """
    mad_string = ""
    vars_to_send = []
    for arg in args:
        formatted_arg, var_to_send = create_mad_string(py_name, arg)
        mad_string += formatted_arg + ", "
        vars_to_send.extend(var_to_send)

    # Remove the last comma and space
    return mad_string[:-2], vars_to_send


def create_mad_string(py_name, var: Any):
    """Convert a list of objects into the required string for MAD-NG.
    Converting string instead of sending more data is up to 2x faster (therefore last resort). Slowdown is mainly due to sending lists of strings.

    Convert a Python variable to its MAD-NG string representation.

    Handles lists, dictionaries, strings, and MAD references. For non-string or non-primitive
    types, it falls back on using a receive call.

    Args:
        py_name (str): The Python reference name in MAD-NG.
        var (Any): The variable to be converted.

    Returns:
        tuple: A tuple containing the formatted string and a list of associated variables.
    """
    if isinstance(var, list):
        string, vars_to_send = format_args_to_string(py_name, *var)
        return "{" + string + "}", vars_to_send
    elif var is None:
        return "nil", []
    elif isinstance(var, str):
        return var, []
    elif isinstance(var, mad_ref):
        return var._name, []
    elif isinstance(var, dict):
        return format_kwargs_to_string(py_name, **var)
    elif isinstance(var, bool):
        return str(var).lower(), []
    else:
        return f"{py_name}:recv()", [var]
