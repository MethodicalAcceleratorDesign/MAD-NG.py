from typing import Iterable, Union, Any  # To make stuff look nicer
import numpy as np

# TODO: Are you able to store the actual parent? If so, you could use https://docs.python.org/3/c-api/refcounting.html instead.
class madReference(object):
    __last__reference_counter = {}
    
    def __init__(self, name: str, mad):
        assert name is not None, "Reference must have a variable to reference to. Did you forget to put a name in the receive functions?"
        self.__name__ = name
        split_name = name.split("[")
        self.__parent__ = (
            "[" in name and "[".join(split_name[:-1]) or None
        )  # if name is compound, get parent by string manipulation
        self.__mad__ = mad
        if name[:8] == "__last__":
            if len(split_name) == 2:
                self.__is_base__ = True
            else:
                self.__is_base__ = False
    
    def __safe_send__(self, string):
        return self.__mad__.send(f"py:__err(true); {string}; py:__err(false);")

    def __getattr__(self, item):
        if item[0] != "_":
            try:
                return self[item]
            except (IndexError, KeyError):
                pass
        raise AttributeError (item)  # For python

    def __setattr__(self, item, value):
        if item[0] == "_":
            return super(madReference, self).__setattr__(item, value)
        self[item] = value

    def __getitem__(self, item: Union[str, int]):
        if isinstance(item, int):
            result = self.__mad__.recv_vars(self.__name__ + f"[ {item + 1} ]")
            if result is None:
                raise IndexError(item)  # For python
        elif isinstance(item, str):
            result = self.__mad__.recv_vars(self.__name__ + f"['{item    }']")
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
            self.__mad__.send_vars(self.__name__ + f"[ {item + 1} ]", value)
        elif isinstance(item, str):
            self.__mad__.send_vars(self.__name__ + f"['{item    }']", value)
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
        last_name = self.__mad__._MAD__last_counter.get()
        self.__safe_send__(f"{last_name} = {self.__name__} {operator} py:recv()").send(rhs)
        return madReference(last_name, self.__mad__)

    def __len__(self):
        return self.__safe_send__(f"py:send(#{self.__name__})").recv()

    def __str__(self):
        val = self.__mad__[self.__name__]
        if isinstance(val, madReference):
            return repr(val)
        else:
            return str(val)

    def eval(self):
        return self.__mad__[self.__name__]

    def __repr__(self):
        return f"MAD-NG Object(Name: {self.__name__}, Parent: {self.__parent__})"

    def __dir__(self) -> Iterable[str]:
        name = self.__name__
        if name[:8] == "__last__":
            name = name + ".__metatable or " + name
        script = f"""
            local modList={{}}; local i = 1;
            for modname, mod in pairs({name}) do modList[i] = modname; i = i + 1; end
            py:send(modList)"""
        self.__safe_send__(script)
        varnames = [x for x in self.__mad__.recv() if isinstance(x, str)]
        return varnames

    def __del__(self):
        if self.__name__[:8] == "__last__" and self.__is_base__:
            self.__mad__._MAD__last_counter.set(int(self.__name__[9:-1]))

class madObject(madReference):
    def __dir__(self) -> Iterable[str]:
        if not self.__mad__.ipython_use_jedi:
            self.__safe_send__(f"py:send({self.__name__}:get_varkeys(MAD.object))")

        self.__safe_send__(f"py:send({self.__name__}:get_varkeys(MAD.object, false))")
        varnames = [x for x in self.__mad__.recv()]

        if not self.__mad__.ipython_use_jedi:
            varnames.extend([x + "()" for x in self.__mad__.recv() if not x in varnames])
        return varnames

    def __call__(self, *args, **kwargs):
        last_name = self.__mad__._MAD__last_counter.get()
        kwargs_string, kwargs_to_send = self.__mad__._MAD__get_kwargs_string(**kwargs)
        args_string  ,   args_to_send = self.__mad__._MAD__get_args_string(*args)
        vars_to_send = kwargs_to_send + args_to_send
        self.__mad__.send(
            f"{last_name} = __mklast__( {self.__name__} {{ {kwargs_string[1:-1]} {args_string} }} )"
        )
        for var in vars_to_send:
            self.__mad__.send(var)
        return madObject(last_name, self.__mad__)

    def __iter__(self):
        self.__iterIndex__ = -1
        return self

    def __next__(self):
        try:
            self.__iterIndex__ += 1
            return self[self.__iterIndex__]
        except IndexError:
            raise StopIteration


class madFunction(madReference):
    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        ismethod = self.__parent__ and self.__safe_send__(f"""
        py:send(MAD.typeid.is_object({self.__parent__}) or MAD.typeid.isy_matrix({self.__parent__}))"""
        ).recv()
        if ismethod:
            return self.__mad__._MAD__call_func(self.__name__, self.__parent__, *args)
        else:
            return self.__mad__._MAD__call_func(self.__name__, *args)
    def __dir__(self):
        return super(madReference, self).__dir__()
