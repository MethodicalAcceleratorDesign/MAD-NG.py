from typing import Any
from .madp_pymad import mad_ref

def get_kwargs_string(py_name, **kwargs):
	# Keep an eye out for failures when kwargs is empty, shouldn't occur in current setup
	"""Convert a keyword argument input to a string used by MAD-NG"""
	kwargsString = "{"
	vars_to_send = []
	for key, item in kwargs.items():
		keyString = str(key).replace("'", "")
		itemString, var = to_MAD_string(py_name, item)
		kwargsString += keyString + " = " + itemString + ", "
		vars_to_send.extend(var)
	return kwargsString + "}", vars_to_send


def get_args_string(py_name, *args):
	"""Convert an argument input to a string used by MAD-NG"""
	mad_string = ""
	vars_to_send = []
	for arg in args:
		string, var = to_MAD_string(py_name, arg)
		mad_string += string + ", "
		vars_to_send.extend(var)
	return mad_string[:-2], vars_to_send


def to_MAD_string(py_name, var: Any):
	"""Convert a list of objects into the required string for MAD-NG.
	Converting string instead of sending more data is up to 2x faster (therefore last resort).
	"""
	if isinstance(var, list):
		string, vars_to_send = get_args_string(py_name, *var)
		return "{" + string + "}", vars_to_send
	elif var is None:
		return "nil", []
	elif isinstance(var, str):
		return var, []
	elif isinstance(var, mad_ref):
		return var._name, []
	elif isinstance(var, dict):
		return get_kwargs_string(py_name, **var)
	elif isinstance(var, bool):
		return str(var).lower(), []
	else:
		return f"{py_name}:recv()", [var]
