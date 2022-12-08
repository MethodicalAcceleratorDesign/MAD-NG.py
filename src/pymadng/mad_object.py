import numpy as np  # For arrays  (Works well with multiprocessing and mmap)
from typing import Any, Iterable, Union, List  # To make stuff look nicer
from types import MethodType  # Used to attach functions to the class

# Custom Classes:
from .pymadClasses import madObject, madFunctor, madReference
from .mad_process import mad_process

# TODO: place into MAD's MADX environment - Still debating
# TODO: Make it so that MAD does the loop for variables not python (speed)


class MAD(object):  # Review private and public
    """An object that allows communication with MAD-NG

    Attributes:
        py_name: A string indicating the name of the reference to python from MAD-NG, for communication from MAD-NG to Python.
    """

    def __init__(self, py_name: str = "py", mad_path: str = None, debug: bool = False):
        """Create a MAD Object to interface with MAD-NG.

        The modules MADX, elements, sequence, mtable, twiss, beta0, beam, survey, object, track, match are imported into
        the MAD-NG environment by default, along with all the elements in the elements module.

        Args:
            py_name (str): The name used to interact with the python process from MAD
                (default = "py")
            madPath (str): The path to the mad executable, for a value of None, the one that comes with pymadng package will be used
                (default = None)
            debug (bool): Sets debug mode on or off
                (default = False)

        Returns:
            A MAD object, allowing for communication with MAD-NG
        """
        self.__process = mad_process(py_name, mad_path, debug, self)
        self.send(
            """
        function __mklast__ (a, b, ...)
            if MAD.typeid.is_nil(b) then return a
            else return {a, b, ...}
            end
        end
        """
        )
        self.py_name = py_name
        # --------------------------------Retrieve the modules of MAD-------------------------------#
        # Limit the 80 modules
        modulesToImport = [
            "MAD",  # Need MAD.MAD?
            "MADX",
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

    # ------------------------------------------------------------------------------------------#

    def send(self, data: Union[str, int, float, np.ndarray, bool, list]) -> None:
        """Send data to MAD-NG.

        Args:
            data (str/int/float/ndarray/bool/list): The data to send to MAD-NG.

        Returns:
            self (the mad object) - so that you can do mad.send("...").recv()

        Raises:
            TypeError: An unsupported type was attempted to be sent to MAD-NG.
            AssertionError: If and np.ndarray is input, the matrix must be of two dimensions.
        """
        self.__process.send(data)
        return self

    def recv(
        self, varname: str = None
    ) -> Union[str, int, float, np.ndarray, bool, list]:
        """Return received data from MAD-NG.

        Args:
            varname(str): The name of the variable you are receiving (Only useful when receiving references)
                (default is None)

        Returns:
            Data from MAD-NG with type str/int/float/ndarray/bool/list, depending what was asked from MAD-NG.
        """
        return self.__process.recv(varname)

    def receive(
        self, varname: str = None
    ) -> Union[str, int, float, np.ndarray, bool, list]:
        """See :meth:`recv`"""
        return self.__process.recv(varname)

    def recv_and_exec(self, env: dict = {}) -> dict:
        """Receive a string from MAD-NG and execute it.

        Note: Numpy and this object are available during the execution as ``np`` and ``mad`` respectively

        Args:
            env (dict): The environment you would like the string to be executed in.
                (default = {})

        Returns:
            The updated environment after executing the string.
        """
        return self.__process.recv_and_exec(env)

    def send_rng(self, rng: Union[np.ndarray, list]):
        """Send a numpy array as a range to MAD-NG.

        Args:
            rng (ndarray/list): A list of values interpreted as a range and sent to MAD-NG.
        """
        return self.__process.send_rng(rng)

    def send_lrng(self, lrng: Union[np.ndarray, list]):
        """Send a numpy array as a logrange to MAD-NG.

        Args:
            lrng (ndarray/list): A list of values interpreted as a logrange and sent to MAD-NG.
        """
        return self.__process.send_lrng(lrng)

    def send_tpsa(self, monos: np.ndarray, coefficients: np.ndarray):
        """Send the monomials and coeeficients of a TPSA to MAD

        The combination of monomials and coeeficients creates a table representing the TPSA object in MAD-NG.

        Args:
            monos (ndarray): A list of monomials in the TPSA.
            coefficients (ndarray): A list of coefficients in the TPSA.

        Raises:
            AssertionError: The list of monomials must be a 2-D array (each monomial is 1-D).
            AssertionError: The number of monomials and coefficients must be identical.
        """
        self.__process.send_tpsa(monos, coefficients)

    def send_ctpsa(self, monos: np.ndarray, coefficients: np.ndarray):
        """Send the monomials and coeeficients of a complex TPSA to MAD

        The combination of monomials and coeeficients creates a table representing the complex TPSA object in MAD-NG.

        See :meth:`send_tpsa`.
        """
        self.__process.send_ctpsa(monos, coefficients)

    def Import(self, module: str, vars: List[str] = []):
        """Import modules into the MAD-NG environment

        Retrieve the classes in MAD-NG from the module ``module``, while only importing the classes in the list ``vars``.
        If no list is provided, it is assumed that you would like to import every class from the module.

        Args:
            module (str): The name of the module to import from.
            vars (List[str]): The variables to import from module.
                (default = [])
        """
        script = ""
        if vars == []:
            vars = [x.strip("(...)") for x in dir(madReference(module, self))]
        for className in vars:
            script += f"""{className} = {module}.{className}\n"""
        self.__process.send(script)

    def __getattr__(self, item):
        if item[0] == "_" and not item == "__last__":
            raise (AttributeError(item))
        return self.receive_var(item)

    # -----------------------------Make the class work like a dictionary----------------------------#
    def __setitem__(self, varName: str, var: Any) -> None:
        if isinstance(varName, tuple):
            nameList = list(varName)
            if isinstance(var, madReference):
                varList = [
                    type(var)(var.__name__ + f"[{i+1}]", self)
                    for i in range(len(nameList))
                ]
            else:
                varList = list(var)
            if len(varList) != len(nameList):
                raise ValueError(
                    "Incorrect number of values to unpack, received",
                    len(varList),
                    "variables and",
                    len(nameList),
                    "keys",
                )
            self.send_variables(nameList, varList)
        else:
            self.send_var(varName, var)

    def __getitem__(self, varName: str) -> Any:
        return self.receive_var(varName)

    # ----------------------------------------------------------------------------------------------#

    # --------------------------------Sending data to subprocess------------------------------------#
    def eval(self, input: str):
        """Evaluate an expression.

        Start the expression with ``=`` to receive the return value.

        Args:
            input (str): An expression that would like to be evaluated in MAD-NG.

        Returns:
            If the string starts with ``=`` the evaluation of the expression is returned.
        """
        if input[0] == "=":
            input = "__last__" + input
            self.__process.send(input)
            return self["__last__"]
        else:
            self.__process.send(input)

    def MADX_env_send(self, input: str):
        """Open the MAD-X environment in MAD-NG and directly send code.

        Args:
            input (str): The code that would like to be evaluated in the MAD-X environment in MAD-NG.
        """
        return self.__process.send("MADX:open_env()\n" + input + "\nMADX:close_env()")

    # ----------------------------------------------------------------------------------------------#

    # ----------------------------------Sending variables across to MAD----------------------------------------#
    def send_variables(
        self,
        names: List[str],
        vars: List[Union[str, int, float, np.ndarray, bool, list]],
    ):
        """Send variables to the MAD-NG process.

        Send the variables in vars with the names in names to MAD-NG.

        Args:
            names (List[str]): The list of names that would like to name your variables in MAD-NG.
            vars (List[str/int/float/ndarray/bool/list]): The list of variables to send with the names 'names' in MAD-NG.

        Raises:
            Errors: See :meth:`send`.
        """
        for i in range(len(vars)):
            if isinstance(vars[i], madReference):
                self.__process.send(f"{names[i]} = {vars[i].__name__}")
            else:
                self.__process.send(f"{names[i]} = {self.py_name}:recv()")
                self.__process.send(vars[i])

    def send_var(self, name: str, var: Union[str, int, float, np.ndarray, bool, list]):
        """Send a variable to the MAD-NG process.

        Send the variable var with the name, name to MAD-NG.

        Args:
            name (List[str]): The name that would like to name your variable in MAD-NG.
            var (List[str/int/float/ndarray/bool/list]): The variable to send with the name, name in MAD-NG.

        Raises:
            Errors: See :meth:`send`.
        """
        self.send_variables([name], [var])

    # -------------------------------------------------------------------------------------------------------------#

    # -----------------------------------Receiving variables from to MAD-------------------------------------------#
    def receive_variables(self, names: List[str]) -> Any:
        """Receive variables from the MAD-NG process

        Given a list of variable names, receive the variables from the MAD-NG process.

        Args:
            names (List[str]): The list of names of variables that you would like to receive from MAD-NG.

        Returns:
            See :meth:`recv`.
        """
        returnVars = []
        for i in range(len(names)):
            if (
                names[i][:2] != "__" or "__last__" in names[i]
            ):  # Check for private variables
                self.__process.send(f"{self.py_name}:send({names[i]})")
                returnVars.append(self.__process.recv(names[i]))
        return tuple(returnVars)

    def receive_var(self, name: str) -> Any:
        """Receive a variable from the MAD-NG process.

        Given a variable name, receive the variable from the MAD-NG process.

        Args:
            name (str): The name of the variable that you would like to receive from MAD-NG.

        Returns:
            See :meth:`recv`

        """
        return self.receive_variables([name])[0]

    # -------------------------------------------------------------------------------------------------------------#

    # ----------------------------------Calling/Creating functions-------------------------------------------------#
    def call_func(self, funcName: str, *args):
        """Call the function funcName and store the result in ``__last__``.

        To assign the return values names, then use ``mad[names] = mad.call_func(funcName, args)``, where ``names`` is a
        variable length argument list of strings.

        Args:
            funcName (str): The name of the function that you would like to call in MAD-NG.
            *args: Variable length argument list required to call the function funcName.

        Returns:
            A reference to a list of the return values of the function.
        """
        self.__process.send(
            f"__last__ = __mklast__({self.get_MAD_string(funcName)}({self.__getArgsAsString(*args)}))\n"
        )
        return madObject("__last__", self)

    def MAD_lambda(self, arguments: List[str], expression: str):
        """Create a small anonymous function in MAD-NG named ``__last__``.

        To assign the returned lambda function a name, then use ``mad['name'] = mad.MAD_lambda(arguments, expression)``.

        Args:
            arguments (List[str]): The list of arguments required to call the function.
            expression (str): The expression that you would like performed and returned when called.

        Returns:
            A reference to the function.
        """

        result = "__last__ = \\"
        if arguments:
            for arg in arguments:
                result += self.get_MAD_string(arg) + ","
            result = result[:-1]
        self.send(result + " -> " + expression)
        return madFunctor("__last__", self)

    # -------------------------------------------------------------------------------------------------------------#

    # -------------------------------String Conversions--------------------------------------------------#
    def __getKwargAsString(self, **kwargs):
        # Keep an eye out for failures when kwargs is empty, shouldn't occur in current setup
        """Convert a keyword argument input to a string used by MAD-NG
        THIS NEEDS TO BE IMPROVED!, WHAT IF USER WANTS BIG DATA AS ARGUMENT"""
        kwargsString = "{"
        for key, item in kwargs.items():
            keyString = str(key).replace("'", "")
            itemString = self.get_MAD_string(item)
            kwargsString += keyString + " = " + itemString + ", "
        return kwargsString + "}"

    def __getArgsAsString(self, *args):
        """Convert an argument input to a string used by MAD-NG
        THIS NEEDS TO BE IMPROVED!, WHAT IF USER WANTS BIG DATA AS ARGUMENT"""
        argStr = ""
        for arg in args:
            argStr += self.get_MAD_string(arg) + ", "
        return argStr[:-2]  # Assumes args is always put last

    def __pyToLuaLst(self, lst: List[Any]) -> str:
        """Convert a python list to a lua list in a string, used when sending information to MAD-NG, should not need to be accessed by user"""
        luaString = "{"
        for item in lst:
            luaString += self.get_MAD_string(item, True) + ", "
        return luaString + "}"

    def get_MAD_string(self, var: Any, convertString=False):
        """Convert a list of objects into the required string for MAD-NG.

        Args:
            var (Any): A variable that you would like converted into the string that can be used by MAD-NG
            convertString (bool): A boolean that when true converts ``var = "Hello World"`` to ``"'Hello World'"`` (Converts to string, not expression in MAD-NG)
                (default = False)

        Returns:
            The converted string, ready for use, directly in the MAD-NG environment

        """
        if isinstance(var, (list, np.ndarray)):
            return self.__pyToLuaLst(var)
        elif var == None:
            return "nil"
        elif isinstance(var, str) and convertString:
            return "'" + var + "'"
        elif isinstance(var, complex):
            # Remove brackets and convert j to i
            return str(var)[1:-1].replace("j", "i") 
        elif isinstance(var, (madReference)):
            return var.__name__
        elif isinstance(var, dict):
            return self.__getKwargAsString(**var)
        elif callable(var):
            return var.__name__
        else:
            return str(var).replace("False", "false").replace("True", "true")

    # ---------------------------------------------------------------------------------------------------#

    def deferred(self, **kwargs):
        """Create a deferred expression object

        For the deferred expression object, the kwargs are used as the deffered expressions, with ``=`` replaced
        with ``:=``. To assign the returned object a name, then use ``mad['name'] = mad.deffered(kwargs)``.

        Args:
            **kwargs: A variable list of keyword arguments, keyword as the name of the deffered expression within the object
            and the value as a string that is sent directly to the MAD-NG environment.

        Returns:
            A reference to the deffered expression object.
        """
        self.__process.send(
            f"__last__ = __mklast__( MAD.typeid.deferred {{ {self.__getKwargAsString(**kwargs).replace('=', ':=')[1:-3]} }} )"
        )
        return madReference("__last__", self)

    def __dir__(self) -> Iterable[str]:
        pyObjs = [x for x in super(MAD, self).__dir__() if x[0] != "_"]
        pyObjs.extend(self.env())
        return pyObjs

    def env(self) -> List[str]:
        """Retreive the environment of MAD

        Returns:
            A list of strings indicating the available variables and modules within the MAD-NG environment
        """
        return dir(self.receive_var(f"{self.py_name}._env"))

    # -------------------------------For use with the "with" statement-----------------------------------#
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        del self

    # ---------------------------------------------------------------------------------------------------#
