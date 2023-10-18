from typing import Iterable, Union, Any  # To make stuff look nicer
import numpy as np
from .madp_pymad import mad_process, mad_ref, type_str, is_private
from .madp_strings import get_args_string, get_kwargs_string

# TODO: Are you able to store the actual parent?
# TODO: Allow __setitem__ to work with multiple indices (Should be a simple recursive loop)

MADX_methods = ["load", "open_env", "close_env"]


class madhl_ref(mad_ref):
  def __init__(self, name: str, mad_proc: mad_process):
    super(madhl_ref, self).__init__(name, mad_proc)
    self._parent = (
      "[" in name and "[".join(name.split("[")[:-1]) or None
    )  # if name is compound, get parent by string manipulation
    self._lst_cntr = mad_proc.lst_cntr

  def __setattr__(self, item, value):
    if is_private(item):
      return super(madhl_ref, self).__setattr__(item, value)
    self[item] = value

  def __setitem__(
    self,
    item: Union[str, int],
    value: Union[str, int, float, np.ndarray, bool, list],
  ):
    if isinstance(item, int):
      self._mad.send_vars(**{f"{self._name}[{item+1}]": value})
    elif isinstance(item, str):
      self._mad.send_vars(**{f"{self._name}['{item}']": value})
    else:
      raise TypeError(
        "Cannot index type of ", type(item), "expected string or int"
      )

  def __add__(self, rhs):
    return self.__gOp__(rhs, "+")

  def __mul__(self, rhs):
    return self.__gOp__(rhs, "*")

  def __pow__(self, rhs):
    return self.__gOp__(rhs, "^")

  def __sub__(self, rhs):
    return self.__gOp__(rhs, "-")

  def __truediv__(self, rhs):
    return self.__gOp__(rhs, "/")

  def __mod__(self, rhs):
    return self.__gOp__(rhs, "%")

  def __eq__(self, rhs):
    if isinstance(rhs, type(self)) and self._name == rhs._name:
      return True
    else:
      return self.__gOp__(rhs, "==").eval()

  def __gOp__(self, rhs, operator: str):
    rtrn = madhl_reflast(self._mad)
    self._mad.psend(
      f"{rtrn._name} = {self._name} {operator} {self._mad.py_name}:recv()"
    ).send(rhs)
    return rtrn

  def __len__(self):
    return self._mad.precv(f"#{self._name}")

  def __str__(self):
    val = self._mad.recv_vars(self._name)
    if isinstance(val, madhl_ref):
      return repr(val)
    else:
      return str(val)

  def eval(self):
    return self._mad.recv_vars(self._name)

  def __repr__(self):
    return f"MAD-NG Object(Name: {self._name}, Parent: {self._parent})"

  def __dir__(self) -> Iterable[str]:
    name = self._name
    if name[:5] == "_last":
      name = name + ".__metatable or " + name
    self._mad.psend(f"""
    local modList={{}}; local i = 1;
    for modname, mod in pairs({name}) do modList[i] = modname; i = i + 1; end
    {self._mad.py_name}:send(modList)
    """)
    return [x for x in self._mad.recv() if isinstance(x, str) and x[0] != "_"]


class madhl_obj(madhl_ref):
  def __dir__(self) -> Iterable[str]:
    if not self._mad.ipython_use_jedi:
      self._mad.psend(
        f"{self._mad.py_name}:send({self._name}:get_varkeys(MAD.object))"
      )
    varnames = self._mad.precv(f"{self._name}:get_varkeys(MAD.object, false)")

    if not self._mad.ipython_use_jedi:
      varnames.extend([x + "()" for x in self._mad.recv() if not x in varnames])
    return varnames

  def __call__(self, *args, **kwargs):
    last_obj = madhl_objlast(self._mad)
    kwargs_str, kwargs_to_send = get_kwargs_string(self._mad.py_name, **kwargs)
    args_str, args_to_send = get_args_string(self._mad.py_name, *args)

    self._mad.send(
      f"{last_obj._name} = __mklast__( {self._name} {{ {kwargs_str[1:-1]} {args_str} }} )"
    )
    for var in kwargs_to_send + args_to_send:
      self._mad.send(var)
    return last_obj

  def __iter__(self):
    self.__iterIndex__ = -1
    return self

  def __next__(self):
    try:
      self.__iterIndex__ += 1
      return self[self.__iterIndex__]
    except IndexError:
      raise StopIteration

  def to_df(self, columns: list = None):
    """Converts the object to a pandas dataframe.

    This function imports pandas and tfs-pandas, if tfs-pandas is not installed, it will only return a pandas dataframe.

    Args:
            columns (list, optional): List of columns to include in the dataframe. Defaults to None.

    Returns:
            pandas.DataFrame or tfs.TfsDataFrame: The dataframe containing the object's data.
    """
    if not self._mad.precv(f"MAD.typeid.is_mtable({self._name})"):
      raise TypeError("Object is not a table, cannot convert to dataframe")

    import pandas as pd

    try:
      import tfs

      DataFrame, header = tfs.TfsDataFrame, "headers"
    except ImportError:
      DataFrame, header = pd.DataFrame, "attrs"

    py_name, obj_name = self._mad.py_name, self._name
    self._mad.send( # Sending every value individually is slow (sending vectors is fast)
      f"""
local is_vector, is_number in MAD.typeid
local colnames = {obj_name}:colnames() -- Get the column names 
{py_name}:send(colnames)               -- Send the column names

-- Loop through all the column names and send them with their data
for i, colname in ipairs(colnames) do
  local col = {obj_name}:getcol(colname)

  -- If the column is not a vector and has a metatable, then convert it to a table (reference or generator columns)
  if not is_vector(col) and getmetatable(col) then
    local tbl, conv_to_vec = table.new(#col, 0), true
    for i, val in ipairs(col) do 
    -- From testing, checking if I can convert to a vector is faster than sending the table
      conv_to_vec, tbl[i] = conv_to_vec and is_number(val), val
    end
    col = conv_to_vec and MAD.vector(tbl) or tbl
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
    # Create the dataframe from the data sent
    colnames = self._mad.recv()
    full_tbl = { # The string is in case references are within the table
      col: self._mad.recv(f"{obj_name}:getcol('{col}')") for col in colnames
    }

    # Not keen on the .squeeze() but it works (ng always sends 2D arrays, but I need the columns in 1D)
    for key, val in full_tbl.items():
      if isinstance(val, np.ndarray):
        full_tbl[key] = val.squeeze()
    df = DataFrame(full_tbl)

    if columns:
      df = df[columns] # Only keep the columns specified

    # Get the header and add it to the dataframe
    hnams = self._mad.recv()
    setattr(df, header,
      {hnam: self._mad.recv(f"{obj_name}['{hnam}']") for hnam in hnams}
    )
    return df


class madhl_fun(madhl_ref):
  # ----------------------------------Calling/Creating functions--------------------------------------#
  def __call_func(self, funcName: str, *args):
    """Call the function funcName and store the result in ``_last``."""
    rtrn_ref = madhl_reflast(self._mad)
    args_string, vars_to_send = get_args_string(self._mad.py_name, *args)
    self._mad.send(f"{rtrn_ref._name} = __mklast__({funcName}({args_string}))\n")
    for var in vars_to_send:
      self._mad.send(var)
    return rtrn_ref

  # ---------------------------------------------------------------------------------------------------#

  def __call__(self, *args: Any) -> Any:
    # Checks for MADX methods
    call_from_madx = (
      self._parent and self._parent.split("['")[-1].strip("']") == "MADX"
    )
    if call_from_madx:
      funcname = self._name.split("['")[-1].strip("']")

    ismethod = self._parent and (
      self._mad.precv(
        f"""
  MAD.typeid.is_object({self._parent}) or MAD.typeid.isy_matrix({self._parent})
  """
      )
    )
    if ismethod and not (call_from_madx and not funcname in MADX_methods):
      return self.__call_func(self._name, self._parent, *args)
    else:
      return self.__call_func(self._name, *args)

  def __dir__(self):
    return super(madhl_ref, self).__dir__()


# Separate class for _last objects for simplicity and fewer if statements
class madhl_last:  # The init and del for a _last object
  def __init__(self, mad_proc: mad_process):
    self._mad = mad_proc
    self._lst_cntr = mad_proc.lst_cntr
    self._lastnum = mad_proc.lst_cntr.get()
    self._name = f"_last[{self._lastnum}]"
    self._parent = "_last"

  def __del__(self):
    self._lst_cntr.set(self._lastnum)


class madhl_reflast(madhl_last, madhl_ref):
  def __call__(self, *args: Any, **kwargs: Any) -> Any:
    obj = self.eval()
    if isinstance(obj, (madhl_obj, madhl_fun)):
      return obj(*args, **kwargs)
    else:
      raise TypeError("Cannot call " + str(obj))

  def __dir__(self):
    return super(madhl_reflast, self).__dir__()


class madhl_objlast(madhl_last, madhl_obj):
  pass


type_str[madhl_ref] = "ref_"
type_str[madhl_obj] = "obj_"
type_str[madhl_fun] = "fun_"

type_str[madhl_reflast] = "ref_"
type_str[madhl_objlast] = "obj_"
