import warnings
import numpy as np  # For arrays  (Works well with multiprocessing and mmap)
from typing import Any, Iterable, Union, Tuple  # To make stuff look nicer
from types import MethodType  # Used to attach functions to the class

# Custom Classes:
from .pymadClasses import madObject, madElement, deferred
from .madProc import mad_process

# TODO: implement yield into MAD
# TODO: Allow looping through objects (Not just elements)
# TODO: don't pollute MAD environment, place into MAD's MADX environment
# TODO: Have error if when importing, thing isn't found
# TODO: Make it so that MAD does the loop for variables not python (speed)
# TODO: Lamdba and kwargs is a botched fix, not a fan of it
# TODO: Recursive dot indexing
# TODO: Add ability to make function asynchronous
# TODO: Make shared memory more secure - flag at end, size and type in buffer, to deal with corrupted data
# TODO: fix madl_mmap int, float and complex sizes to not be constant!
# TODO: Allow sending of integers not always cast to float
# TODO: Fix what happens if mad trys to write too much to the buffer! Then make ability to send in chunks
# TODO: Look into how to use repr!!!!!!! (May simplify string iterpolation)


class MAD(object):  # Review private and public
    def __init__(self, pyName: str = "py", madPath: str = None, debug:bool =False) -> None:
        """
        Initialise MAD Object.
        pyname: The name used to interact with the python process from MAD; default = "py"
        madPath: The path to the mad executable; default = None (Use the one that comes with pymadng)
        debug: Sets debug mode on or off; default = False
        """
        self.process = mad_process(pyName, madPath, debug, self)
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
        return self.process.send(input)
    
    def send_data(self, input: Union[str, int, float, np.ndarray, bool, list]) -> None:
        return self.process.send_data(input)

    def recv(self) -> dict:
        return self.process.recv()
    
    def recv_and_exec(self, env: dict = {}) -> dict:
        return self.process.recv_and_exec(env)

    def retrieveMADClasses(
        self, moduleName: str, requireInitialisation: bool, classNames: list[str] = []
    ):
        """Retrieve the classes in MAD from the module "moduleName", while only importing the classes in the list "classesToImport".
        If no list is provided, it is assumed that you would like to import every class"""
        script = ""
        if classNames == []:
            script += f"""
                       local stringtosend=""
                       function getModName(modname, mod)
                           return [[superClass._import("{moduleName}", "]]..tostring(modname)..[[", "]]..tostring(mod)..[[", {requireInitialisation})\n]]
                       end
                       for modname, mod in pairs({moduleName}) do stringtosend = stringtosend .. getModName(modname, mod); end
                       py:send(stringtosend)"""
        else:
            for className in classNames:
                script += f"""superClass._import("{moduleName}", "{className}", "]].. tostring({moduleName}.{className}) .. [[", {requireInitialisation})\n"""
            script = f"py:send([[{script}]])"
        self.process.send(script)
        self.process.recv_and_exec()

    # CLEAN UP THIS FUNCTION:
    def _import(self, moduleName, varName, varType, requireInitialisation):
        """Only ever called by MAD - DO NOT USE"""
        ##To be improved
        if "function" in varType:
            exec(
                f"""def {varName}(self, resultName, *args): 
            self.callFunc(resultName, "{varName}", *args) """
            )
            setattr(self, varName, MethodType(locals()[varName], self))
        else:
            if requireInitialisation:
                exec(
                    f"""def {varName}(self, varName, *args, **kwargs): 
                self._setupClass("{varName}", "{moduleName}", varName, *args, **kwargs) """
                )
                setattr(self, varName, MethodType(locals()[varName], self))
            else:
                self.__dict__[varName] = madObject(varName, self)
        self.process.send(f"{varName} = {moduleName}.{varName}")

    def importClasses(self, moduleName: str, classesToImport: list[str] = []):
        # Maybe not have this and have init function instead?
        """Import uninitialised variables into the local environment (necessary?)"""
        self.retrieveMADClasses(moduleName, True, classesToImport)

    def importVariables(self, moduleName: str, varsToImport: list[str] = []):
        """Import initialised variables into the local environment (necessary?)"""
        self.retrieveMADClasses(moduleName, False, varsToImport)

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
            input = "_" + input
            self.process.send(input)
            return self._
        else:
            self.process.send(input)

    def MADXInput(self, input: str):
        return self.process.send("MADX:open_env()\n" + input + "\nMADX:close_env()")
    # ----------------------------------------------------------------------------------------------#

    # ----------------------------------Sending variables across to MAD----------------------------------------#
    def sendVariables(
        self,
        varNames: list[str],
        vars: list[Union[np.ndarray, int, float, list]],
    ):
        """Send variables to the MAD process, either send a list of varNames that already exist in the python MAD class or the varNames along with a list of the data"""
        for i in range(len(vars)):
            self.process.send(f"{varNames[i]} = {self.pyName}:recv()")
            self.process.send(vars[i])

    def sendVar(self, varName: str, var: Union[np.ndarray, int, float, list]):
        """Send a variable to the MAD process, either send a varName that already exists in the python MAD class or a varName along with data"""
        self.sendVariables([varName], [var])

    # -------------------------------------------------------------------------------------------------------------#

    # -----------------------------------Receiving variables from to MAD-------------------------------------------#
    def receiveVariables(
        self, varNameList: list[str]
    ) -> Any:
        """Given a list of variable names, receive the variables from the MAD process"""
        returnVars = []
        for i in range(len(varNameList)):
            if varNameList[i][:2] != "__": # Check for private variables
                self.process.send(
                    f"py:send({varNameList[i]})"
                )
                returnVars.append(self.process.recv(varNameList[i]))
        return tuple(returnVars)

    def receiveVar(self, var: str) -> Any:
        """Recieve a single variable from the MAD process"""
        return self.receiveVariables([var])[0]

    # -------------------------------------------------------------------------------------------------------------#

    # ----------------------------------Calling functions(WIP)-----------------------------------------------------#
    # Should result name be provided? ALSO NOT TESTED -->
    def callFunc(self, resultName: Union[str, list[str]], funcName: str, *args):
        """Call the function funcName and store the result in resultName, then retreive the result into the MAD dictionary"""
        if isinstance(resultName, list):
            resultName = self.__pyToLuaLst(resultName)
        if resultName:
            stringStart = f"{self.getAsMADString(resultName)} = "
        else:
            stringStart = ""
        self.process.send(
            stringStart
            + f"""{self.getAsMADString(funcName)}({self.__getArgsAsString(*args)})\n"""
        )
        if resultName:
            return self.receiveVar(resultName)

    def callMethod(
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
        self.process.send(
            stringStart
            + f"""{self.getAsMADString(varName)}:{self.getAsMADString(methName)}({self.__getArgsAsString(*args)})\n"""
        )
        if resultName:
            return self.receiveVariables(resultName)

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
        elif not var:
            return "nil"
        elif isinstance(var, str) and convertString:
            return "'" + var + "'"
        elif isinstance(var, complex):
            return str(var).replace("j", "i")
        elif isinstance(var, (madObject, madElement)):
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

    def MADLambda(self, varName: str, arguments: list[str], expression: str):
        result = self.getAsMADString(varName) + " = \\"
        if arguments:
            for arg in arguments:
                result += self.getAsMADString(arg) + ","
            result = result[:-1]
        return result + " -> " + expression

    # ---------------------------------------------------------------------------------------------------#

    # -------------------------------Setup MAD Classes---------------------------------------------------#
    def _setupClass(
        self,
        className: str,
        moduleName: str,
        resultName: Union[str, list[str]],
        *args,
        **kwargs,
    ):
        """Create a class 'className' from the module 'moduleName' and store into the variable 'varName'
        the kwargs are used to as extra keyword arguments within MAD"""
        if isinstance(resultName, list):
            self.process.send(
                f"""
    {self.__pyToLuaLst(resultName)[1:-3].replace("'", "")} = {className} {{ {self.__getKwargAsString(**kwargs)[1:-1]} {self.__getArgsAsString(*args)} }}
                """
            )
            self.receiveVariables(resultName)  # Make this optional, or not do it
                    
        else:
            self.process.send(
                f"""
    {resultName} = {className} '{resultName}' {{ {self.__getKwargAsString(**kwargs)[1:-1]} {self.__getArgsAsString(*args)} }} 
                """
            )
            if moduleName == "MAD.element":
                self.__dict__[resultName] = madElement(resultName, self)
                returnElm = (
                    lambda _, **kwargs: f"""{resultName} {self.__getKwargAsString(**kwargs)}"""
                )
                setattr(
                    self.__dict__[resultName],
                    "set",
                    MethodType(returnElm, self.__dict__[resultName]),
                )
            else:
                self.__dict__[resultName] = madObject(resultName, self)

    def defExpr(self, **kwargs):
        """Create a deffered expression object where the kwargs are used as the deffered expressions, specified using strings"""
        return (
            self.__getKwargAsString(**kwargs).replace("=", ":=").replace("'", "")[1:-3]
        )  # Change := to equals, remove string identifers, and remove ", "

    def deferred(self, varName: str, **kwargs):
        """Create a deffered expression object with the name "varName" where the kwargs are used as the deffered expressions, specified using strings"""
        self.process.send(
            f"""
            local deferred in MAD.typeid
            {varName} = deferred {{{self.defExpr(**kwargs)}}}
            """
        )
        self.__dict__[varName] = deferred(varName, self)

    def loadsequence(self, seqName: str, seqFilename: str, targetFile: str = None):
        """Load a MAD-X sequence from the file seqFilename and into the variable 'seqName'. Optionally add a targetFile, which is the MAD version of the sequence file"""
        if ".seq" not in seqFilename:
            seqFilename += ".seq"
        if not targetFile:
            targetFile = seqFilename.strip(".seq")
        if ".mad" not in targetFile:
            targetFile += ".mad"
        # Potential failure below - if *args does not contain element set, " may be removed unnecessarily
        self.process.send(
            f"""
            MADX:load("{seqFilename}", "{targetFile}")
            {seqName} = MADX.seq
            """
        )
        self.__dict__[seqName] = madObject(seqName, self)

    def __dir__(self) -> Iterable[str]:
        return [x for x in super(MAD, self).__dir__() if x[0] != "_"]

    # -------------------------------For use with the "with" statement-----------------------------------#
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        del self

    # ---------------------------------------------------------------------------------------------------#
