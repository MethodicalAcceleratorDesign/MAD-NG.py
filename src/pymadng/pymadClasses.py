from typing import Iterable, Union, Any  # To make stuff look nicer


class madReference(object):
    def __init__(self, name, mad):
        self.__name__ = name
        self.__parent__ = (
            name and "." in name and ".".join(name.split(".")[:-1]) or None
        )  # No need for or?
        self.__mad__ = mad

    def __getattribute__(self, item):
        if (
            item
            in [
                "iterVars",
                "iterIndex",
                "method",
                "set",
            ]
            or "__" == item[:2]
        ):
            return super(madReference, self).__getattribute__(item)
        return self.__mad__.receiveVar(self.__name__ + "." + item)

    def __setattr__(self, item, value):
        if (
            item
            in [
                "iterVars",
                "iterIndex",
                "method",
                "set",
            ]
            or "__" == item[:2]
        ):
            return super(madReference, self).__setattr__(item, value)
        self.__mad__.sendVar(self.__name__ + "." + item, value)

    def __getitem__(self, item: Union[str, int]):
        if isinstance(item, int):
            result = self.__mad__.receiveVar(self.__name__ + f"[ {item + 1} ]")
        elif isinstance(item, str):
            result = self.__mad__.receiveVar(self.__name__ + f"['{item    }']")
        else:
            result = None
        if result is None:
            raise (IndexError(item))
        return result

    def __setitem__(self, item, value):
        self.__mad__.sendVar(self.__name__ + "." + item, value)

    def __dir__(self) -> Iterable[str]:
        script = f"""
            local modList={{}}; local i = 1;
            for modname, mod in pairs({self.__name__}) do modList[i] = modname; i = i + 1; end
            py:send(modList)"""
        self.__mad__.send(script)
        return [x for x in self.__mad__.recv() if x[:2] != "__"]

    def method(self, methodName: str, resultName: str, *args):
        return self.__mad__.callMethod(resultName, self.__name__, methodName, *args)


class madObject(madReference):
    def __dir__(self) -> Iterable[str]:
        self.__mad__.send(f"py:send({self.__name__}:get_varkeys(MAD.object))")
        varnames = [x for x in self.__mad__.recv() if x[:2] != "__"]
        return varnames

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.__mad__._setupClass(self.__name__, *args, **kwargs)
        

    def __iter__(self):
        self.__iterIndex__ = -1
        return self

    def __next__(self):
        try:
            self.__iterIndex__ += 1
            return self[self.__iterIndex__]
        except IndexError:
            pass
        raise StopIteration


class madFunctor(madObject):
    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        if self.__parent__ and isinstance(self.__mad__[self.__parent__], madObject):
            return self.__mad__.callFunc(self.__name__, self.__parent__, *args)
        else:
            return self.__mad__.callFunc(self.__name__, *args)