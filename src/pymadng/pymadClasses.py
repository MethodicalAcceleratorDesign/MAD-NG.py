from typing import Iterable, Union, Any  # To make stuff look nicer
import numpy as np


class madReference(object):
    def __init__(self, name, mad):
        self.__name__ = name
        self.__parent__ = (
            name and "[" in name and "[".join(name.split("[")[:-1]) or None
        )  # if name is compound, get parent by string manipulation
        self.__mad__ = mad

    def __getattr__(self, item):
        try:
            return self[item]
        except (IndexError, KeyError):
            pass
        raise (AttributeError(item))  # For python

    def __setattr__(self, item, value):
        if "__" == item[:2]:
            return super(madReference, self).__setattr__(item, value)
        self[item] = value

    def __getitem__(self, item: Union[str, int]):
        if isinstance(item, int):
            result = self.__mad__.recv_vars(self.__name__ + f"[ {item + 1} ]")
            if result is None:
                raise (IndexError(item))  # For python
        elif isinstance(item, str):
            result = self.__mad__.recv_vars(self.__name__ + f"['{item    }']")
            if result is None:
                raise (KeyError(item))  # For python
        else:
            raise (TypeError("Cannot index type of ", type(item)))

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
            raise (TypeError("Cannot index type of ", type(item)))

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
            self.__gOp__(rhs, "==")
            return self.__mad__["__last__"]

    def __gOp__(self, rhs, operator: str):
        self.__mad__.send(f"__last__ = {self.__name__} {operator} py:recv()")
        self.__mad__.send(rhs)
        return madReference("__last__", self.__mad__)

    def __len__(self):
        self.__mad__.send(f"py:send(#{self.__name__})")
        return self.__mad__.recv()

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
        script = f"""
            local modList={{}}; local i = 1;
            for modname, mod in pairs({self.__name__}) do modList[i] = modname; i = i + 1; end
            py:send(modList)"""
        self.__mad__.send(script)
        varnames = [x for x in self.__mad__.recv() if x[:2] != "__"]
        #Below will potentially break
        # for i in range(len(varnames)):
        #     if isinstance(self[varnames[i]], madFunctor):
        #         varnames[i] += "(...)"
        return varnames


class madObject(madReference):
    def __dir__(self) -> Iterable[str]:
        self.__mad__.send(f"py:send({self.__name__}:get_varkeys(MAD.object))")
        self.__mad__.send(f"py:send({self.__name__}:get_varkeys(MAD.object, false))")
        varnames = [x for x in self.__mad__.recv() if x[:2] != "__"]
        varnames.extend([x + "()" for x in self.__mad__.recv() if x[:2] != "__" and not x in varnames])
        return varnames

    def __call__(self, *args, **kwargs):
        self.__mad__.send(
            f"""
            __last__ = __mklast__( {self.__name__} {{ 
                {self.__mad__._MAD__getKwargAsString(**kwargs)[1:-1]} 
                {self.__mad__._MAD__getArgsAsString(*args)} }} 
                )
            """
        )
        return madObject("__last__", self.__mad__)

    def __iter__(self):
        self.__iterIndex__ = -1
        return self

    def __next__(self):
        try:
            self.__iterIndex__ += 1
            return self[self.__iterIndex__]
        except IndexError:
            raise StopIteration


class madFunctor(madReference):
    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        if self.__parent__ and isinstance(
            self.__mad__[self.__parent__], (madObject, np.ndarray)
        ):
            return self.__mad__.call_func(self.__name__, self.__parent__, *args)
        else:
            return self.__mad__.call_func(self.__name__, *args)
