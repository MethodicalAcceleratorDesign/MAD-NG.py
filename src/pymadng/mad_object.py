import numpy as np  # For arrays  (Works well with multiprocessing and mmap)
from typing import Any, Iterable, Union, Tuple  # To make stuff look nicer
from types import MethodType  # Used to attach functions to the class

# Custom Classes:
from .pymadClasses import madObject, madFunctor, madReference
from .mad_process import mad_process

# TODO: implement yield into MAD - Why?
# TODO: place into MAD's MADX environment - Still debating 
# TODO: Have error if when importing, thing isn't found???
# TODO: Make it so that MAD does the loop for variables not python (speed)
# TODO: Look into how to use repr!!!!!!! (May simplify string iterpolation)


class MAD(object):  # Review private and public
    def __init__(
        self, pyName: str = "py", madPath: str = None, debug: bool = False
    ) -> None:
        """
        Initialise MAD Object.
        pyName: The name used to interact with the python process from MAD; default = "py"
        madPath: The path to the mad executable; default = None (So the one that comes with pymadng package will be used)
        debug: Sets debug mode on or off; default = False
        """
        self.__process = mad_process(pyName, madPath, debug, self)
        self.pyName = pyName
        # --------------------------------Retrieve the modules of MAD-------------------------------#
        # Limit the 80 modules
        modulesToImport = [
            "MAD",  # Need MAD.MAD?
            "elements",
            "sequence",
            "mtable",
            "twiss",
            "beta0",
            "beam",
            "survey",
            "object",
            "track",
            "match",
        ]
        self.Import("MAD", modulesToImport)
        self.Import("MAD.element")
        self.__dict__["MADX"] = madObject("MADX", self)

    # ------------------------------------------------------------------------------------------#

    def send(self, data: Union[str, int, float, np.ndarray, bool, list]) -> None:
        """Send data to MAD, equivalent to recv"""
        self.__process.send(data)

    def recv(self) -> Union[str, int, float, np.ndarray, bool, list]:
        """Receive data from MAD and return it, equivalent to receive"""
        return self.__process.recv()

    def receive(self) -> Union[str, int, float, np.ndarray, bool, list]:
        """Receive data from MAD and return it, equivalent to recv"""
        return self.__process.recv()

    def recv_and_exec(self, env: dict = {}) -> dict:
        """Receive a string from MAD and execute it"""
        return self.__process.recv_and_exec(env)

    def send_rng(self, rng: Union[np.ndarray, list]):
        """Send a numpy array as a range to MAD"""
        return self.__process.send_rng(rng)

    def send_lrng(self, lrng: Union[np.ndarray, list]):
        """Send a numpy array as a logrange to MAD"""
        return self.__process.send_lrng(lrng)

    def Import(self, moduleName: str, varsToImport: list[str] = []):
        """Retrieve the classes in MAD from the module "moduleName", while only importing the classes in the list "classNames".
        If no list is provided, it is assumed that you would like to import every class from the module"""
        script = ""
        if varsToImport == []:
            varsToImport = dir(madReference(moduleName, self))
        for className in varsToImport:
            script += f"""{className} = {moduleName}.{className}\n"""
        self.__process.send(script)

    def __getattribute__(self, item):
        try:
            return super(MAD, self).__getattribute__(item)
        except AttributeError:
            return self.receiveVar(item)

    # -----------------------------Make the class work like a dictionary----------------------------#
    def __setitem__(self, varName: str, var: Any) -> None:
        if isinstance(varName, tuple):
            nameList = list(varName)
            varList = list(var)
            if len(varList) != len(nameList):
                raise ValueError(
                    "Incorrect number of values to unpack, received",
                    len(varList),
                    "variables and",
                    len(nameList),
                    "keys",
                )
            self.sendVariables(nameList, varList)
        else:
            self.sendVar(varName, var)

    def __getitem__(self, varName: str) -> Any:
        return self.receiveVar(varName)

    # ----------------------------------------------------------------------------------------------#

    # --------------------------------Sending data to subprocess------------------------------------#
    def eval(self, input: str):
        """Evaluate an expression. Start the expression with '=' to receive the return value."""
        if input[0] == "=":
            input = "__last__" + input
            self.__process.send(input)
            return self["__last__"]
        else:
            self.__process.send(input)

    def MADX_env_send(self, input: str):
        return self.__process.send("MADX:open_env()\n" + input + "\nMADX:close_env()")

    # ----------------------------------------------------------------------------------------------#

    # ----------------------------------Sending variables across to MAD----------------------------------------#
    def sendVariables(
        self,
        varNames: list[str],
        vars: list[Union[np.ndarray, int, float, list]],
    ):
        """Send variables to the MAD process, either send a list of varNames along with a list of the data"""
        for i in range(len(vars)):
            self.__process.send(f"{varNames[i]} = {self.pyName}:recv()")
            self.__process.send(vars[i])

    def sendVar(self, varName: str, var: Union[np.ndarray, int, float, list]):
        """Send a variable "var" to the MAD process and give it the name "varName" """
        self.sendVariables([varName], [var])

    # -------------------------------------------------------------------------------------------------------------#

    # -----------------------------------Receiving variables from to MAD-------------------------------------------#
    def receiveVariables(self, varNameList: list[str]) -> Any:
        """Given a list of variable names, receive the variables from the MAD process"""
        returnVars = []
        for i in range(len(varNameList)):
            if (
                varNameList[i][:2] != "__" or "__last__" in varNameList[i]
            ):  # Check for private variables
                self.__process.send(f"{self.pyName}:send({varNameList[i]})")
                returnVars.append(self.__process.recv(varNameList[i]))
        return tuple(returnVars)

    def receiveVar(self, var: str) -> Any:
        """Recieve a single variable 'var' from the MAD process"""
        return self.receiveVariables([var])[0]

    # -------------------------------------------------------------------------------------------------------------#

    # ----------------------------------Calling/Creating functions-------------------------------------------------#
    def callFunc(self, funcName: str, *args):
        """Call the function funcName and store the result in __last__"""
        self.__process.send(
            f"__last__ = {self.getAsMADString(funcName)}({self.__getArgsAsString(*args)})\n"
        )
        return madReference("__last__", self)

    def callMethod(  # Needed?
        self, resultName: Union[str, list[str]], varName: str, methName: str, *args
    ):
        """Call the method methName of the variable varName and store the result in resultName, then retreive the result into the MAD dictionary (may be removed)"""
        if isinstance(resultName, list):
            stringStart = f"{self.getAsMADString(resultName)} = "
        elif resultName:
            stringStart = f"{self.getAsMADString(resultName)} = "
            resultName = [resultName]
        else:
            stringStart = ""
        self.__process.send(
            stringStart
            + f"""{self.getAsMADString(varName)}:{self.getAsMADString(methName)}({self.__getArgsAsString(*args)})\n"""
        )

    def MADLambda(self, arguments: list[str], expression: str):
        """Create a small anonymous function in MAD named __last__"""
        result = "__last__ = \\"
        if arguments:
            for arg in arguments:
                result += self.getAsMADString(arg) + ","
            result = result[:-1]
        self.send(result + " -> " + expression)
        return madFunctor("__last__", None, self)

    # -------------------------------------------------------------------------------------------------------------#

    # -------------------------------String Conversions--------------------------------------------------#
    def __getKwargAsString(self, **kwargs):
        # Keep an eye out for failures when kwargs is empty, shouldn't occur in current setup
        """Convert a keyword argument input to a string used by MAD, should not be required by the user"""
        kwargsString = "{"
        for key, item in kwargs.items():
            keyString = str(key).replace("'", "")
            itemString = self.getAsMADString(item)
            kwargsString += keyString + " = " + itemString + ", "
        return kwargsString + "}"

    def __getArgsAsString(self, *args):
        """Convert an argument input to a string used by MAD, should not be required by the user"""
        argStr = ""
        for arg in args:
            argStr += self.getAsMADString(arg) + ", "
        return argStr[:-2]  # Assumes args is always put last

    def getAsMADString(self, var: Any, convertString=False):
        """Convert a list of objects into the required string for MAD"""
        if isinstance(var, (list, np.ndarray)):
            return self.__pyToLuaLst(var)
        elif var == None:
            return "nil"
        elif isinstance(var, str) and convertString:
            return "'" + var + "'"
        elif isinstance(var, complex):
            return str(var).replace("j", "i")
        elif isinstance(var, (madReference)):
            return var.__name__
        elif isinstance(var, dict):
            return self.__getKwargAsString(**var)
        elif callable(var):
            return var.__name__
        else:
            return str(var).replace("False", "false").replace("True", "true")

    def __pyToLuaLst(self, lst: list[Any]) -> str:
        """Convert a python list to a lua list in a string, used when sending information to MAD, should not need to be accessed by user"""
        luaString = "{"
        for item in lst:
            luaString += self.getAsMADString(item, True) + ", "
        return luaString + "}"
    # ---------------------------------------------------------------------------------------------------#

    # -------------------------------Setup MAD Classes---------------------------------------------------#
    def _setupClass(
        self,
        className: str,
        *args,
        **kwargs,
    ):
        """Create a class 'className' from the module 'moduleName' and store into the variable '__last__'
        the kwargs are used to as extra keyword arguments within MAD. Should not be needed by the user """
        self.__process.send(
            f"""
            __last__ = {{ {className} {{ {self.__getKwargAsString(**kwargs)[1:-1]} {self.__getArgsAsString(*args)} }} }}
            """
        )
        return madReference("__last__", self)

    def __todeferred(self, **kwargs):
        """Return a where the kwargs are used as the deffered expressions, specified using strings"""
        return self.__getKwargAsString(**kwargs).replace("=", ":=")[1:-3]
        # Change := to equals, remove string identifers, and remove ", "

    def deferred(self, **kwargs):
        """Create a deferred expression object where the kwargs are used as the deffered expressions"""
        self.__process.send(
            f"__last__ = {{ MAD.typeid.deferred {{{self.__todeferred(**kwargs)}}} }}"
        )
        return madReference("__last__", self)

    def loadsequence(self, seqFilename: str, targetFile: str = None):
        """Load a MAD-X sequence from the file seqFilename. Optionally add a targetFile, which is the MAD version of the sequence file"""
        if not targetFile:
            targetFile = seqFilename.strip(".seq")
        self.__process.send(
            f"""
            MADX:load("{seqFilename}", "{targetFile}")
            __last__ = MADX.seq
            """
        )
        return madReference("__last__", self)

    def __dir__(self) -> Iterable[str]:
        return [x for x in super(MAD, self).__dir__() if x[0] != "_"].extend(self.env())

    def env(self) -> list[str]:
        """Retrive the environment of MAD"""
        return dir(self.receiveVar(f"{self.pyName}._env"))

    # -------------------------------For use with the "with" statement-----------------------------------#
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        del self

    # ---------------------------------------------------------------------------------------------------#
