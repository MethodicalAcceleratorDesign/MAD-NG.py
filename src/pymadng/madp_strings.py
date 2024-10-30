from typing import Any
from .madp_pymad import mad_ref

def format_kwargs_to_string(py_name, **kwargs):
	# Keep an eye out for failures when kwargs is empty, shouldn't occur in current setup
	"""Convert a keyword argument input to a string used by MAD-NG
	
	Args:
		py_name (str): The name of the Python variable in the MAD-NG environment
		**kwargs: The keyword arguments to be converted to a string
	
	Returns:
		str: The string representation of the keyword arguments (may include variables that need to be sent through the pipe)
		list: The variables to send to the MAD-NG environment
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

	Args:
		py_name (str): The name of the Python variable in the MAD-NG environment
		*args: The arguments to be converted to a string

	Returns:
		str: The string representation of the arguments (may include variables that need to be sent through the pipe)
		list: The variables to send to the MAD-NG environment	
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

	Args:
		py_name (str): The name of the Python variable in the MAD-NG environment
		var (Any): The variable to be converted to a string
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
