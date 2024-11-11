from __future__ import annotations

import warnings  # To warn the user when they try to deepcopy a mad_ref
from typing import TYPE_CHECKING, Any  # To make stuff look nicer

import numpy as np

from .madp_pymad import is_private, mad_process, mad_ref, type_str
from .madp_strings import format_args_to_string, format_kwargs_to_string

if TYPE_CHECKING:
    from collections.abc import Iterable

# TODO: Are you able to store the actual parent? (jgray 2023)
# TODO: Allow __setitem__ to work with multiple indices (Should be a simple recursive loop) (jgray 2023)

MADX_methods = ["load", "open_env", "close_env"]


# MAD High Level reference
class high_level_mad_ref(mad_ref):
    def __init__(self, name: str, mad_proc: mad_process):
        super(high_level_mad_ref, self).__init__(name, mad_proc)
        self._parent = (
            "[" in name and "[".join(name.split("[")[:-1]) or None
        )  # if name is compound, get parent by string manipulation
        self._last_counter = (
            mad_proc.last_counter
        )  # Set the last counter to the current value in the process

    def __setattr__(self, item, value):
        if is_private(item):
            # If the attribute is private, set it as a normal attribute
            return super(high_level_mad_ref, self).__setattr__(item, value)
        # Otherwise, set the item as a variable in the MAD-NG process
        self[item] = value

    def __setitem__(
        self,
        item: str | int,
        value: str | int | float | np.ndarray | bool | list | mad_ref,
    ):
        if isinstance(item, int):
            item = item + 1  # Ints need to be incremented by 1 to match MAD-NG indexing
        elif isinstance(item, str):
            item = f"'{item}'"  # Strings need to be wrapped in quotes
        else:  # Any other index type is invalid
            raise TypeError(
                "Cannot index type of ", type(item), "expected string or int"
            )
        self._mad.send_vars(**{f"{self._name}[{item}]": value})

    def __add__(self, rhs):
        return self.__generate_operation__(rhs, "+")

    def __mul__(self, rhs):
        return self.__generate_operation__(rhs, "*")

    def __pow__(self, rhs):
        return self.__generate_operation__(rhs, "^")

    def __sub__(self, rhs):
        return self.__generate_operation__(rhs, "-")

    def __truediv__(self, rhs):
        return self.__generate_operation__(rhs, "/")

    def __mod__(self, rhs):
        return self.__generate_operation__(rhs, "%")

    def __eq__(self, rhs):
        if isinstance(rhs, type(self)) and self._name == rhs._name:
            return True
        else:
            return self.__generate_operation__(rhs, "==").eval()

    def __generate_operation__(self, rhs, operator: str):
        rtrn = mad_high_level_last_ref(self._mad)
        self._mad.protected_send(
            f"{rtrn._name} = {self._name} {operator} {self._mad.py_name}:recv()"
        ).send(rhs)
        return rtrn

    def __len__(self):
        return self._mad.protected_variable_retrieval(f"#{self._name}")

    def __str__(self):
        val = self._mad.recv_vars(self._name)
        if isinstance(val, high_level_mad_ref):
            return repr(val)
        else:
            return str(val)

    def eval(self):
        return self._mad.recv_vars(self._name)

    def __repr__(self):  # TODO: This should be better (jgray 2024)
        return f"MAD-NG Object(Name: {self._name}, Parent: {self._parent}, Process: {repr(self._mad)})"

    def __dir__(self) -> Iterable[str]:
        name = self._name
        if name[:5] == "_last":
            name = name + ".__metatable or " + name
        self._mad.protected_send(f"""
    local modList={{}}; local i = 1;
    for modname, mod in pairs({name}) do modList[i] = modname; i = i + 1; end
    {self._mad.py_name}:send(modList)
    """)
        return [x for x in self._mad.recv() if isinstance(x, str) and x[0] != "_"]

    def __deepcopy__(self, memo):
        val = self.eval()
        if isinstance(val, list):
            for i, v in enumerate(val):
                if isinstance(v, mad_ref):
                    val[i] = v.__deepcopy__(memo)
        elif isinstance(val, type(self)) and val._name == self._name:
            warnings.warn(
                "An attempt to deepcopy a mad_ref has been made, this is not supported and will result in a copy of the reference."
            )
        return val


class high_level_mad_object(high_level_mad_ref):
    def __dir__(self) -> Iterable[str]:
        if not self._mad.ipython_use_jedi:
            self._mad.protected_send(
                f"{self._mad.py_name}:send({self._name}:get_varkeys(MAD.object))"
            )
        varnames = self._mad.protected_variable_retrieval(
            f"{self._name}:get_varkeys(MAD.object, false)"
        )

        if not self._mad.ipython_use_jedi:
            varnames.extend([x + "()" for x in self._mad.recv() if x not in varnames])
        return varnames

    def __call__(self, *args, **kwargs):
        last_obj = high_level_last_object(self._mad)
        kwargs_str, kwargs_to_send = format_kwargs_to_string(
            self._mad.py_name, **kwargs
        )
        args_str, args_to_send = format_args_to_string(self._mad.py_name, *args)

        self._mad.protected_send(
            f"{last_obj._name} = __mklast__( {self._name} {{ {kwargs_str[1:-1]} {args_str} }} )"
        )
        for var in kwargs_to_send + args_to_send:
            self._mad.send(var)
        return last_obj

    def __iter__(self):
        self._iterindex = -1
        return self

    def __next__(self):
        try:
            self._iterindex += 1
            return self[self._iterindex]
        except IndexError:
            raise StopIteration

    def to_df(self, columns: list = None):  # For backwards compatibility (jgray 2024)
        """See `convert_to_dataframe`"""
        return self.convert_to_dataframe(columns)

    def convert_to_dataframe(self, columns: list = None):
        """Converts the object to a pandas dataframe.

        This function imports pandas and tfs-pandas, if tfs-pandas is not installed, it will only return a pandas dataframe.

        Args:
            columns (list, optional): List of columns to include in the dataframe. Defaults to None.

        Returns:
            pandas.DataFrame or tfs.TfsDataFrame: The dataframe containing the object's data.
        """
        if not self._mad.protected_variable_retrieval(
            f"MAD.typeid.is_mtable({self._name})"
        ):
            raise TypeError("Object is not a table, cannot convert to dataframe")

        import pandas as pd

        try:
            import tfs

            # If tfs is available, use the headers attribute
            DataFrame, hdr_attr = tfs.TfsDataFrame, "headers"
        except ImportError:
            # Otherwise, use the pandas dataframe and attrs attribute
            DataFrame, hdr_attr = pd.DataFrame, "attrs"

        py_name, obj_name = self._mad.py_name, self._name
        self._mad.protected_send(  # Sending every value individually is slow (sending vectors is fast)
            f"""
local is_vector, is_number, is_string in MAD.typeid
local colnames = {py_name}:recv() or {obj_name}:colnames() -- Get the column names 
{py_name}:send(colnames)               -- Send the column names

-- Loop through all the column names and send them with their data
for i, colname in ipairs(colnames) do
  local col = {obj_name}:getcol(colname)

  -- If the column is not a vector and has a metatable, then convert it to a table (reference or generator columns)
  if not is_vector(col) or getmetatable(col) then
    local tbl = table.new(#col, 0)
    local conv_to_vec = true
    local conv_to_str = true
    for i, val in ipairs(col) do 
    -- From testing, checking if I can convert to a vector is faster than sending the table
      conv_to_vec = conv_to_vec and is_number(val)
      conv_to_str = conv_to_str and is_string(val)
      tbl[i] = val
    end
    if conv_to_str then
      tbl = table.concat(tbl, "\\n")
    elseif conv_to_vec then
      tbl = MAD.vector(tbl)
    end
    col = tbl
  end

  {py_name}:send(col) -- Send the column data
end

local header = {obj_name}.header -- Get the header names
{py_name}:send(header)           -- Send the header names

for i, attr in ipairs(header) do 
  {py_name}:send({obj_name}[attr]) -- Send the header data
end
"""
        )
        self._mad.send(columns)
        # Create the dataframe from the data sent
        colnames = self._mad.recv()
        full_tbl = {  # The string is in case references are within the table
            col: self._mad.recv(f"{obj_name}:getcol('{col}')") for col in colnames
        }

        # Get the header names and data
        hdr_names = self._mad.recv()
        hdr = {
            hdr_name: self._mad.recv(f"{obj_name}['{hdr_name}']")
            for hdr_name in hdr_names
        }

        # Not keen on the .squeeze() but it works (ng always sends 2D arrays, but I need the columns in 1D)
        for key, val in full_tbl.items():
            if isinstance(val, np.ndarray):
                full_tbl[key] = val.squeeze()
            elif isinstance(val, str):
                full_tbl[key] = val.split("\n")

        # Now create the dataframe
        df = DataFrame(full_tbl)
        setattr(df, hdr_attr, hdr)

        return df


class high_level_mad_func(high_level_mad_ref):
    # ----------------------------------Calling/Creating functions--------------------------------------#
    def __call_func(self, funcName: str, *args):
        """Call the function funcName and store the result in ``_last``."""
        rtrn_ref = mad_high_level_last_ref(self._mad)
        args_string, vars_to_send = format_args_to_string(self._mad.py_name, *args)
        self._mad.protected_send(
            f"{rtrn_ref._name} = __mklast__({funcName}({args_string}))\n"
        )
        for var in vars_to_send:
            self._mad.send(var)
        return rtrn_ref

    # ---------------------------------------------------------------------------------------------------#

    def __call__(self, *args: Any) -> Any:
        # Checks for MADX methods
        call_from_madx = (
            self._parent and self._parent.split("['")[-1].strip("']") == "MADX"
        )
        if call_from_madx:  # Retrive the function name if the direct parent is MADX
            funcname = self._name.split("['")[-1].strip("']")

        ismethod = self._parent and (
            self._mad.protected_variable_retrieval(
                f"""
  MAD.typeid.is_object({self._parent}) or MAD.typeid.isy_matrix({self._parent})
  """
            )
        )  # Identify if _parent needs to be sent as the first argument (for methods)

        # If it is a method, and if it is a MADX method when called from MADX
        if ismethod and not (call_from_madx and funcname not in MADX_methods):
            return self.__call_func(self._name, self._parent, *args)
        else:
            return self.__call_func(self._name, *args)

    def __dir__(self):
        return super(high_level_mad_ref, self).__dir__()


# Separate class for _last objects for simplicity and fewer if statements
class mad_last:  # The init and del for a _last object
    def __init__(self, mad_proc: mad_process):
        self._mad = mad_proc
        self._last_counter = mad_proc.last_counter
        self._lastnum = mad_proc.last_counter.get()
        self._name = f"_last[{self._lastnum}]"
        self._parent = "_last"

    def __del__(self):
        self._last_counter.set(self._lastnum)


class mad_high_level_last_ref(mad_last, high_level_mad_ref):
    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        obj = self.eval()
        if isinstance(obj, (high_level_mad_object, high_level_mad_func)):
            return obj(*args, **kwargs)
        else:
            raise TypeError("Cannot call " + str(obj))

    def __dir__(self):
        return super(mad_high_level_last_ref, self).__dir__()


class high_level_last_object(mad_last, high_level_mad_object):
    pass


type_str[high_level_mad_ref] = "ref_"
type_str[high_level_mad_object] = "obj_"
type_str[high_level_mad_func] = "fun_"

type_str[mad_high_level_last_ref] = "ref_"
type_str[high_level_last_object] = "obj_"
