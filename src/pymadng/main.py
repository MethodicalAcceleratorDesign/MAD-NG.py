import os, mmap, tempfile, warnings, sys, select, time, re, subprocess

# os is used for directorys
# mmap is for memory mapping
# tempfile is for temporarily creating files

import numpy as np  # For arrays  (Works well with multiprocessing and mmap)
from resource import getpagesize  # To get page size
from multiprocessing import shared_memory  # For shared memory
from typing import Any, Union  # To make stuff look nicer
from types import MethodType  # Used to attach functions to the class

# Custom Classes:
from .pymadClasses import madObject, madElement, deferred

# TODO: implement yield into MAD
# TODO: Allow looping through objects
# TODO: create a metaclass that allows for variables to be created using MAD.x and automatically sent over
# TODO: don't pollute MAD environment, place into MAD's MADX environment
# TODO: Have error if when importing, thing isn't found
# TODO: Improve method syntax
# TODO: Have every string send to mad go through the same converter - prevent duplication
# TODO: Make it so that MAD does the loop for variables not python (speed)
# TODO: Make args and kwargs not have different methods of string interpolation
# TODO: Improve error catching
# TODO: Lamdba and kwargs is a botched fix, not a fan of it
# TODO: Recursive dot indexing
# TODO: Improve declaration of where MAD is and usage of mad name
# TODO: Remove return from call func and call method, allow return / multiple return directly out of the function (Will hugely simplify current functions)
# TODO: Make runPipeContents aware of object or not


class MAD:  # Review private and public
    __pagesWritten = 0
    __PAGE_SIZE = getpagesize()  # To allow to work on multiple different machines
    userVars = {}

    def __init__(
        self,
        srcdir: str,
        log: bool = False,
        ram_limit: int = 1024e6,
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
        self.shm = shared_memory.SharedMemory(create=True, size=int(ram_limit))
        self.RAM_LIMIT = int(ram_limit)
        self.openFile = open("/dev/shm/" + self.shm.name, mode="r+")
        self.mmap = mmap.mmap(
            self.openFile.fileno(), length=0, flags=mmap.MAP_SHARED, prot=mmap.PROT_READ
        )
        self.copyOnRetreive = copyOnRetreive
        self.__scriptFd, self.__scriptDir = tempfile.mkstemp()
        if srcdir[-1] != "/":
            srcdir += "/"
        self.SRC_DIR = srcdir  # Must be run in directory where mad executable or a sub folder called pyMAD  ##Have this can be changed on install?
        # Path to mad executable -- this line will be changed to be more flexible
        self.PATH_TO_MAD = srcdir + "mad"
        self.globalVars = {"np": np}
        self.pipeDir = srcdir + self.__scriptDir.split("/")[2].replace("tmp", "pipe")

        # Setup communication pipe
        os.mkfifo(self.pipeDir) 

        # Create initial file when MAD process is created
        INITIALISE_SCRIPT = f"""
        sharedata, sharetable, readSharedMemory, openSharedMemory, close, writeToPipe = require ("madl_mmap").sharedata, require ("madl_mmap").sharetable, require ("madl_mmap").readSharedMemory, require ("madl_mmap").openSharedMemory, require ("madl_mmap").close, require ("madl_mmap").writeToPipe\n
        local openPipe in require("madl_mmap")
        openPipe("{self.pipeDir}")
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
            self.process.wait(0.01)
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
            # self.outputFile = open(srcdir + "outLog.txt", "w")
            self.inputFile = open(srcdir + "inLog.txt", "w")
            self.process.logfile_send = self.inputFile
            # self.process.logfile_read = self.outputFile
            # ---------------------------------------#
        self.log = log
        self.process.logfile_read = sys.stdout
        self.process.delaybeforesend = None  # Makes slightly faster

        # Wait for mad to be ready for input
        self.sendScript(INITIALISE_SCRIPT, False)

        # Now read from pipe as write end is open
        self.pipe = os.open(self.pipeDir, os.O_RDONLY)
        self.pollIn = select.poll()
        self.pollIn.register(self.pipe, select.POLLIN)
        self.pipeMatch = re.compile(r"(?P<instruction>pyInstruction:.*\n)*(?P<commands>(pyCommand:.*\n)*)\n*(?P<status>continue|finished)?")

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
            self.userVars[nameList[i]] = None  #####Double check if this is necessary

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
        self.process.stdin.write((input).encode("utf-8"))
        self.process.stdin.flush()
        if wait:
            return self.runPipeContents()

    def sendScript(self, fileInput: str, wait: bool = True) -> int:
        """Enter a string, which will be send in a separate file for MAD to run"""
        os.ftruncate(self.__scriptFd, 0)
        os.lseek(self.__scriptFd, 0, os.SEEK_SET)
        if wait:
            fileInput += "\nwriteToPipe('finished\\n')\n"
        if self.log:
            self.inputFile.write(fileInput)
        os.write(self.__scriptFd, fileInput.encode("utf-8"))
        return self.writeToProcess(f'assert(loadfile("{self.__scriptDir}"))()', wait)

    def eval(self, input: str):
        if input[0] == "=":
            input = "_" + input
        self.writeToProcess(input + "\n", False)
        if input[0] == "_":
            result = self.receiveVar("_")
            del self.userVars["_"]
            del self.__dict__["_"]
            return result

    # def input(self, input: str): #Same as sendScript
    #     self.writeToProcess("do " + input + " end")

    # ----------------------------------------------------------------------------------------------#

    # -----------------------------------------Shared Memory----------------------------------------#
    def writeToSharedMemory(self, data: np.ndarray) -> None:
        """Enter a numpy array which will be entered into shared memory, if not send to MAD process, synchronisation problems will occur"""
        pagesUpTo = []
        for i in range(len(data)):
            offset = self.__PAGE_SIZE * self.__pagesWritten
            sharedArray = np.ndarray(
                data[i].shape, dtype=data[i].dtype, buffer=self.shm.buf[offset:]
            )
            sharedArray[:] = data[i][:]
            pagesUpTo.append(self.__pagesWritten)
            self.__pagesWritten = (offset + data[i].nbytes) // self.__PAGE_SIZE + 1
        return pagesUpTo

    def __chkPage(self, pageUpTo: int) -> None:
        if self.__pagesWritten != pageUpTo:
            self.__pagesWritten = pageUpTo
            print("WARNING SHARED MEMORY MISALLIGNED, PLEASE REPORT")

    def readMADScalar(self, dType, pageUpTo):
        """Directly run by MAD, never used by user"""
        return self.readMADMatrix(dType, [1, 1], pageUpTo)[0][0]

    def getMADTable(self, pageUpTo):  # Needs improvement!
        """Directly run by MAD, never used by user"""
        self.__chkPage(pageUpTo)
        self.__pagesWritten += 1
        return madObject("MADTABLE" + str(self.__pagesWritten), self)

    def readMADMatrix(self, dType, dims, pageUpTo):
        """Directly run by MAD, never used by user"""
        self.__chkPage(pageUpTo)
        # Below line does not work on windows - the windows version uses access = ... rather than flags and prot
        self.mmap = mmap.mmap(
            self.openFile.fileno(), length=0, flags=mmap.MAP_SHARED
        )  # prot=mmap.PROT_READ)
        result = np.frombuffer(
            dtype=dType,
            buffer=self.mmap,
            count=dims[0] * dims[1],
            offset=self.__pagesWritten * self.__PAGE_SIZE,
        ).reshape(dims)
        self.__pagesWritten += result.nbytes // self.__PAGE_SIZE + 1
        return result

    def readMADString(self, dims, pageUpTo):
        """Directly run by MAD, never used by user"""
        self.__chkPage(pageUpTo)
        self.mmap = mmap.mmap(
            self.openFile.fileno(), length=0, flags=mmap.MAP_SHARED
        )  # prot=mmap.PROT_READ)
        decodedData = np.ndarray(
            dims,
            dtype=np.int32,
            buffer=self.mmap,
            offset=self.__pagesWritten * self.__PAGE_SIZE,
        )
        decodedString = ""
        stringMatrix = np.resize(decodedData, dims)
        for val in stringMatrix[0]:
            decodedString = decodedString + chr(val)  # Convert back to string

        self.__pagesWritten += decodedData.nbytes // self.__PAGE_SIZE + 1
        return decodedString

    def readMADTable(self, tableLength) -> list:  # Not doing named tables yet
        """Reads a table from MAD and returns a list"""
        return f"TABLE|STARTS|HERE|{tableLength}"

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
            else:
                vars[i] = np.atleast_2d(vars[i])
                varTypes.append(vars[i].dtype)

        # ---------------------Adaptive file size--------------------# (Currently not used, file is opened at max memory size)
        totalDataSize = self.__PAGE_SIZE * self.__pagesWritten
        varList = []
        varTypesList = []
        initIndex = 0
        for i in range(len(vars)):
            totalDataSize += (vars[i].nbytes // self.__PAGE_SIZE + 1) * self.__PAGE_SIZE
            if totalDataSize * 1.1 > self.RAM_LIMIT:
                if i == initIndex:
                    raise (
                        OverflowError(
                            "Data size greater than ram limit, cannot send to mad"
                        )
                    )  # Next step would be to send in chunks
                varList.append(vars[initIndex:i])
                varTypesList.append(varTypes[initIndex:i])
                totalDataSize = (
                    vars[i].nbytes // self.__PAGE_SIZE + 1
                ) * self.__PAGE_SIZE
                initIndex = i
        varList.append(vars[initIndex:])
        varTypesList.append(varTypes[initIndex:])
        # -----------------------------------------------------------#
        for i in range(len(varList)):
            pagesUpTo = self.writeToSharedMemory(varList[i])
            fileInput = 'local readIMatrix, readMatrix, readCMatrix, readScalar in require ("madl_mmap")\n'
            fileInput += f'openSharedMemory("{self.shm.name}")\n'
            for j in range(len(varList[i])):
                if varTypesList[i][j] == np.int32:
                    functionToCall = "readIMatrix"
                elif varTypesList[i][j] == np.int64:
                    warnings.warn(
                        "64bit integers not supported by MAD, casting to float64"
                    )
                    varList[i][j] = np.asarray(varList[i][j], dtype=np.float64)
                    functionToCall = "readMatrix"
                elif varTypesList[i][j] == np.float64:
                    functionToCall = "readMatrix"
                elif varTypesList[i][j] == np.complex128:
                    functionToCall = "readCMatrix"
                elif varTypesList[i][j] == "scalar":
                    functionToCall = "readScalar"
                else:
                    print(varTypesList[i][j])
                    raise (
                        NotImplementedError(
                            "received type:",
                            varList.dtype,
                            "Only int32, float64 and complex128 implemented",
                        )
                    )
                fileInput += f"{varNames[j]} = {functionToCall}({self.__pyToLuaLst(varList[i][j].shape)}, {pagesUpTo[j]})\n"  # Process return
                # self.output.write(f'{varNames[j]} = {functionToCall}({self.__pyToLuaLst(varList[i][j].shape)})\n') #Process return (debug)
            fileInput += f"close()\n"
            self.sendScript(fileInput)
            if len(varList) > 1 and i < len(varList) - 1:
                self.resetShmSafely()  # Split into several because too much data, so memory needs cleaning every time (does it?)

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
            return os.read(self.pipe, 8912).decode("utf-8").replace("\x00", "")

    #Read all types of contents
    def runPipeContents(self): 
        status, pipeRead = "start", ""
        instruction = None
        self.evaluatedList = []
        while status != "finished":
            pipeRead += self.readPipe()
            instructionSet = re.match(self.pipeMatch,pipeRead)
            status = instructionSet.group("status")
            instruction = instruction or instructionSet.group("instruction") #In case of continue
            if status == "finished" or status == "continue":
                if instructionSet.group("commands") is not None:
                    commands = instructionSet.group("commands").split("pyCommand:")[1:]
                    tableStart, tableLength = 0, 0
                    for i in range(len(commands)):
                        evaluatedValue = eval(
                            commands[i],
                            self.globalVars,
                            {"self": self},
                        )
                        if (
                            isinstance(evaluatedValue, str)
                            and evaluatedValue[:17] == "TABLE|STARTS|HERE"
                        ):
                            tableLength, tableStart = int(evaluatedValue[18:]), i
                            self.evaluatedList.append([])
                        elif tableLength > 0 and i <= tableStart + tableLength:
                            self.evaluatedList[-1].append(evaluatedValue)
                        else:
                            self.evaluatedList.append(evaluatedValue)
                            tableStart, tableLength = 0, 0
            if status == "continue":
                self.evaluatedList.pop()
                pipeRead = ""
        if instruction == "pyInstruction:Save\n":
            return self.evaluatedList

    def receiveVariables(self, varNameList: list[str], shareType="data") -> Any:
        """Given a list of variable names, receive the variables from the MAD process, and save into the MAD dictionary"""
        numVars = len(varNameList)
        y = min(numVars, 20)
        # Split the reading to only 20 variables are read at once, significantly improves performance:
        for x in range(0, numVars, 20):
            self.__varNameList = varNameList[x:y]
            madReturn = self.sendScript(
                f"""
            openSharedMemory("{self.shm.name}", true)
            local offset = share{shareType}({self.__pyToLuaLst(varNameList[x:y]).replace("'", "")})                  --This mmaps to shared memory
            close()
                """
            )
            for i in range(len(madReturn)):
                if isinstance(madReturn[i], madObject):
                    madReturn[i + x].__name__ = self.__varNameList[i + x]
                self[varNameList[i + x]] = madReturn[i + x]
            y += min(20, numVars - y)
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
            resultName = self.__pyToLuaLst(resultName)
        if resultName:
            stringStart = f"{self.__getAsMADString(resultName)} = "
        else:
            stringStart = ""
        self.sendScript(
            stringStart
            + f"""{self.__getAsMADString(varName)}:{self.__getAsMADString(methName)}({self.__getArgsAsString(*args)})\n"""
        )
        if resultName:
            return self.receiveVar(resultName)

    # -------------------------------------------------------------------------------------------------------------#

    # ------------------------------------------Stored Data Manipulation-------------------------------------------#
    def convertMmapToData(self):
        """Convert the memory mappings in the MAD dictionary into data in the python environment"""
        for key in self.userVars.keys():
            if isinstance(self.__dict__[key], np.ndarray):
                newArray = np.empty_like(self.__dict__[key])
                newArray[:] = self.__dict__[key][:]
                self.__dict__[key] = newArray

    def resetShmSafely(self, resetMAD: bool = True):
        """Reset the shared memory safely, i.e. no data is lost on reset"""
        self.convertMmapToData()
        for i in range(len(self.evaluatedList)):
            if isinstance(self.evaluatedList[i], np.ndarray):
                newArray = np.empty_like(self.evaluatedList[i])
                newArray[:] = self.evaluatedList[i][:]
                self.evaluatedList[i] = newArray
        fildes = os.open("/dev/shm/" + self.shm.name, os.O_RDWR)
        os.ftruncate(fildes, 0)
        os.ftruncate(fildes, self.RAM_LIMIT)
        self.__pagesWritten = 0
        self.shm = shared_memory.SharedMemory(
            name=self.shm.name, create=False, size=self.RAM_LIMIT
        )
        if resetMAD:
            self.sendScript('safelyCloseMemory = require ("madl_mmap").safelyCloseMemory\nsafelyCloseMemory()')
        else:
            self.writeToProcess("continue\n", False)

    # ---------------------------------------------------------------------------------------------------#

    # -------------------------------String Conversions--------------------------------------------------#
    def __getKwargAsString(
        self, **kwargs
    ):  # Keep an eye out for failures when kwargs is empty, shouldn't occur in current setup
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
        if not var:
            return "nil"
        elif isinstance(var, str) and convertString:
            return "'" + var + "'"
        elif isinstance(var, list):
            return self.__pyToLuaLst(var)
        elif isinstance(var, (madObject, madElement)):
            return var.__name__
        elif isinstance(var, dict):
            return self.__getKwargAsString(**var)
        elif callable(var):
            return var.__name__
        else:
            return str(var).replace("False", "false").replace("True", "true")

    def __pyToLuaLst(self, lst: list[Any], split=False) -> str:
        """Convert a python list to a lua list in a string, used when sending information to MAD, should not need to be accessed by user"""
        luaString = "{"
        for item in lst:
            luaString += self.__getAsMADString(item, True) + ", "
        # #-------Resolves character limit in interactive mode-----------#
        # for x in range(len(newList) // 125):
        #     idx = newList.find(",", 125*x, 125*(x+1))
        #     while idx <  125*(x+1) and idx > 0:
        #         newIdx = idx + 1
        #         idx =  newList.find(",", idx + 1, 125*(x+1))
        #     newList = newList[:newIdx] + "\n" + newList[newIdx:]
        # #---------------------------------------------------------------#
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

    def MADLambda(self, varName, arguments: list[str], expression: str):
        return (
            self.__getAsMADString(varName)
            + " = \\"
            + self.__getArgsAsString(tuple(arguments))[1:-1].replace("'", "")
            + " -> "
            + expression
        )

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
            else:
                self[resultName] = madObject(resultName, self)

    def deferedExpr(self, **kwargs):
        """Create a deffered expression object where the kwargs are used as the deffered expressions, specified using strings"""
        return (
            self.__getKwargAsString(**kwargs).replace("=", ":=").replace("'", "")[1:-3]
        )  # Change := to equals, remove string identifers, and remove ", "

    def deferred(self, varName: str, **kwargs):
        """Create a deffered expression object with the name "varName" where the kwargs are used as the deffered expressions, specified using strings"""
        self.sendScript(
            f"""
            local deferred in MAD.typeid
            {varName} = deferred {{{self.deferedExpr(**kwargs)}}}
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
        self.shm.close()  # Closes the shared memory, needs to be done before unlinked
        self.shm.unlink()  # Deletes the shared memory (prevents memory leaks)
        if self.process:
            self.process.terminate()  # ctrl-c (stops mad)
            self.process.wait()
        self.openFile.close()
        os.unlink(self.__scriptDir)
        os.unlink(self.pipeDir)

    def __del__(self):  # Should not be relied on
        if self.shm.buf:
            self.shm.close()  # Closes the shared memory, needs to be done before unlinked
            self.shm.unlink()  # Deletes the shared memory (prevents memory leaks)
        if os.path.exists(self.pipeDir):
            os.unlink(self.pipeDir)  # Have in the __del__
        if os.path.exists(self.__scriptDir):
            os.unlink(self.__scriptDir)  # Have in the __del__
        if self.process:
            self.process.terminate()  # ctrl-c (stops mad)
            self.process.wait()

    # -------------------------------For use with the "with" statement-----------------------------------#
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        print()
        self.close()

    # ---------------------------------------------------------------------------------------------------#
