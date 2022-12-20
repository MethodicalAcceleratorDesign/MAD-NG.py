import numpy as np  # For arrays  (Works well with multiprocessing and mmap)
from typing import Any, Iterable, Union, List  # To make stuff look nicer

# Custom Classes:
from .pymadClasses import madReference
from .mad_process import mad_process

# TODO: Make it so that MAD does the loop for variables not python (speed)


class last_counter():
    def __init__(self, size: int, mad_process):
        self.counter = list(range(size, 0, -1))
        self.mad_process = mad_process

    def get(self):
        assert len(self.counter) != 0, "Assigned too many anonymous, variables, increase num_temp_vars or assign the variables into MAD"
        return f"__last__[{self.counter.pop()}]"
    
    def set(self, idx):
        self.counter.append(idx)
    

class MAD(object):  # Review private and public
    """An object that allows communication with MAD-NG

    Attributes:
        py_name: A string indicating the name of the reference to python from MAD-NG, for communication from MAD-NG to Python.
    """

    def __init__(self, py_name: str = "py", mad_path: str = None, debug: bool = False, num_temp_vars: int = 8, ipython_use_jedi: bool = False):
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
            num_temp_vars (int): The number of unique temporary variables you intend to use, see :doc:`Managing References <ex-managing-refs>`
                (default = 8)
            ipython_use_jedi (bool): Allow ipython to use jedi in tab completion, will be slower and may result in MAD-NG throwing errors
                (default = False)

        Returns:
            A MAD object, allowing for communication with MAD-NG
        """
        self.ipython_use_jedi = ipython_use_jedi
        self.__last_counter = last_counter(num_temp_vars, self)
        #Stop jedi running getattr on my classes...
        if not ipython_use_jedi: 
            try:
                shell = get_ipython().__class__.__name__
                if shell == 'TerminalInteractiveShell':
                    get_ipython().Completer.use_jedi = False
            except NameError:
                pass
        self.__process = mad_process(py_name, mad_path, debug, self)
        self.send(
            """
        function __mklast__ (a, b, ...)
            if MAD.typeid.is_nil(b) then return a
            else return {a, b, ...}
            end
        end
        __last__ = {}
        """
        )
        self.py_name = py_name
        # --------------------------------Retrieve the modules of MAD-------------------------------#
        # Limit the 80 modules
        modulesToImport = [
            "MAD",  # Need MAD.MAD?
            "MADX",
            "element",
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
        self.load("MAD", modulesToImport)

    # ------------------------------------------------------------------------------------------#

    def send(self, data: Union[str, int, float, np.ndarray, bool, list]) -> None:
        """Send data to MAD-NG.

        Args:
            data (str/int/float/ndarray/bool/list): The data to send to MAD-NG.

        Returns:
            self (the mad object) - so that you can do ``mad.send(...).recv()``

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

        Raises:
            TypeError: If you forget to give a name when receiving a reference,  
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

    def send_rng(self, start: float, stop: float, size: int):
        """Send a range to MAD-NG, equivalent to np.linspace, but in MAD-NG.

        Args:
            start (float): The start of range
            stop (float): The end of range (inclusive)
            size (float): The length of range
        """
        return self.__process.send_rng(start, stop, size)

    def send_lrng(self, start: float, stop: float, size: int):
        """Send a numpy array as a logrange to MAD-NG, equivalent to np.geomspace, but in MAD-NG.

        Args:
            start (float): The start of range
            stop (float): The end of range (inclusive)
            size (float): The length of range
        """
        return self.__process.send_lrng(start, stop, size)

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

    def __errhdlr(self, on_off: bool):
        self.send(f"py:__err("+ str(on_off).lower() + ")")

    def __safe_send(self, string: str):
        return self.send(f"py:__err(true); {string}; py:__err(false);")

    def load(self, module: str, vars: List[str] = []):
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
            vars = [x.strip("()") for x in dir(madReference(module, self))]
        elif isinstance(vars, str):
            vars = [vars]
        for className in vars:
            script += f"""{className} = {module}.{className}\n"""
        self.__process.send(script)

    def __getattr__(self, item):
        if item[0] == "_" and not item[:8] == "__last__":
            raise AttributeError(item)
        return self.recv_vars(item)

    # -----------------------------Make the class work like a dictionary----------------------------#
    def __setitem__(self, varName: str, var: Any) -> None:
        if isinstance(varName, tuple):
            varName = list(varName)
            if isinstance(var, madReference):
                var = [
                    type(var)(var.__name__ + f"[{i+1}]", self)
                    for i in range(len(varName))
                ]
            else:
                var = list(var)
            if len(var) != len(varName):
                raise ValueError(
                    "Incorrect number of values to unpack, received",
                    len(var),
                    "variables and",
                    len(varName),
                    "keys",
                )
        self.send_vars(varName, var)

    def __getitem__(self, varName: str) -> Any:
        return self.recv_vars(varName)

    # ----------------------------------------------------------------------------------------------#

    # --------------------------------Sending data to subprocess------------------------------------#
    def eval(self, input: str):
        """Evaluate an expression in MAD and return the result.

        Args:
            input (str): An expression that would like to be evaluated in MAD-NG.

        Returns:
            The evaluated result.
        """
        last_name = self.__last_counter.get()
        return self.send(f"{last_name} =" + input)[last_name]

    def MADX_env_send(self, input: str):
        """Open the MAD-X environment in MAD-NG and directly send code.

        Args:
            input (str): The code that would like to be evaluated in the MAD-X environment in MAD-NG.
        """
        return self.__process.send("MADX:open_env()\n" + input + "\nMADX:close_env()")

    def py_strs_to_mad_strs(self, input: Union[str, List[str]]):
        """Add ' to either side of a string or list of strings
        
        Args: 
            input(str/list[str]): The string or list of strings that you would like to add ' either side to.

        Returns:
            A string or list of strings with ' placed at the beginning and the end of the string.
        """
        if isinstance(input, list):
            return ["'" + x + "'" for x in input]
        else:
            return "'" + input + "'"

    # ----------------------------------------------------------------------------------------------#

    # ----------------------------------Sending variables across to MAD----------------------------------------#
    def send_vars(
        self,
        names: Union[str, List[str]],
        vars: List[Union[str, int, float, np.ndarray, bool, list]],
    ):
        """Send variables to the MAD-NG process.

        Send the variables in vars with the names in names to MAD-NG.

        Args:
            names (List[str]): The list of names that would like to name your variables in MAD-NG.
            vars (List[str/int/float/ndarray/bool/list]): The list of variables to send with the names 'names' in MAD-NG.

        Raises:
            Errors: See :meth:`send`.
            AssertionError: A list of names must be matched with a list of variables
            AssertionError: The number of names must match the number of variables
        """
        if isinstance(names, str): 
            names = [names]
            vars = [vars]
        else:
            assert isinstance(vars, list), "A list of names must be matched with a list of variables"
            assert len(vars) == len(names), "The number of names must match the number of variables"
        for i, var in enumerate(vars):
            if isinstance(vars[i], madReference):
                self.__process.send(f"{names[i]} = {var.__name__}")
            else:
                self.__process.send(f"{names[i]} = {self.py_name}:recv()")
                self.__process.send(var)
    # -------------------------------------------------------------------------------------------------------------#

    # -----------------------------------Receiving variables from to MAD-------------------------------------------#
    def recv_vars(self, names: Union[str, List[str]]) -> Any:
        """Receive variables from the MAD-NG process

        Given a list of variable names, receive the variables from the MAD-NG process.

        Args:
            names (List[str]): The list of names of variables that you would like to receive from MAD-NG.

        Returns:
            See :meth:`recv`.
        """
        if isinstance(names, str): 
            names = [names]
            lst_rtn = False
        else: 
            lst_rtn = True

        returnVars = []
        for name in names:
            if name[:2] != "__" or name[:8] == "__last__":  # Check for private variables
                self.__process.send(f"{self.py_name}:__err(true):send({name}):__err(false)")
                returnVars.append(self.__process.recv(name))
        
        if lst_rtn:
            return tuple(returnVars)
        else: 
            return returnVars[0]

    # -------------------------------------------------------------------------------------------------------------#

    # ----------------------------------Calling/Creating functions-------------------------------------------------#
    def __call_func(self, funcName: str, *args):
        """Call the function funcName and store the result in ``__last__``."""
        last_name = self.__last_counter.get()
        args_string, vars_to_send = self.__get_args_string(*args)
        self.__process.send(
            f"{last_name} = __mklast__({funcName}({args_string}))\n"
        )

        for var in vars_to_send:
            self.send(var)
        return madReference(last_name, self)
    # -------------------------------------------------------------------------------------------------------------#

    # -------------------------------String Conversions--------------------------------------------------#
    def __get_kwargs_string(self, **kwargs):
        # Keep an eye out for failures when kwargs is empty, shouldn't occur in current setup
        """Convert a keyword argument input to a string used by MAD-NG"""
        kwargsString = "{"
        vars_to_send = []
        for key, item in kwargs.items():
            keyString = str(key).replace("'", "")
            itemString, var = self.__to_MAD_string(item)
            kwargsString += keyString + " = " + itemString + ", "
            vars_to_send.extend(var)
        return kwargsString + "}", vars_to_send

    def __get_args_string(self, *args):
        """Convert an argument input to a string used by MAD-NG"""
        mad_string = ""
        vars_to_send = []
        for arg in args:
            string, var = self.__to_MAD_string(arg)
            mad_string += string + ", "
            vars_to_send.extend(var)
        return mad_string[:-2], vars_to_send

    def __to_MAD_string(self, var: Any):
        """Convert a list of objects into the required string for MAD-NG. 
        Converting string instead of sending more data is up to 2x faster (therefore last resort)."""
        if isinstance(var, list):
            string, vars_to_send = self.__get_args_string(*var)
            return "{" + string + "}", vars_to_send
        elif var is None:
            return "nil", []
        elif isinstance(var, str):
            return var, []
        elif isinstance(var, complex):
            string = str(var)
            return (string[0] == "(" and string[1:-1] or string).replace("j", "i"), []
        elif isinstance(var, (madReference)):
            return var.__name__, []
        elif isinstance(var, dict):
            return self.__get_kwargs_string(**var)
        elif isinstance(var, bool):
            return str(var).lower(), []
        elif isinstance(var, (float, int)):
            return str(var), []
        else:
            return f"{self.py_name}:recv()", [var]

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
        last_name = self.__last_counter.get()
        kwargs_string, vars_to_send = self.__get_kwargs_string(**kwargs)
        self.__process.send(
            f"{last_name} = __mklast__( MAD.typeid.deferred {{ {kwargs_string.replace('=', ':=')[1:-3]} }} )"
        )
        for var in vars_to_send:
            self.send(var)
        return madReference(last_name, self)

    def __dir__(self) -> Iterable[str]:
        pyObjs = [x for x in super(MAD, self).__dir__() if x[0] != "_"]
        pyObjs.extend(self.env())
        pyObjs.extend(dir(self.recv_vars("_G")))
        return pyObjs

    def env(self) -> List[str]:
        """Retreive the list of names of variables in the environment of MAD

        Returns:
            A list of strings indicating the available variables and modules within the MAD-NG environment
        """
        return dir(self.recv_vars(f"{self.py_name}._env"))

    # -------------------------------For use with the "with" statement-----------------------------------#
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        del self

    # ---------------------------------------------------------------------------------------------------#
