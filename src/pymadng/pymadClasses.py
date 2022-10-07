import numpy as np
from typing import Union  # To make stuff look nicer

# TODO: Make each madObject have a list of objects that obeys a print function
# TODO: Make dot overload more stable -> Could you load a module and instead only overload the dot for everything within the module?


class madObject(object):
    def __init__(self, name, mad):
        self.__name__ = name
        self.__mad__ = mad

    def __getattribute__(self, item):
        if (
            item
            in [
                "attachedElements",
                "attributes",
                "iterVars",
                "iterIndex",
                "method",
            ]
            or "__" == item[:2]
        ):
            return super(madObject, self).__getattribute__(item)
        self.__mad__.receiveVariables([self.__name__ + "." + item])
        return self.__mad__.__getattribute__(self.__name__ + "." + item)

    def __setattr__(self, item, value):
        if (
            item
            in [
                "attachedElements",
                "attributes",
                "iterVars",
                "iterIndex",
                "method",
            ]
            or "__" == item[:2]
        ):
            return super(madObject, self).__setattr__(item, value)
        if isinstance(value, madObject):
            self.__mad__.sendScript(
                f"{self.__name__ + '.' + item} = {value.__name__}\n"
            )
        elif isinstance(value, np.ndarray):
            self.__mad__.sendVar(self.__name__ + "." + item, value)

    def __getitem__(self, item: Union[str, int]):
        if isinstance(item, str):
            self.__mad__.receiveVariables([self.__name__ + "." + item])
            return self.__mad__.__getattribute__(self.__name__ + "." + item)
        elif isinstance(item, int):
            self.__mad__.receiveVariables([self.__name__ + "[" + str(item) + "]"])
            return self.__mad__.__getattribute__(self.__name__ + "[" + str(item) + "]")

    def __setitem__(self, item, value):
        if isinstance(value, madObject):
            self.__mad__.sendScript(
                f"{self.__name__ + '.' + item} = {value.__name__}\n"
            )
        elif isinstance(value, np.ndarray):
            self.__mad__.sendVar(self.__name__ + "." + item, value)

    def __str__(self):
        return str(self.__mad__.receiveVariables([self.__name__], shareType="table")[0])

    def method(self, methodName: str, resultName: str, *args):
        return self.__mad__.callMethod(resultName, self.__name__, methodName, *args)


class madElement(madObject):
    attributes = [
        "l",
        "lrad",
        "angle",
        "tilt",
        "model",
        "method",
        "nslice",
        "misalign",
        "apertype",
    ]

    def __init__(self, name, mad):
        self.__name__ = name
        self.__mad__ = mad

        def getKwargAsString(**kwargs):
            kwargList = [
                x.split(",")[-1].replace("'", "") for x in str(kwargs).split(":")[:-1]
            ]  # Replace all the ' in the args (could split up?)
            kvalsList = [
                x.split(",")[0] for x in str(kwargs).split(":")[1:]
            ]  # Do not replace string identifier in vals
            kwargsString = ",".join(
                [kwargList[x] + " =" + kvalsList[x] for x in range(len(kwargList))]
            )
            return kwargsString

        returnElm = (
            lambda funcName=name, **kwargs: f"""{name} '{funcName}' {getKwargAsString(**kwargs)}"""
        )
        setattr(mad, name + "Set", returnElm)

    def __iter__(self):
        self.iterVars = [self.__name__ + "." + attr for attr in self.attributes]
        self.iterIndex = 0
        self.__mad__.receiveVariables(self.iterVars)
        return self

    def __next__(self):
        while self.iterIndex < len(self.attributes):
            attr = self.__mad__[self.__name__ + "." + self.attributes[self.iterIndex]]
            self.iterIndex += 1
            return {self.attributes[self.iterIndex - 1]: attr}
        raise StopIteration


class deferred(madObject):
    pass
