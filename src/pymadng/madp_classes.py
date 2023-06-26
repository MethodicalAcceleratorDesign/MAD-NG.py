from typing import Iterable, Union, Any  # To make stuff look nicer
import numpy as np
from .madp_pymad import mad_process, mad_ref, data_types
from .madp_strings import get_args_string, get_kwargs_string
from .madp_last import last_counter

# TODO: Are you able to store the actual parent? 
# TODO: Verify if functions need kwargs or not. (I would  not)

MADX_methods = ["load", "open_env", "close_env"]
class madhl_ref(mad_ref):    
  def __init__(self, name: str, mad_proc: mad_process, last_counter: last_counter):
    super(madhl_ref, self).__init__(name, mad_proc)
    self.__parent__ = (
      "[" in name and "[".join(name.split("[")[:-1]) or None
    )  # if name is compound, get parent by string manipulation
    self.__mad__ = mad_proc
    self.__lst_cntr__ = last_counter

  def __setattr__(self, item, value):
    if item[0] == "_":
      return super(madhl_ref, self).__setattr__(item, value)
    self[item] = value

  def __setitem__(
    self,
    item: Union[str, int],
    value: Union[str, int, float, np.ndarray, bool, list],
  ):
    if isinstance(item, int):
      self.__mad__.send_vars(f"{self.__name__}[{item+1}]", value)
    elif isinstance(item, str):
      self.__mad__.send_vars(f"{self.__name__}['{item}']", value)
    else:
      raise TypeError("Cannot index type of ", type(item), "expected string or int")

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
    if (isinstance(rhs, type(self)) and self.__name__ == rhs.__name__):
      return True
    else:
      return self.__gOp__(rhs, "==").eval()

  def __gOp__(self, rhs, operator: str):
    rtrn = madhl_reflast(self.__mad__, self.__lst_cntr__)
    self.__mad__.psend(f"{rtrn.__name__} = {self.__name__} {operator} {self.__mad__.py_name}:recv()").send(rhs)
    return rtrn

  def __len__(self):
    return self.__mad__.precv(f"#{self.__name__}")

  def __str__(self):
    val = self.__mad__.recv_vars(self.__name__)
    if isinstance(val, madhl_ref):
      return repr(val)
    else:
      return str(val)

  def eval(self):
    return self.__mad__.recv_vars(self.__name__)

  def __repr__(self):
    return f"MAD-NG Object(Name: {self.__name__}, Parent: {self.__parent__})"

  def __dir__(self) -> Iterable[str]:
    name = self.__name__
    if name[:8] == "__last__":
      name = name + ".__metatable or " + name
    script = f"""
      local modList={{}}; local i = 1;
      for modname, mod in pairs({name}) do modList[i] = modname; i = i + 1; end
      {self.__mad__.py_name}:send(modList)"""
    self.__mad__.psend(script)
    varnames = [x for x in self.__mad__.recv() if isinstance(x, str) and x[0] != "_"]
    return varnames

class madhl_obj(madhl_ref):
  def __dir__(self) -> Iterable[str]:
    if not self.__mad__.ipython_use_jedi:
      self.__mad__.psend(f"{self.__mad__.py_name}:send({self.__name__}:get_varkeys(MAD.object))")
    varnames = self.__mad__.precv(f"{self.__name__}:get_varkeys(MAD.object, false)")

    if not self.__mad__.ipython_use_jedi:
      varnames.extend([x + "()" for x in self.__mad__.recv() if not x in varnames])
    return varnames

  def __call__(self, *args, **kwargs):
    last_obj = madhl_objlast(self.__mad__, self.__lst_cntr__)
    kwargs_string, kwargs_to_send = get_kwargs_string(self.__mad__.py_name, **kwargs)
    args_string  ,   args_to_send = get_args_string(self.__mad__.py_name, *args)
    
    self.__mad__.send(
      f"{last_obj.__name__} = __mklast__( {self.__name__} {{ {kwargs_string[1:-1]} {args_string} }} )"
    )
    for var in kwargs_to_send + args_to_send:
      self.__mad__.send(var)
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


class madhl_fun(madhl_ref):
  # ----------------------------------Calling/Creating functions--------------------------------------#
  def __call_func(self, funcName: str, *args):
    """Call the function funcName and store the result in ``__last__``."""
    rtrn_ref = madhl_reflast(self.__mad__, self.__lst_cntr__)
    args_string, vars_to_send = get_args_string(self.__mad__.py_name, *args)
    self.__mad__.send(
      f"{rtrn_ref.__name__} = __mklast__({funcName}({args_string}))\n"
    )
    for var in vars_to_send:
      self.__mad__.send(var)
    return rtrn_ref
  # ---------------------------------------------------------------------------------------------------#
  
  def __call__(self, *args: Any) -> Any:
    # Checks for MADX methods
    call_from_madx = self.__parent__ and self.__parent__.split("['")[-1].strip("']") == "MADX"
    if call_from_madx: funcname = self.__name__.split("['")[-1].strip("']")

    ismethod = self.__parent__ and (self.__mad__.precv(f"""
    MAD.typeid.is_object({self.__parent__}) or MAD.typeid.isy_matrix({self.__parent__})
    """))
    if ismethod and not (call_from_madx and not funcname in MADX_methods):
      return self.__call_func(self.__name__, self.__parent__, *args)
    else:
      return self.__call_func(self.__name__, *args)
  def __dir__(self):
    return super(madhl_ref, self).__dir__()

# Separate class for __last__ objects for simplicity and fewer if statements
class madhl_last(): # The init and del for a __last__ object
  def __init__(self, mad_proc: mad_process, last_counter: last_counter):
    self.__lastnum__ = last_counter.get()
    self.__name__ = f"__last__[{self.__lastnum__}]"
    self.__mad__ = mad_proc
    self.__parent__ = "__last__"
    self.__lst_cntr__ = last_counter
  
  def __del__(self):
    self.__lst_cntr__.set(self.__lastnum__)

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

data_types[madhl_ref] = "ref_"
data_types[madhl_obj] = "obj_"
data_types[madhl_fun] = "fun_"

data_types[madhl_reflast] = "ref_"
data_types[madhl_objlast] = "obj_"