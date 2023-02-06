from typing import Iterable, Union, Any  # To make stuff look nicer
import numpy as np

# TODO: Are you able to store the actual parent? 
# TODO: Verify if functions need kwargs or not. 
# BUG: In the case of MADX, the ?only? object that includes methods and functions, we attempt to call the functions like methods. Try MAD.MADX.abs(1).
class mad_ref(object):    
    def __init__(self, name: str, mad_proc):
        assert name is not None, "Reference must have a variable to reference to. Did you forget to put a name in the receive functions?"
        self.__name__ = name
        self.__parent__ = (
            "[" in name and "[".join(name.split("[")[:-1]) or None
        )  # if name is compound, get parent by string manipulation
        self.__mad__ = mad_proc

    def __getattr__(self, item):
        if item[0] != "_":
            try:
                return self[item]
            except (IndexError, KeyError):
                pass
        raise AttributeError (item)  # For python

    def __setattr__(self, item, value):
        if item[0] == "_":
            return super(mad_ref, self).__setattr__(item, value)
        self[item] = value

    def __getitem__(self, item: Union[str, int]):
        if isinstance(item, int):
            result = self.__mad__.safe_recv(f"{self.__name__}[{item+1}]")
            if result is None:
                raise IndexError(item)  # For python
        elif isinstance(item, str):
            result = self.__mad__.safe_recv(f"{self.__name__}['{item}']")
            if result is None:
                raise KeyError(item)  # For python
        else:
            raise TypeError("Cannot index type of ", type(item))

        return result

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
        rtrn = mad_reflast(self.__mad__)
        self.__mad__.safe_send(f"{rtrn.__name__} = {self.__name__} {operator} {self.__mad__.py_name}:recv()").send(rhs)
        return rtrn

    def __len__(self):
        return self.__mad__.safe_recv(f"#{self.__name__}")

    def __str__(self):
        val = self.__mad__.recv_vars(self.__name__)
        if isinstance(val, mad_ref):
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
        self.__mad__.safe_send(script)
        varnames = [x for x in self.__mad__.recv() if isinstance(x, str) and x[0] != "_"]
        return varnames

class mad_obj(mad_ref):
    def __dir__(self) -> Iterable[str]:
        if not self.__mad__.ipython_use_jedi:
            self.__mad__.safe_send(f"{self.__mad__.py_name}:send({self.__name__}:get_varkeys(MAD.object))")

        # self.__mad__.safe_send(f"{self.__mad__.py_name}:send({self.__name__}:get_varkeys(MAD.object, false))")
        # varnames = [x for x in self.__mad__.recv()]
        varnames = self.__mad__.safe_recv(f"{self.__name__}:get_varkeys(MAD.object, false)")

        if not self.__mad__.ipython_use_jedi:
            varnames.extend([x + "()" for x in self.__mad__.recv() if not x in varnames])
        return varnames

    def __call__(self, *args, **kwargs):
        last_obj = mad_objlast(self.__mad__)
        kwargs_string, kwargs_to_send = self.__mad__.mad_strs.get_kwargs_string(**kwargs)
        args_string  ,   args_to_send = self.__mad__.mad_strs.get_args_string(*args)
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


class mad_func(mad_ref):
    # ----------------------------------Calling/Creating functions--------------------------------------#
    def __call_func(self, funcName: str, *args):
        """Call the function funcName and store the result in ``__last__``."""
        rtrn_ref = mad_reflast(self.__mad__)
        args_string, vars_to_send = self.__mad__.mad_strs.get_args_string(*args)
        self.__mad__.send(
            f"{rtrn_ref.__name__} = __mklast__({funcName}({args_string}))\n"
        )
        for var in vars_to_send:
            self.__mad__.send(var)
        return rtrn_ref
    # ---------------------------------------------------------------------------------------------------#
    
    def __call__(self, *args: Any) -> Any:
        ismethod = self.__parent__ and self.__mad__.safe_recv(f"""
        MAD.typeid.is_object({self.__parent__}) or MAD.typeid.isy_matrix({self.__parent__})
        """)
        if ismethod:
            return self.__call_func(self.__name__, self.__parent__, *args)
        else:
            return self.__call_func(self.__name__, *args)
    def __dir__(self):
        return super(mad_ref, self).__dir__()

# Separate class for __last__ objects for simplicity and fewer if statements
class mad_last(): # The init and del for a __last__ object
    def __init__(self, mad_proc):
        self.__lastnum__ = mad_proc.last_counter.get()
        self.__name__ = f"__last__[{self.__lastnum__}]"
        self.__mad__ = mad_proc
        self.__parent__ = "__last__"
    
    def __del__(self):
        self.__mad__.last_counter.set(self.__lastnum__)

class mad_reflast(mad_last, mad_ref):
    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        obj = self.eval()
        if isinstance(obj, (mad_obj, mad_func)):
            return obj(*args, **kwargs)
        else:
            raise TypeError("Cannot call " + str(obj))
    
    def __dir__(self):
        return super(mad_reflast, self).__dir__()

class mad_objlast(mad_last, mad_obj):
    pass
