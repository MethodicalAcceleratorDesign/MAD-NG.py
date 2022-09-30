import os, mmap, pexpect, tempfile
#os is used for directorys
#mmap is for memory mapping
#pexpect is for communication with the mad executable
#tempfile is for temporarily creating files 

import sys, time #debugging 
import numpy as np #For arrays  (Works well with multiprocessing and mmap)
from resource import getpagesize #To get page size
from multiprocessing import shared_memory #For shared memory
from typing import Any, Union #To make stuff look nicer
from types import MethodType #Used to attach functions to the class

#Custom Classes:
from pymadngClasses import madObject, madElement, deferred

#TODO: implement yield into MAD
#TODO: Allow looping through objects
#TODO: create a metaclass that allows for variables to be created using MAD.x and automatically sent over
#TODO: don't pollute MAD environment, place into MAD's MADX environment
#TODO: Have error if when importing, thing isn't found
#TODO: Improve method syntax
#TODO: Have every string send to mad go through the same converter - prevent duplication
#TODO: Make it so that you ask MAD for the variable, so it doesn't output EVERY VARIABLE
#TODO: Make args and kwargs not have different methods of string interpolation
#TODO: Improve error catching
#TODO: Change name to __name__ in class?
#TODO: Lamdba and kwargs is a botched fix, not a fan of it
#TODO: Recursive dot indexing
#TODO: Improve declaration of where MAD is and usage of mad name


class MAD(): #Review private and public

    __pagesWritten = 0
    __PAGE_SIZE = getpagesize()  #To allow to work on multiple different machines
    __possibleProcessReturn = [pexpect.EOF, pexpect.TIMEOUT, r"stdin.*\r\n> $", r"SIGSEGV: segmentation fault!.*", r"/tmp/tmp.*stdin:1: in main chunk", r"> $"] #Use this list to cope with errors    
    userVars = {}
    __madReturn = []

    def __init__(self, srcdir: str, log: bool = False, ram_limit: int = 1024e6, copyOnRetreive: bool = True) -> None:
        """Initialise MAD Object. 
        Optional Arguments:
        srcdir (str): If not running this python program in MAD/src/pymad, enter the SRC directory
        log (bool): True means the sending and receiving data is logged
        ram_limit (int): How much ram memory you would like to limit the program to using.
        copyOnRetrieve (bool): When True, the variables are copied from the memory mapping when assigned to a variable outside MAD. When False, you receive a memory mapped numpy array that if transferred outside the MAD class, will have to be manually dealt with
        """
        #Init shared memory related variables
        self.shm = shared_memory.SharedMemory(create=True, size=int(ram_limit)) #Probs don't want all that memory taken up
        self.RAM_LIMIT = int(ram_limit)
        self.openFile = open("/dev/shm/" + self.shm.name, mode="r+")
        self.mmap = mmap.mmap(self.openFile.fileno(), length=0, flags=mmap.MAP_SHARED, prot=mmap.PROT_READ)
        self.copyOnRetreive = copyOnRetreive

        #All variable names will be changed as soon as I can think of better names
        if srcdir[-1] != "/": srcdir += "/"
        self.SRC_DIR = srcdir              #Must be run in directory where mad executable or a sub folder called pyMAD  ##Have this can be changed on install?
        self.PATH_TO_MAD = srcdir + "mad" #Path to mad executable                         ##This line will be changed to be more flexible
        self.globalVars = {"np":np}
        
        #Create initial file when MAD process is created
        INITIALISE_SCRIPT = """
        sharedata, readSharedMemory, openSharedMemory, closeSharedMemory = require ("madl_mmap").sharedata, require ("madl_mmap").readSharedMemory, require ("madl_mmap").openSharedMemory, require ("madl_mmap").closeSharedMemory\n
        """

        #Init the process
        self.process = pexpect.spawn(self.PATH_TO_MAD, ["-q"], encoding="utf-8", timeout=120) #2 Minute timeout
        if log:
            #----------Optional Logging-------------#
            # self.output = sys.stdout #Debugging
            self.output = open(srcdir + "outLog.txt", "w")
            self.input = open(srcdir + "inLog.txt", "w")
            self.process.logfile_send = self.input
            self.process.logfile_read = self.output
            #---------------------------------------#
        self.log = log

        self.process.delaybeforesend = None #Makes slightly faster
        MADReturn = self.process.expect(self.__possibleProcessReturn) #waits for mad to be ready for input
        # self.__possibleProcessReturn.pop()
        if MADReturn == 5: #or MADReturn == 6:
            MADReturn = self.sendScript(INITIALISE_SCRIPT) #waits for mad to be ready for input
            if MADReturn != 5: raise(RuntimeError("MAD process failed", self.process.match.group(0)))
        else: raise(RuntimeError("MAD process failed", self.process.match.group(0)))

        #--------------------------------Retrieve the modules of MAD-------------------------------#
        modulesToImport = ["MAD", "elements", "sequence", "mtable", "twiss", "beta0", "beam", "survey", "object", "track", "match"] #Limits the ~80 modules
        self.importClasses("MAD", modulesToImport)
        self.importClasses("MAD.element")
        self.importVariables("MAD", "MADX")
        #------------------------------------------------------------------------------------------#

    def retrieveMADClasses(self, moduleName: str): #Currently can only do classes, unable to separate functions
        """Retrieve the classes in MAD from the module "moduleName", while only importing the classes in the list "classesToImport".
        If no list is provided, it is assumed that you would like to import every class"""
        self.__possibleProcessReturn.append(r"Modules:\r\n(?P<names>.*)\r\n> $")
        madReturn = self.sendScript(f"""
        local tostring = tostring
        function getModName(modname, mod)
            io.write(modname .. "|" .. tostring(mod) .. ";")
        end
        io.write("Modules:\\n")
        for modname, mod in pairs({moduleName}) do pcall(getModName, modname, mod) end io.write("\\n")""")
        self.__possibleProcessReturn.pop()
        return self.process.match.group(0).strip("Modules:\r\n").split(";")[:-1] #Ignore \r\n
    
    def importClasses(self, moduleName: str,classesToImport: list[str] = []): #CLEAN UP THIS FUNCTION
        for madClass in self.retrieveMADClasses(moduleName):
            varName = madClass.split("|")[0]
            varType = madClass.split("|")[1]
            if "function" not in varType and (classesToImport == [] or varName in classesToImport): ##If statements can be improved
                exec(f"""def {varName}(self, varName, *args, **kwargs): 
                self.setupClass("{varName}", "{moduleName}", varName, *args, **kwargs) """) #Create a function on the fly
                setattr(self, varName, MethodType(locals()[varName], self)) #Bind the function to the mad class
                if varName != "MADX": self.sendScript(f"{varName} = {moduleName}.{varName}")
            
            elif "function" in varType and (classesToImport == [] or varName in classesToImport): #WIP - NOT TESTED
                exec(f"""def {varName}(self, resultName, *args): 
                self.callFunc(resultName, "{varName}", *args) """) #Create a function on the fly
                setattr(self, varName, MethodType(locals()[varName], self)) #Bind the function to the mad class
                self.sendScript(f"{varName} = {moduleName}.{varName}")

    def importVariables(self, moduleName: str, varsToImport: list[str] = []):
        for madClass in self.retrieveMADClasses(moduleName):
            varName = madClass.split("|")[0]
            varType = madClass.split("|")[1]
            # if moduleName ==  "elements" and varName in varsToImport:
            #     self[varName] = madElement(varName, self)
            #     self.sendScript(f"{varName} in {moduleName}")
            if varName in varsToImport and "function" in varType: #Functionise this ?
                exec(f"""def {varName}(self, resultName, *args): 
                self.callFunc(resultName, "{varName}", *args) """) #Create a function on the fly
                setattr(self, varName, MethodType(locals()[varName], self)) #Bind the function to the mad class
                self.sendScript(f"{varName} = {moduleName}.{varName}")
                
            elif varName in varsToImport:
                self.__dict__[varName] = madObject(varName, self) 
                if varName != "MADX": self.sendScript(f"{varName} = {moduleName}.{varName}")

    #-----------------------------Make the class work like a dictionary----------------------------#
    def __setitem__(self, varName: str, var: Any) -> None:
        if isinstance(varName, tuple):
            nameList = list(varName)
            varList = list(var)
            if len(varList) != len(nameList): raise ValueError("Incorrect number of values to unpack, received", len(varList), "variables and", len(nameList), "keys")
        else: 
            nameList = [varName]
            varList = [var]
        for i in range(len(nameList)):
            if type(varList[i]) == list:
                varList[i] = np.array(varList[i]) #So the user isn't forced to initialise the array as numpy
            self.__dict__[nameList[i]] = varList[i]
            self.userVars[nameList[i]] = None #####Double check if this is necessary

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
    #----------------------------------------------------------------------------------------------#
    
    # def __dict__(self):
    #     return self.vars

    # def __del__(self):
        # self.mmap.close() #N
    #--------------------------------Sending data to subprocess------------------------------------#
    def writeToProcess(self, input: str, expect: bool = True) -> int:
        """Enter a string, which will be send directly to MAD interactive mode 
        returns: index of __possibleProcessReturn indicating the return from MAD"""
        self.process.write(input + "\n")
        if expect: return self.process.expect(self.__possibleProcessReturn) #waits for mad to be ready for input/completed last input
    
    def sendScript(self, fileInput: str, expect: bool = True) -> int:
        """Enter a string, which will be send in a separate file for MAD to run
        returns: index of __possibleProcessReturn indicating the return from MAD"""
        scriptFd, scriptDir = tempfile.mkstemp()
        os.write(scriptFd, fileInput.encode("utf-8"))
        MADReturn = self.writeToProcess(f'assert(loadfile("{scriptDir}"))()', expect)
        os.close(scriptFd)
        if self.log: self.input.write(fileInput) 
        return MADReturn

    def eval(self, input: str):
        if "=" not in input:
            input = "qwtscvbn = " + input
        var = input.split("=")[0].strip(" ")
        if self.writeToProcess(input) != 5: raise(RuntimeError("MAD process failed", self.process.match.group(0)))
        result = self.receiveVar(var)
        if var == "qwtscvbn":
            del self.userVars["qwtscvbn"]
            del self.__dict__["qwtscvbn"]
        return result
    #----------------------------------------------------------------------------------------------#

    #-----------------------------------------Shared Memory----------------------------------------#
    def writeToSharedMemory(self, data: np.ndarray) -> None:
        """Enter a numpy array which will be entered into shared memory, if not send to MAD process, synchronisation problems will occur"""
        for i in range(len(data)):
            offset = self.__PAGE_SIZE * self.__pagesWritten
            sharedArray = np.ndarray(data[i].shape, dtype=data[i].dtype, buffer=self.shm.buf[offset:])
            sharedArray[:] = data[i][:]
            self.__pagesWritten = (offset + data[i].nbytes) // self.__PAGE_SIZE + 1
    
    def readMADScalar(self, dType):
        """Directly run by MAD, never used by user"""
        return self.readMADMatrix(dType, [1, 1])[0][0]

    def readMADElement(self, elmName, element): #Needs improvement!
        """Directly run by MAD, never used by user"""
        self.__pagesWritten += 1
        return 

    def readMADMatrix(self, dType, dims):
        """Directly run by MAD, never used by user"""
        #Below line does not work on windows - the windows version uses access = ... rather than flags and prot
        self.mmap = mmap.mmap(self.openFile.fileno(), length=0, flags=mmap.MAP_SHARED)# prot=mmap.PROT_READ)
        result = np.frombuffer(dtype=dType, buffer=self.mmap, count=dims[0]*dims[1], offset=self.__pagesWritten*self.__PAGE_SIZE).reshape(dims)
        self.__pagesWritten += result.nbytes // self.__PAGE_SIZE + 1
        return result

    def readMADString(self, dims):
        """Directly run by MAD, never used by user"""
        self.mmap = mmap.mmap(self.openFile.fileno(), length=0, flags=mmap.MAP_SHARED)# prot=mmap.PROT_READ)
        decodedData = np.ndarray(dims, dtype=np.int32, buffer=self.mmap, offset=self.__pagesWritten*self.__PAGE_SIZE)
        decodedString = ''
        stringMatrix = np.resize(decodedData, dims)
        for val in stringMatrix[0]:
            decodedString = decodedString + chr(val) #Convert back to string

        self.__pagesWritten += decodedData.nbytes // self.__PAGE_SIZE + 1
        return decodedString
    #---------------------------------------------------------------------------------------------------#
    
    def __pyToLuaLst(self, lst: list[Any], split = False) -> str:
        """Convert a python list to a lua list in a string, used when sending information to MAD, should not need to be accessed by user"""
        newList = str(lst).replace("[", "{",).replace("]", "}",).replace("(", "{").replace(")", "}")
        # #-------Resolves character limit in interactive mode-----------#
        # for x in range(len(newList) // 125):
        #     idx = newList.find(",", 125*x, 125*(x+1))
        #     while idx <  125*(x+1) and idx > 0:
        #         newIdx = idx + 1
        #         idx =  newList.find(",", idx + 1, 125*(x+1))
        #     newList = newList[:newIdx] + "\n" + newList[newIdx:]
        # #---------------------------------------------------------------#
        return newList

    #----------------------------------Sending variables across to MAD----------------------------------------#
    def sendVariables(self, varNames: list[str], vars: list[Union[np.ndarray, int, float, list]] = None):
        """Send variables to the MAD process, either send a list of varNames that already exist in the python MAD class or the varNames along with a list of the data"""
        if not vars: vars = list(self[tuple(varNames)])
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
                varTypes.append(vars[i].dtype)

        # ---------------------Adaptive file size--------------------# (Currently not used, file is opened at max memory size)
        totalDataSize  = self.__PAGE_SIZE * self.__pagesWritten
        varList = []
        varTypesList = []
        initIndex = 0
        for i in range(len(vars)):
            totalDataSize += (vars[i].nbytes // self.__PAGE_SIZE + 1) * self.__PAGE_SIZE
            if totalDataSize*1.1 > self.RAM_LIMIT:
                if i == initIndex: raise(OverflowError("Data size greater than ram limit, cannot send to mad")) #Next step would be to send in chunks
                varList.append(vars[initIndex:i])
                varTypesList.append(varTypes[initIndex:i])
                totalDataSize = (vars[i].nbytes // self.__PAGE_SIZE + 1) * self.__PAGE_SIZE
                initIndex = i
        varList.append(vars[initIndex:])
        varTypesList.append(varTypes[initIndex:])
        #-----------------------------------------------------------#
        for i in range(len(varList)):
            self.writeToSharedMemory(varList[i])
            fileInput = 'local readIMatrix, readMatrix, readCMatrix, readScalar in require ("madl_mmap")\n'
            fileInput += f'openSharedMemory("{self.shm.name}")\n'
            for j in range(len(varList[i])):
                match varTypesList[i][j]: #Errors here if not using numpy array
                    case np.int32:
                        functionToCall = "readIMatrix"
                    case np.float64:
                        functionToCall = "readMatrix"
                    case np.complex128:
                        functionToCall = "readCMatrix"
                    case "scalar":
                        functionToCall = "readScalar"
                    case _:
                        print(varTypesList)
                        raise(NotImplementedError("received type:", varList.dtype, "Only int32, float64 and complex128 implemented"))
                        
                fileInput += f'{varNames[j]} = {functionToCall}({self.__pyToLuaLst(varList[i][j].shape)})\n' #Process return
                # self.output.write(f'{varNames[j]} = {functionToCall}({self.__pyToLuaLst(varList[i][j].shape)})\n') #Process return (debug)
            fileInput += f'closeSharedMemory()\n'
            if self.sendScript(fileInput) != 5: raise(RuntimeError("MAD process failed", self.process.match.group(0)))
            if len(varList) > 1 and i < len(varList) - 1: self.resetShmSafely() #Split into several because too much data, so memory needs cleaning every time (does it?)

    
    def sendVar(self, varName: str, var: Union[np.ndarray, int, float, list] = None):
        """Send a variable to the MAD process, either send a varName that already exists in the python MAD class or a varName along with data"""
        if var is not None: self.sendVariables([varName], [var])
        else:   self.sendVariables([varName])
    
    def sendall(self):
        """Send all the variables that currently exist in the MAD dictionary, will overwrite variables in the MAD environment, use with caution"""
        self.sendVariables(list(self.userVars.keys()))
    #-------------------------------------------------------------------------------------------------------------#

    #-----------------------------------Receiving variables from to MAD-------------------------------------------#
    def receiveVariables(self, varNameList: list[str]) -> Any: #Function used by user / internally
        """Given a list of variable names, receive the variables from the MAD process, and save into the MAD dictionary"""
        varNameIndex = 0
        numVars = len(varNameList)
        y = min(numVars, 20)
        for x in range(0, numVars, 20): #Splits the reading to only 20 variables are read at once, significantly improves performance
            status = "continue"
            self.__possibleProcessReturn.append(r"(?P<command>pyCommand:.+\n)+(?P<status>readtable|continue|finished)") #readtable is a dummy var in order to have the matching
            MADReturn = self.sendScript(f"""
            openSharedMemory("{self.shm.name}", true)
            local offset = sharedata({self.__pyToLuaLst(varNameList[x:y]).replace("'", "")})                  --This mmaps to shared memory
            closeSharedMemory()
                """)
            while status != "finished":
                if MADReturn == 6:
                    self.__madReturn = self.process.match.group(0).replace("\t", "\r\n").split(":")[1:]
                    numVars, status = self.__getVars(varNameList[varNameIndex:], self)
                    varNameIndex += numVars
                else:
                    raise(RuntimeError(self.process.match.group(0)))
                if status == "continue":
                    MADReturn = self.writeToProcess("continue")
            self.__possibleProcessReturn.pop()
            y += min(20, numVars - y)
        
            if self.process.expect(self.__possibleProcessReturn) != 5: raise(RuntimeError(self.process.match.group(0)))
        return self[tuple(varNameList)]
    
    def __getVars(self, varNameList: list[str], dictionary) -> Union[int, str]: # Function used internally by python or MAD
        """Mainly used by receiveVariables, by evaluating the return from the MAD process and storing the result in dictionary"""
        varNameIndex = 0
        idx = 0
        while idx < len(self.__madReturn): #Change to be a numbered loop!
            evaledFunc = eval(self.__madReturn[idx].split("\r\n")[0], self.globalVars, {"self":self}) 
            if evaledFunc is not None: #Change the output of self.safelyCloseShm
                if isinstance(evaledFunc, str) and evaledFunc == "None": #Special case when the result is nil
                    dictionary[varNameList[varNameIndex]] = eval(evaledFunc)
                else:
                    dictionary[varNameList[varNameIndex]] = evaledFunc
                varNameIndex += 1
            idx += 1
        status = self.process.match.group("status")
        return varNameIndex, status
    
    def readMADTable(self) -> list: #Not doing named tables yet
        """WIP: Reads a table from MAD and returns a list"""
        table = {}
        startTable = endTable = 0
        for i in range(len(self.__madReturn)):
            if "readMADTable(" in self.__madReturn[i]:
                startTable = i
            if "tablehasended" in self.__madReturn[i]:
                endTable = i 
                break
        entireReturn = self.__madReturn
        self.__madReturn = entireReturn[startTable+1:endTable+1]
        self.__getVars(list(range(endTable - startTable)), table) 
        self.__madReturn = entireReturn[:startTable+1] + entireReturn[endTable+1:]
        return list(table.values())

    
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
    #-------------------------------------------------------------------------------------------------------------#

    #----------------------------------Calling functions(WIP)-----------------------------------------------------#
    def callFunc(self, resultName: Union[str, list[str]], funcName: str, *args): #Should result name be provided? ALSO NOT TESTED
        """Call the function funcName and store the result in resultName, then retreive the result into the MAD dictionary"""
        if isinstance(resultName, list): resultName = self.__pyToLuaLst(resultName)
        if resultName: stringStart = f"do {self.__getAsMADString(resultName)} = "
        else: stringStart = "do "
        self.writeToProcess(stringStart + f"""{self.__getAsMADString(funcName)}({self.__getArgsAsString(*args)}) end""")
        return self.receiveVar(resultName)

    def callMethod(self, resultName: str, varName: Union[str, list[str]], methName: str, *args):
        """Call the method methName of the variable varName and store the result in resultName, then retreive the result into the MAD dictionary"""
        if isinstance(resultName, list): resultName = self.__pyToLuaLst(resultName)
        if resultName: stringStart = f"do {self.__getAsMADString(resultName)} = "
        else: stringStart = "do "
        self.writeToProcess(stringStart + f"""{self.__getAsMADString(varName)}:{self.__getAsMADString(methName)}({self.__getArgsAsString(*args)}) end""") # -2 to get rid of ", "
        if resultName: return self.receiveVar(resultName)
    #-------------------------------------------------------------------------------------------------------------#
    
    #------------------------------------------Stored Data Manipulation-------------------------------------------#
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
        fildes = os.open("/dev/shm/"+self.shm.name, os.O_RDWR)
        os.ftruncate(fildes, 0)
        os.ftruncate(fildes, self.RAM_LIMIT)
        self.__pagesWritten = 0
        self.shm = shared_memory.SharedMemory(name=self.shm.name, create=False, size = self.RAM_LIMIT)
        if resetMAD: self.writeToProcess('=require ("madl_mmap").safelyCloseMemory()')


    def closeData(self): #After calling this, the variables within MAD are still accessible but communication has ended
        """Close the shared memory, MAD process """
        self.convertMmapToData()
        self.userVars.clear()
        self.shm.close() #Closes the shared memory, needs to be done before unlinked
        self.shm.unlink() #Deletes the shared memory (prevents memory leaks)
        if self.process: 
            self.process.sendcontrol("c") #ctrl-c (stops mad)
            self.process.close()
        self.openFile.close()
        # self.mmap.close() #N
    #---------------------------------------------------------------------------------------------------#
        
    #-------------------------------Setup MAD Classes---------------------------------------------------#
    def __getKwargAsString(self, **kwargs): #Keep an eye out for failures when kwargs is empty, shouldn't occur in current setup
        """Convert a kwargs input to a string used by MAD, should not be required by the user"""
        kwargsString = "{"
        for key, item in kwargs.items():
            keyString = str(key).replace("'", "")
            if isinstance(item, str): #Need to keep strings in kwargs
                item = "'" + item + "'"
            itemString = self.__getAsMADString(item)
            kwargsString += keyString + " = " + itemString + ", "
        return kwargsString + "}"
    
    def __getArgsAsString(self, *args):
        argStr = ""
        for arg in args:
            argStr += self.__getAsMADString(arg) + ", "
        return argStr[:-2] #Assumes args is always put last
    
    def __getAsMADString(self, var: Any):
        if isinstance(var, list):
            return self.__pyToLuaLst(var) 
        elif isinstance(var, (madObject, madElement)):
            return var.name
        elif isinstance(var, dict):
            return self.__getKwargAsString(**var)
        elif callable(var):
                return var.__name__
        else:
            return str(var).replace("False", "false").replace("True", "true")

    def MADKwargs(self, varName: str, *args, **kwargs):
        if varName: start = f"{varName} = "
        else: start = ""
        return  start + f"""{{ {self.__getKwargAsString(**kwargs)[1:-1]} {self.__getArgsAsString(*args)} }} """

    def MADLambda(self, varName, arguments: list[str], expression: str):
        return self.__getAsMADString(varName) + " = \\" + self.__getArgsAsString(tuple(arguments))[1:-1].replace("'", "") + " -> " + expression

    def setupClass(self, className: str, moduleName: str, resultName: Union[str, list[str]], *args, **kwargs):
        """Create a class 'className' from the module 'modulaName' and store into the variable 'varName'
        the kwargs are used to as extra keyword arguments within MAD """
        if isinstance(resultName, list): 
            self.sendScript(f"""
    {self.__pyToLuaLst(resultName)[1:-1].replace("'", "")} = {className} {{ {self.__getKwargAsString(**kwargs)[1:-1]} {self.__getArgsAsString(*args)} }} 
                """)
            self.receiveVariables(resultName)

        else:
            self.sendScript(f"""
    {resultName} = {className} '{resultName}' {{ {self.__getKwargAsString(**kwargs)[1:-1]} {self.__getArgsAsString(*args)} }} 
                """)
            if moduleName == "MAD.element":
                self[resultName] = madElement(resultName, self)
            else:
                self[resultName] = madObject(resultName, self) 

    def deferedExpr(self, **kwargs):
        """Create a deffered expression object where the kwargs are used as the deffered expressions, specified using strings """
        return self.__getKwargAsString(**kwargs).replace("=", ":=").replace("'", "")[1:-3] #Change := to equals, remove string identifers, and remove ", "

    def deferred(self, varName: str, **kwargs):
        """Create a deffered expression object with the name "varName" where the kwargs are used as the deffered expressions, specified using strings """
        self.sendScript(f"""
local deferred in MAD.typeid
{varName} = deferred {{{self.deferedExpr(**kwargs)}}}
            """)
        self.__dict__[varName] = deferred(varName, self)

    def loadsequence(self, seqName: str, seqFilename: str, targetFile: str = None):
        """Load a MAD-X sequence from the file seqFilename and into the variable 'seqName'. Optionally add a targetFile, which is the MAD version of the sequence file"""
        if ".seq" not in seqFilename: seqFilename += ".seq"
        if not targetFile: targetFile = seqFilename.strip(".seq")
        if ".mad" not in targetFile: targetFile += ".mad"
        #Potential failure below - if *args does not contain element set, " may be removed unnecessarily
        self.sendScript(f"""
MADX:load("{seqFilename}", "{targetFile}")
{seqName} = MADX.seq
            """)
        self.__dict__[seqName] = madObject(seqName, self)
    #---------------------------------------------------------------------------------------------------#

    #-------------------------------For use with the "with" statement-----------------------------------#
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, tb):
        if self.log:
            print()
        # if exc_type:
        #     traceback.print_exception(exc_type, exc_value, tb)
        #     time.sleep(5) #for debugging
        self.closeData()
    #---------------------------------------------------------------------------------------------------#
