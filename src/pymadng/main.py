import os, tempfile, warnings, sys, select, time, re, subprocess

# os is used for directorys
# mmap is for memory mapping
# tempfile is for temporarily creating files

import numpy as np  # For arrays  (Works well with multiprocessing and mmap)
from resource import getpagesize  # To get page size
from typing import Any, Union, Tuple  # To make stuff look nicer
from types import MethodType

from sympy import var  # Used to attach functions to the class

# Custom Classes:
from .pymadClasses import madObject, madElement, deferred

# TODO: implement yield into MAD
# TODO: Allow looping through objects (Not just elements)
# TODO: don't pollute MAD environment, place into MAD's MADX environment
# TODO: Have error if when importing, thing isn't found
# TODO: Improve method syntax
# TODO: Have every string send to mad go through the same converter - prevent duplication
# TODO: Make it so that MAD does the loop for variables not python (speed)
# TODO: Lamdba and kwargs is a botched fix, not a fan of it
# TODO: Recursive dot indexing
# TODO: Add ability to make function asynchronous
# TODO: Make shared memory more secure - flag at end, size and type in buffer, to deal with corrupted data
# TODO: fix madl_mmap int, float and complex sizes to not be constant!
# TODO: Allow sending of integers not always cast to float
# TODO: Fix what happens if mad trys to write too much to the buffer! Then make ability to send in chunks


class MAD:  # Review private and public
    __PAGE_SIZE = getpagesize()  # To allow to work on multiple different machines
    userVars = {}
    process = None
    mad_is_running_scipt = False
    pipeRead = ""

    def __init__(
        self,
        srcdir: str = None,  # need to be optional?
        log: bool = False,
        ram_limit: int = 2**30 + 2**12,
        copyOnRetreive: bool = True,
    ) -> None:
        """Initialise MAD Object.
        Optional Arguments:
        srcdir (str): If not running this python program in MAD/src/pymad, enter the SRC directory
        log (bool): True means the sending and receiving data is logged
        ram_limit (int): How much ram memory you would like to limit the program to using.
        copyOnRetrieve (bool): When True, the variables are copied from the memory mapping when assigned to a variable outside MAD. When False, you receive a memory mapped numpy array that if transferred outside the MAD class, will have to be manually dealt with
        """
        # Init shared memory related variables
        self.RAM_LIMIT = int(ram_limit)
        self.copyOnRetreive = copyOnRetreive
        self.__tmpFldr = tempfile.mkdtemp(prefix="pymadng-") + "/"
        self.__madScriptFd, self.__madScriptDir = tempfile.mkstemp(
            prefix="madscript-", dir=self.__tmpFldr
        )
        self.__pyScriptFd, self.__pyScriptDir = tempfile.mkstemp(
            prefix="pyscript-", dir=self.__tmpFldr
        )
        os.close(self.__pyScriptFd)
        if not srcdir:
            srcdir = os.path.dirname(os.path.abspath(__file__)) + "/"
        if srcdir[-1] != "/":
            srcdir += "/"
        self.SRC_DIR = srcdir
        self.PATH_TO_MAD = srcdir + "mad"
        self.globalVars = {"np": np}
        self.pipeDir = self.__tmpFldr + "pipe"

        # Setup communication pipe
        os.mkfifo(self.pipeDir)

        # Create initial file when MAD process is created
        INITIALISE_SCRIPT = f"""
        sharedata, sharetable, close, writeToPipe, setupScript = require ("madl_buffer").sharedata, require ("madl_buffer").sharetable, require ("madl_buffer").close, require ("madl_buffer").writeToPipe, require ("madl_buffer").setupScript\n
        local openPipe in require("madl_buffer")
        openPipe("{self.pipeDir}")
        setupScript("{self.__pyScriptDir}")
       """

        # shell = True; security problems?
        self.process = subprocess.Popen(
            self.PATH_TO_MAD + " -q" + " -i",
            shell=True,
            bufsize=0,
            stdout=sys.stdout,
            stderr=sys.stdout,
            stdin=subprocess.PIPE,
        )  # , universal_newlines=True)
        try:  # See if it closes in 10 ms (1 ms is too quick)
            self.process.wait(0.1)
            self.close()
            raise (
                OSError(
                    f"Unsuccessful opening of {self.PATH_TO_MAD}, process closed immediately"
                )
            )
        except subprocess.TimeoutExpired:
            pass
        if log:
            # ----------Optional Logging-------------#
            self.inputFile = open(os.getcwd() + "/inLog.txt", "w")
            self.process.logfile_send = self.inputFile
            # ---------------------------------------#
        self.log = log

        # Wait for mad to be ready for input
        self.sendScript(INITIALISE_SCRIPT, False)

        # Now read from pipe as write end is open
        self.pipe = os.open(self.pipeDir, os.O_RDONLY)
        self.pollIn = select.poll()
        self.pollIn.register(self.pipe, select.POLLIN)
        self.pipeMatch = re.compile(
            r"(?P<commands>(pyCommand:.*\n)*)\n*(?P<status>finished|continue)?"
        )
        self.execCheck = re.compile(r"self.__dict__\['.+\] = ")
        # self.writeToProcess("_PROMPT = ''") #Change this to change how output works

        # --------------------------------Retrieve the modules of MAD-------------------------------#
        # Limit the 80 modules
        modulesToImport = [
            # "MAD", #Need MAD.MAD?
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

    def retrieveMADClasses(
        self, moduleName: str, requireInitialisation: bool, classNames: list[str] = []
    ):
        """Retrieve the classes in MAD from the module "moduleName", while only importing the classes in the list "classesToImport".
        If no list is provided, it is assumed that you would like to import every class"""
        script = f"""local tostring = tostring\n"""
        if classNames == []:
            script += f"""
                       function getModName(modname, mod)
                           writeToPipe('pyCommand:self._import("{moduleName}", "'..tostring(modname)..'", "'..tostring(mod)..'", {requireInitialisation})\\n')\n
                       end
                       for modname, mod in pairs({moduleName}) do pcall(getModName, modname, mod); end writeToPipe("\\n")"""
        else:
            for className in classNames:
                script += f"""writeToPipe('pyCommand:self._import("{moduleName}", "{className}", "'.. tostring({moduleName}.{className}) .. '", {requireInitialisation})\\n')\n"""
        self.sendScript(script)

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
                self.setupClass("{varName}", "{moduleName}", varName, *args, **kwargs) """
                )
                setattr(self, varName, MethodType(locals()[varName], self))
            else:
                self.__dict__[varName] = madObject(varName, self)
        self.sendScript(f"{varName} = {moduleName}.{varName}\n")

    def importClasses(self, moduleName: str, classesToImport: list[str] = []):
        """Import uninitialised variables into the local environment (necessary?)"""
        self.retrieveMADClasses(moduleName, True, classesToImport)

    def importVariables(self, moduleName: str, varsToImport: list[str] = []):
        """Import initialised variables into the local environment (necessary?)"""
        self.retrieveMADClasses(moduleName, False, varsToImport)

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
        else:
            nameList = [varName]
            varList = [var]
        for i in range(len(nameList)):
            if type(varList[i]) == list:
                varList[i] = np.array(
                    varList[i]
                )  # So the user isn't forced to initialise the array as numpy
            self.__dict__[nameList[i]] = varList[i]
            if not isinstance(varList[i], madObject):
                self.userVars[
                    nameList[i]
                ] = None  #####Double check if this is necessary
        self.sendVariables(list(self.userVars.keys()))

    def __getitem__(self, varName: str) -> Any:
        if isinstance(varName, tuple):
            if self.copyOnRetreive:
                itemList = []
                for name in list(varName):
                    if isinstance(self.__dict__[name], np.ndarray):
                        var = np.empty_like(self.__dict__[name])
                        var[:] = self.__dict__[name][:]
                        itemList.append(var)
                    else:
                        itemList.append(self.__dict__[name])
                return tuple(itemList)
            else:
                return tuple([self.__dict__[name] for name in list(varName)])
        else:
            if self.copyOnRetreive:
                var = np.empty_like(self.__dict__[varName])
                if isinstance(self.__dict__[varName], np.ndarray):
                    var[:] = self.__dict__[varName][:]
                    return var
                else:
                    return self.__dict__[varName]
            else:
                return self.__dict__[varName]

    # ----------------------------------------------------------------------------------------------#

    # --------------------------------Sending data to subprocess------------------------------------#
    def writeToProcess(self, input: str, wait: bool = True) -> int:
        """Enter a string, which will be send directly to MAD interactive mode, most users should use sendScript"""
        if input[len(input) - 2 :] != "\n":
            input += "\n"  # Prevent multiple lines
        if self.mad_is_running_scipt:
            self.runPipeContents()  # This implementation is terrible -> what if the user wnats to results returned?
            # Could the mad process write the the python mad class dictionary?
        self.process.stdin.write(
            (input + "\nwriteToPipe('finished\\n')\n").encode("utf-8")
        )
        self.process.stdin.flush()
        self.mad_is_running_scipt = True
        if wait:
            return self.runPipeContents()

    def sendScript(self, fileInput: str, wait: bool = True) -> int:
        """Enter a string, which will be send in a separate file for MAD to run"""
        os.ftruncate(self.__madScriptFd, 0)
        os.lseek(self.__madScriptFd, 0, os.SEEK_SET)
        if self.log:
            self.inputFile.write(fileInput)
        os.write(self.__madScriptFd, fileInput.encode("utf-8"))
        return self.writeToProcess(f'assert(loadfile("{self.__madScriptDir}"))()', wait)

    def eval(self, input: str, wait=True):
        if input[0] == "=":
            input = "_" + input
        self.writeToProcess(input, wait)
        if input[0] == "_":
            result = self.receiveVar("_")
            return result

    def MADXInput(self, input: str):
        return self.sendScript("MADX:open_env()\n" + input + "\nMADX:close_env()")

    # ----------------------------------------------------------------------------------------------#

    # -----------------------------------------MAD Commands-----------------------------------------#
    def readMADScalar(self, dType, valueList):
        """Directly run by MAD, never used by user"""
        return self.readMADMatrix(dType, [1, 1], valueList)[0][0]

    def getMADTable(self, name):  # Needs improvement!
        """Directly run by MAD, never used by user"""
        if name:
            return madObject(name, self)
        else:
            return madObject("MADTABLE", self)

    def readMADMatrix(self, DType, dims, valueList):
        """Directly run by MAD, never used by user"""
        return np.asarray(valueList, DType).reshape(dims)

    def readMADString(self, string):
        """Directly run by MAD, never used by user"""
        return string

    # ---------------------------------------------------------------------------------------------------#

    # ----------------------------------Sending variables across to MAD----------------------------------------#
    def sendVariables(
        self,
        varNames: list[str],
        vars: list[Union[np.ndarray, int, float, list]] = None,
    ):
        """Send variables to the MAD process, either send a list of varNames that already exist in the python MAD class or the varNames along with a list of the data"""
        if not vars:
            vars = list(self[tuple(varNames)])
        varTypes = []
        for i in range(len(vars)):
            if not isinstance(vars[i], np.ndarray):
                if isinstance(vars[i], (int, float)):
                    vars[i] = np.array([vars[i]], dtype=np.float64, ndmin=2)
                    varTypes.append("scalar")
                elif isinstance(vars[i], list):
                    vars[i] = np.array(vars[i], ndmin=2)
                    varTypes.append(vars[i].dtype)
                elif isinstance(vars[i], str):
                    vars[i] = np.array((vars[i]), ndmin=1)
                    varTypes.append(vars[i].dtype)
            else:
                vars[i] = np.atleast_2d(vars[i])
                varTypes.append(vars[i].dtype)

        # ---------------------Data size checks----------------------#
        totalDataSize = 0
        for i in range(len(vars)):
            totalDataSize += (vars[i].nbytes // self.__PAGE_SIZE + 1) * self.__PAGE_SIZE
            if totalDataSize + self.__PAGE_SIZE > self.RAM_LIMIT:
                raise (
                    OverflowError(
                        "Data size greater than ram limit, cannot send to mad"
                    )
                )  # Next step would be to send in chunks
        # -----------------------------------------------------------#
        fileInput = 'local readIMatrix, readMatrix, readCMatrix, readScalar, readString in require ("madl_buffer")\n'
        for i in range(len(vars)):
            if varTypes[i] == np.int32:
                functionToCall = "readIMatrix"
            elif varTypes[i] == np.int64:
                warnings.warn("64bit integers not supported by MAD, casting to float64")
                vars[i] = np.asarray(vars[i], dtype=np.float64)
                functionToCall = "readMatrix"
            elif varTypes[i] == np.float64:
                functionToCall = "readMatrix"
            elif varTypes[i] == np.complex128:
                functionToCall = "readCMatrix"
            elif varTypes[i] == "scalar":
                functionToCall = "readScalar"
            elif str(varTypes[i])[:2] == "<U":
                functionToCall = "readString"
            else:
                print("got var type", varTypes[i])
                raise (
                    NotImplementedError(
                        "received type:",
                        vars[i].dtype,
                        "Only int32, float64 and complex128 implemented",
                    )
                )
            fileInput += f"{varNames[i]} = {functionToCall}({self.__pyToLuaLst(vars[i].shape)}, {self.__pyToLuaLst(vars[i])})\n"  # Process return
        self.sendScript(fileInput)

    def sendVar(self, varName: str, var: Union[np.ndarray, int, float, list] = None):
        """Send a variable to the MAD process, either send a varName that already exists in the python MAD class or a varName along with data"""
        if var is not None:
            self.sendVariables([varName], [var])
        else:
            self.sendVariables([varName])

    def sendall(self):
        """Send all the variables that currently exist in the MAD dictionary, will overwrite variables in the MAD environment, use with caution"""
        self.sendVariables(list(self.userVars.keys()))

    # -------------------------------------------------------------------------------------------------------------#

    # -----------------------------------Receiving variables from to MAD-------------------------------------------#
    def readPipe(self):
        """Read up to 8.912 MB from the pipe and return the result"""
        if self.pollIn.poll(120000) == []:  # 2 Minute poll!
            warnings.warn(
                "Either no data in PIPE or PIPE between MAD and python unavailable, may cause errors elsewhere"
            )
        else:
            return os.read(self.pipe, 8192).decode("utf-8").replace("\x00", "")

    # Read all types of contents
    def runCommands(self, commands: str):
        evaluatedList = []
        for i in range(len(commands)):
            if self.execCheck.match(commands[i]):
                evaluatedValue = exec(
                    commands[i],
                    self.globalVars,
                    {"self": self},
                )  # Always returns None
            else:
                evaluatedValue = eval(
                    commands[i],
                    self.globalVars,
                    {"self": self},
                )
            if isinstance(evaluatedValue, tuple):
                evaluatedList += evaluatedValue
            else:
                evaluatedList.append(evaluatedValue)
        return evaluatedList

    def readScript(self):
        with open(self.__pyScriptDir, "r") as file:
            return tuple(self.runCommands(file.read().split("\n")[:-1]))

    def runPipeContents(self):
        status = None
        while not status:
            self.pipeRead += self.readPipe()
            matchedString = self.pipeMatch.match(self.pipeRead)
            status = matchedString.group("status")
            self.pipeRead = self.pipeRead[matchedString.end("status") + 1 :]
        if status == "finished":
            self.mad_is_running_scipt = False
        if matchedString.group("commands") is not None:
            commands = matchedString.group("commands").split("pyCommand:")[1:]
            evaluatedList = self.runCommands(commands)
        return evaluatedList

    def receiveVariables(self, varNameList: list[str], is_table: bool = False) -> Any:
        """Given a list of variable names, receive the variables from the MAD process, and save into the MAD dictionary"""
        # Split the reading to only 20 variables are read at once, significantly improves performance:
        self.sendScript(
            f"""
        local offset = sharedata({self.__pyToLuaLst(varNameList).replace("'", "")}, {self.__pyToLuaLst(varNameList)}, {self.__getAsMADString(is_table)})                  --This mmaps to shared memory
            """
        )
        return self[tuple(varNameList)]

    def receiveVar(self, var: str) -> Any:
        """Recieve a single variable from the MAD process"""
        return self.receiveVariables([var])[0]

    def updateVariables(self):
        """Update all the variables that currently exist in the MAD dictionary from MAD"""
        keyList = list(self.userVars.keys())
        recievedVars = self.receiveVariables(keyList)
        if len(keyList) > 1:
            for i in range(len(keyList)):
                self.__dict__[keyList[i]] = recievedVars[i]
        else:
            self.__dict__[keyList[0]] = recievedVars

    # -------------------------------------------------------------------------------------------------------------#

    # ----------------------------------Calling functions(WIP)-----------------------------------------------------#
    # Should result name be provided? ALSO NOT TESTED -->
    def callFunc(self, resultName: Union[str, list[str]], funcName: str, *args):
        """Call the function funcName and store the result in resultName, then retreive the result into the MAD dictionary"""
        if isinstance(resultName, list):
            resultName = self.__pyToLuaLst(resultName)
        if resultName:
            stringStart = f"{self.__getAsMADString(resultName)} = "
        else:
            stringStart = ""
        self.sendScript(
            stringStart
            + f"""{self.__getAsMADString(funcName)}({self.__getArgsAsString(*args)})\n"""
        )
        if resultName:
            return self.receiveVar(resultName)

    def callMethod(
        self, resultName: Union[str, list[str]], varName: str, methName: str, *args
    ):
        """Call the method methName of the variable varName and store the result in resultName, then retreive the result into the MAD dictionary"""
        if isinstance(resultName, list):
            stringStart = f"{self.__getAsMADString(resultName)} = "
        elif resultName:
            stringStart = f"{self.__getAsMADString(resultName)} = "
            resultName = [resultName]
        else:
            stringStart = ""
        self.sendScript(
            stringStart
            + f"""{self.__getAsMADString(varName)}:{self.__getAsMADString(methName)}({self.__getArgsAsString(*args)})\n"""
        )
        if resultName:
            return self.receiveVariables(resultName)

    # -------------------------------------------------------------------------------------------------------------#

    # ------------------------------------------Stored Data Manipulation-------------------------------------------#
    def convertMmapToData(self):
        """Convert the memory mappings in the MAD dictionary into data in the python environment"""
        for key in self.userVars.keys():
            if isinstance(self.__dict__[key], np.ndarray):
                newArray = np.empty_like(self.__dict__[key])
                newArray[:] = self.__dict__[key][:]
                self.__dict__[key] = newArray

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
            itemString = self.__getAsMADString(item)
            kwargsString += keyString + " = " + itemString + ", "
        return kwargsString + "}"

    def __getArgsAsString(self, *args):
        argStr = ""
        for arg in args:
            argStr += self.__getAsMADString(arg) + ", "
        return argStr[:-2]  # Assumes args is always put last

    def __getAsMADString(self, var: Any, convertString=False):
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
            luaString += self.__getAsMADString(item, True) + ", "
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
        result = self.__getAsMADString(varName) + " = \\"
        if arguments:
            for arg in arguments:
                result += self.__getAsMADString(arg) + ","
            result = result[:-1]
        return result + " -> " + expression

    # ---------------------------------------------------------------------------------------------------#

    # -------------------------------Setup MAD Classes---------------------------------------------------#
    def setupClass(
        self,
        className: str,
        moduleName: str,
        resultName: Union[str, list[str]],
        *args,
        **kwargs,
    ):
        """Create a class 'className' from the module 'modulaName' and store into the variable 'varName'
        the kwargs are used to as extra keyword arguments within MAD"""
        if isinstance(resultName, list):
            self.sendScript(
                f"""
    {self.__pyToLuaLst(resultName)[1:-3].replace("'", "")} = {className} {{ {self.__getKwargAsString(**kwargs)[1:-1]} {self.__getArgsAsString(*args)} }}
                """
            )
            self.receiveVariables(resultName)  # Make this optional, or not do it

        else:
            self.sendScript(
                f"""
    {resultName} = {className} '{resultName}' {{ {self.__getKwargAsString(**kwargs)[1:-1]} {self.__getArgsAsString(*args)} }} 
                """
            )
            if moduleName == "MAD.element":
                self[resultName] = madElement(resultName, self)
                returnElm = (
                    lambda _, **kwargs: f"""{resultName} {self.__getKwargAsString(**kwargs)}"""
                )
                setattr(
                    self[resultName], "set", MethodType(returnElm, self[resultName])
                )
            else:
                self[resultName] = madObject(resultName, self)

    def defExpr(self, **kwargs):
        """Create a deffered expression object where the kwargs are used as the deffered expressions, specified using strings"""
        return (
            self.__getKwargAsString(**kwargs).replace("=", ":=").replace("'", "")[1:-3]
        )  # Change := to equals, remove string identifers, and remove ", "

    def deferred(self, varName: str, **kwargs):
        """Create a deffered expression object with the name "varName" where the kwargs are used as the deffered expressions, specified using strings"""
        self.sendScript(
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
        self.sendScript(
            f"""
            MADX:load("{seqFilename}", "{targetFile}")
            {seqName} = MADX.seq
            """
        )
        self.__dict__[seqName] = madObject(seqName, self)

    # ---------------------------------------------------------------------------------------------------#
    def close(self):
        # After calling this, the variables within MAD are still accessible but communication has ended
        """Close the shared memory, MAD process"""
        self.convertMmapToData()
        self.userVars.clear()
        if self.process:
            self.process.terminate()  # ctrl-c (stops mad)
            self.process.wait()
        os.unlink(self.__madScriptDir)
        os.unlink(self.__pyScriptDir)
        os.unlink(self.pipeDir)
        os.rmdir(self.__tmpFldr)

    def __del__(self):  # Should not be relied on
        if os.path.exists(self.pipeDir):
            os.unlink(self.pipeDir)
        if os.path.exists(self.__madScriptDir):
            os.unlink(self.__madScriptDir)
        if os.path.exists(self.__pyScriptDir):
            os.unlink(self.__pyScriptDir)
        if os.path.exists(self.__tmpFldr):
            os.rmdir(self.__tmpFldr)
        if self.process:
            self.process.terminate()
            self.process.wait()

    # -------------------------------For use with the "with" statement-----------------------------------#
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.close()

    # ---------------------------------------------------------------------------------------------------#
