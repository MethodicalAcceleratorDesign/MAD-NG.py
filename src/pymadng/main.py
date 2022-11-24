import numpy as np  # For arrays  (Works well with multiprocessing and mmap)
from typing import Any, Iterable, Union, Tuple  # To make stuff look nicer
from types import MethodType  # Used to attach functions to the class

# Custom Classes:
from .pymadClasses import madObject, madFunctor, madReference
from .mad_process import mad_process

# TODO: implement yield into MAD
# TODO: place into MAD's MADX environment
# TODO: Have error if when importing, thing isn't found???
# TODO: Make it so that MAD does the loop for variables not python (speed)
# TODO: MADkwargs is a botched fix, not a fan of its
# TODO: Look into how to use repr!!!!!!! (May simplify string iterpolation)


class MAD(object):  # Review private and public
    def __init__(
        self, pyName: str = "py", madPath: str = None, debug: bool = False
    ) -> None:
        """
        Initialise MAD Object.
        pyname: The name used to interact with the python process from MAD; default = "py"
        madPath: The path to the mad executable; default = None (Use the one that comes with pymadng)
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
        self.importClasses("MAD", modulesToImport)
        self.importClasses("MAD.element")
        self.__dict__["MADX"] = madObject("MADX", self)

    # ------------------------------------------------------------------------------------------#

    def send(self, input: Union[str, int, float, np.ndarray, bool, list]) -> None:
        return self.__process.send(input)

    def recv(self) -> dict:
        return self.__process.recv()

    def receive(self) -> dict:
        return self.__process.recv()

    def recv_and_exec(self, env: dict = {}) -> dict:
        return self.__process.recv_and_exec(env)

    def send_rng(self, rng: Union[np.ndarray, list]):
        return self.__process.send_rng(rng)

    def send_lrng(self, lrng: Union[np.ndarray, list]):
        return self.__process.send_lrng(lrng)

    def retrieveMADClasses(self, moduleName: str, classNames: list[str] = []):
        """Retrieve the classes in MAD from the module "moduleName", while only importing the classes in the list "classNames".
        If no list is provided, it is assumed that you would like to import every class from the module"""
        script = ""
        if classNames == []:
            classNames = dir(madReference(moduleName, self))
        for className in classNames:
            script += f"""{className} = {moduleName}.{className}\n"""
        self.__process.send(script)

    def importClasses(self, moduleName: str, classesToImport: list[str] = []):
        # Maybe not have this and have init function instead?
        """Import uninitialised variables into the local environment (necessary?)"""
        self.retrieveMADClasses(moduleName, classesToImport)

    def importVariables(self, moduleName: str, varsToImport: list[str] = []):
        """Import initialised variables into the local environment (necessary?)"""
        self.retrieveMADClasses(moduleName, varsToImport)

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
        """Send variables to the MAD process, either send a list of varNames that already exist in the python MAD class or the varNames along with a list of the data"""
        for i in range(len(vars)):
            self.__process.send(f"{varNames[i]} = {self.pyName}:recv()")
            self.__process.send(vars[i])

    def sendVar(self, varName: str, var: Union[np.ndarray, int, float, list]):
        """Send a variable to the MAD process, either send a varName that already exists in the python MAD class or a varName along with data"""
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
        """Recieve a single variable from the MAD process"""
        return self.receiveVariables([var])[0]

    # -------------------------------------------------------------------------------------------------------------#

    # ----------------------------------Calling/Creating functions-------------------------------------------------#
    def callFunc(self, funcName: str, *args):
        """Call the function funcName and store the result in resultName, then retreive the result into the MAD dictionary"""
        self.__process.send(
            f"__last__ = {self.getAsMADString(funcName)}({self.__getArgsAsString(*args)})\n"
        )

    def callMethod(  # Needed?
        self, resultName: Union[str, list[str]], varName: str, methName: str, *args
    ):
        """Call the method methName of the variable varName and store the result in resultName, then retreive the result into the MAD dictionary"""
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
        """Convert a kwargs input to a string used by MAD, should not be required by the user"""
        kwargsString = "{"
        for key, item in kwargs.items():
            keyString = str(key).replace("'", "")
            if isinstance(item, str):  # Need to keep strings in kwargs
                item = "'" + item + "'"
            itemString = self.getAsMADString(item)
            kwargsString += keyString + " = " + itemString + ", "
        return kwargsString + "}"

    def __getArgsAsString(self, *args):
        argStr = ""
        for arg in args:
            argStr += self.getAsMADString(arg) + ", "
        return argStr[:-2]  # Assumes args is always put last

    def getAsMADString(self, var: Any, convertString=False):
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

    def MADKwargs(self, varName: str, *args, **kwargs):
        if varName:
            start = f"{varName} = "
        else:
            start = ""
        return (
            start
            + f"""{{ {self.__getKwargAsString(**kwargs)[1:-1]} {self.__getArgsAsString(*args)} }} """
        )

    # ---------------------------------------------------------------------------------------------------#

    # -------------------------------Setup MAD Classes---------------------------------------------------#
    def _setupClass(
        self,
        className: str,
        *args,
        **kwargs,
    ):
        """Create a class 'className' from the module 'moduleName' and store into the variable '__last__'
        the kwargs are used to as extra keyword arguments within MAD"""
        self.__process.send(
            f"""
            __last__ = {{ {className} {{ {self.__getKwargAsString(**kwargs)[1:-1]} {self.__getArgsAsString(*args)} }} }}
            """
        )

    def defExpr(self, **kwargs):
        """Create a deffered expression object where the kwargs are used as the deffered expressions, specified using strings"""
        return (
            self.__getKwargAsString(**kwargs).replace("=", ":=").replace("'", "")[1:-3]
        )  # Change := to equals, remove string identifers, and remove ", "

    def deferred(self, **kwargs):
        """Create a deferred expression object with the name "varName" where the kwargs are used as the deffered expressions, specified using strings"""
        self.__process.send(
            f"__last__ = {{ MAD.typeid.deferred {{{self.defExpr(**kwargs)}}} }}"
        )
        return madReference("__last__", self)

    def loadsequence(self, seqFilename: str, targetFile: str = None):
        """Load a MAD-X sequence from the file seqFilename and into the variable 'seqName'. Optionally add a targetFile, which is the MAD version of the sequence file"""
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
        return dir(self.receiveVar(f"{self.pyName}._env"))

    # -------------------------------For use with the "with" statement-----------------------------------#
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        del self

    # ---------------------------------------------------------------------------------------------------#
