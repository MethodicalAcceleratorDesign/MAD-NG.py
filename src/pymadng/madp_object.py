from __future__ import annotations  # For type hinting

import platform
from pathlib import Path
from typing import Any, TYPE_CHECKING, TextIO  # To make stuff look nicer

import numpy as np  # For arrays  (Works well with multiprocessing and mmap)

# Custom Classes:
from .madp_classes import (
    high_level_mad_func,
    high_level_mad_object,
    high_level_mad_ref,
    mad_high_level_last_ref,
)
from .madp_last import last_counter
from .madp_pymad import is_private, mad_process, type_fun
from .madp_strings import format_kwargs_to_string

if TYPE_CHECKING:
    from collections.abc import Iterable

# TODO: Make it so that MAD does the loop for variables not python (speed) (jgray 2023)
# TODO: Review recv_and exec:
"""
Default arguments are evaluated once at module load time.
This may cause problems if the argument is a mutable object such as a list or a dictionary.
If the function modifies the object (e.g., by appending an item to a list), the default value is modified.
Source: https://google.github.io/styleguide/pyguide.html
"""  # (jgray 2023)

bin_path = Path(__file__).parent.resolve() / "bin"


# --------------------- Overload recv_ref functions ---------------------- #
# Override the type of reference created by python
# (so madp_pymad can be run independently, these objects create pythonic objects)
def recv_ref(self: mad_process) -> high_level_mad_ref:
    return high_level_mad_ref(self.varname, self)


def recv_obj(self: mad_process) -> high_level_mad_object:
    return high_level_mad_object(self.varname, self)


def recv_fun(self: mad_process) -> high_level_mad_func:
    return high_level_mad_func(self.varname, self)


type_fun["ref_"]["recv"] = recv_ref
type_fun["obj_"]["recv"] = recv_obj
type_fun["fun_"]["recv"] = recv_fun
# ------------------------------------------------------------------------ #


class MAD(object):
    """An object that allows communication with MAD-NG

    Attributes:
      py_name: A string indicating the name of the reference to python from MAD-NG, for communication from MAD-NG to Python.
      __MAD_version__: A string indicating the version of MAD-NG being used. (Also accessible from ``pymadng.MAD().MAD.env.version``)
    """

    def __init__(
        self,
        mad_path: str | Path = None,
        py_name: str = "py",
        raise_on_madng_error: bool = True,
        debug: bool = False,
        stdout: TextIO | str | Path = None,
        redirect_sterr: bool = False,
        num_temp_vars: int = 8,
        ipython_use_jedi: bool = False,
    ):
        """Create a MAD Object to interface with MAD-NG.

        The modules MADX, elements, sequence, mtable, twiss, beta0, beam, survey, object, track, match are imported into
        the MAD-NG environment by default.

        Args:
          mad_path (str): The path to the mad executable, for the default value of None, the one that comes with pymadng package will be used
          py_name (str): The name used to interact with the python process from MAD, default is 'py'.
          raise_on_madng_error (bool): Will _always_ raise an error if MAD-NG errors, default is True.
          debug (bool): Sets debug mode on or off. This will output additional information to the stdout. (default is False)
          stdout (TextIO | str | Path): Redirect the MAD-NG stdout to a file, useful for debugging. If a TextIO is given, it will write to this file. If a string or Path is given, it is expected to be a file path, and will open this file to write to. (default is None)
          redirect_sterr (bool): Redirect the stderr to the stdout, useful for debugging. (default is False)
          num_temp_vars (int): The number of unique temporary variables you intend to use, see :doc:`Managing References <ex-managing-refs>` for more information. (default is 8)
          ipython_use_jedi (bool): Allow ipython to use jedi in tab completion, will be slower and may result in MAD-NG throwing errors. (default is False)

        Returns:
          A MAD object, allowing for communication with MAD-NG
        """

        # ------------------------- Create the process --------------------------- #
        mad_path = mad_path or bin_path / ("mad_" + platform.system())
        self.__process = mad_process(
            mad_path=mad_path,
            py_name=py_name,
            raise_on_madng_error=raise_on_madng_error,
            debug=debug,
            stdout=stdout,
            redirect_sterr=redirect_sterr,
        )
        self.__process.ipython_use_jedi = ipython_use_jedi
        self.__process.last_counter = last_counter(num_temp_vars)
        # ------------------------------------------------------------------------ #

        ## Store the relavent objects into a function to get reference objects
        self.__get_mad_reflast = lambda: mad_high_level_last_ref(self.__process)
        self.__get_mad_ref = lambda name: high_level_mad_ref(name, self.__process)

        if not ipython_use_jedi:  # Stop jedi running getattr on my classes...
            try:
                ipython = get_ipython()
                if ipython.__class__.__name__ == "TerminalInteractiveShell":
                    ipython.Completer.use_jedi = False
            except NameError:
                pass
        self.py_name = py_name
        # --------------------------------Retrieve the modules of MAD-------------------------------#
        # Limit the 80 modules
        modulesToImport = [
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
        self.load("MAD", *modulesToImport)
        self.__MAD_version__ = self.MAD.env.version

        # Send a function to MAD-NG to create a list in the return or a single value
        self.send(
            """
function __mklast__ (a, b, ...)
  if type(b) == "nil" then return a
  else                     return {a, b, ...}
  end
end
_last = {}
  """
        )

    # ------------------------------------------------------------------------------------------#

    # --------------------------- Receiving data from subprocess -------------------------------#
    def recv(
        self, varname: str = None
    ) -> str | int | float | np.ndarray | bool | list | high_level_mad_ref:
        """Return received data from MAD-NG.

        Args:
          varname(str): The name of the variable you are receiving (Only useful when receiving references)

        Returns:
          Data from MAD-NG with type str/int/float/ndarray/bool/list/ref, depending what was asked from MAD-NG.

        Raises:
          TypeError: If you forget to give a name when receiving a reference,
        """
        return self.__process.recv(varname)

    def receive(
        self, varname: str = None
    ) -> str | int | float | np.ndarray | bool | list | high_level_mad_ref:
        """See :meth:`recv`"""
        return self.__process.recv(varname)

    def recv_and_exec(self, context: dict = {}) -> dict:
        """Receive a string from MAD-NG and execute it.

        Note: The class numpy and the instance of this object are available during the execution as ``np`` and ``mad`` respectively

        Args:
          context (dict): The environment context you would like the string to be executed in.

        Returns:
          The updated environment after executing the string.
        """
        context["mad"] = self
        return self.__process.recv_and_exec(context)

    # --------------------------------Sending data to subprocess------------------------------------#
    def send(self, data: str | int | float | np.ndarray | bool | list) -> MAD:
        """Send data to MAD-NG.

        Args:
          data (str/int/float/ndarray/bool/list): The data to send to MAD-NG.

        Returns:
          self (the instance of the mad object)

        Raises:
          TypeError: An unsupported type was attempted to be sent to MAD-NG.
          AssertionError: If data is a np.ndarray, the matrix must be of two dimensions.
        """
        self.__process.send(data)
        return self

    def protected_send(self, string: str) -> MAD:
        """Send a string to MAD-NG, but if any of the command errors, python will be notified.
        Then, once python receives the fact that the command errored, it will raise an error.

        For example, if you send ``mad.send("a = 1/'a'")``, MAD-NG will error, and python will just continue.
        But if you send ``mad.protected_send("a = 1/'a'").recv()``, python will raise an error.
        Note, if the ``recv`` is not called, the error will not be raised.

        Args:
          string (str): The string to send to MAD-NG. This must be a string to be evaluated in MAD-NG. Not a string to be sent to MAD-NG.

        Returns:
          self (the instance of the mad object)
        """
        assert isinstance(string, str), "The input to protected_send must be a string"
        self.__process.protected_send(string)
        return self

    def psend(self, string: str) -> MAD:
        """See :meth:`protected_send`"""
        return self.protected_send(string)

    def send_range(self, start: float, stop: float, size: int):
        """Send a range to MAD-NG, equivalent to np.linspace, but in MAD-NG.

        Args:
          start (float): The start of range
          stop (float): The end of range (inclusive)
          size (float): The length of range
        """
        self.__process.send_range(start, stop, size)

    def send_logrange(self, start: float, stop: float, size: int):
        """Send a numpy array as a logrange to MAD-NG, equivalent to np.geomspace, but in MAD-NG.

        Args:
          start (float): The start of range
          stop (float): The end of range (inclusive)
          size (float): The length of range
        """
        self.__process.send_logrange(start, stop, size)

    def send_tpsa(self, monos: np.ndarray, coefficients: np.ndarray):
        """Send the monomials and coefficients of a TPSA to MAD

        The combination of monomials and coefficients creates a table representing the TPSA object in MAD-NG.

        Args:
          monos (ndarray): A list of monomials in the TPSA.
          coefficients (ndarray): A list of coefficients in the TPSA.

        Raises:
          AssertionError: The list of monomials must be a 2-D array (each monomial is 1-D).
          AssertionError: The number of monomials and coefficients must be identical.
          AssertionError: The monomials must be of type 8-bit unsigned integer
        """
        self.__process.send_tpsa(monos, coefficients)

    def send_cpx_tpsa(self, monos: np.ndarray, coefficients: np.ndarray):
        """Send the monomials and coefficients of a complex TPSA to MAD-NG

        The combination of monomials and coefficients creates a table representing the complex TPSA object in MAD-NG.

        Args:
          See: :meth:`send_tpsa`.

        Raises:
          See: :meth:`send_tpsa`.
        """
        self.__process.send_cpx_tpsa(monos, coefficients)

    # ---------------------------------------------------------------------------------------------------------#

    # -------------------------------- Dealing with communication of variables --------------------------------#
    def send_vars(self, **vars: str | int | float | np.ndarray | bool | list):
        """Send variables to the MAD-NG process.

        Send the variables in vars with the names in names to MAD-NG.

        Args:
          **vars (str/int/float/ndarray/bool/list): The variables to send with the assigned name in MAD-NG by the keyword argument.

        Raises:
          See: :meth:`send`.
        """
        self.__process.send_vars(**vars)

    def recv_vars(self, *names: str) -> Any:
        """Receive variables from the MAD-NG process

        Given a list of variable names, receive the variables from the MAD-NG process.

        Args:
          *names (str): The name(s) of variables that you would like to receive from MAD-NG.

        Returns:
          See :meth:`recv`.
        """
        return self.__process.recv_vars(*names)

    # -------------------------------------------------------------------------------------------------------------#

    def load(self, module: str, *vars: str):
        """Import modules into the MAD-NG environment

        Retrieve the classes in MAD-NG from the module ``module``, while only importing the classes in the variable length list ``vars``.
        If no string is provided, it is assumed that you would like to import every class from the module.

        For example, ``mad.load("MAD.gmath")`` imports all variables from the module ``MAD.gmath``.
        But ``mad.load("MAD", "matrix", "cmatrix")```` only imports the modules ``matrix`` and ``cmatrix`` from the module ``MAD.gmath``.

        Args:
          module (str): The name of the module to import from.
          *vars (str): Variable length argument list of the variable(s) to import from module.
        """
        script = ""
        if vars == ():
            vars = [x.strip("()") for x in dir(self.__get_mad_ref(module))]
        for className in vars:
            script += f"""{className} = {module}.{className}\n"""
        self.__process.send(script)

    def loadfile(self, path: str | Path, *vars: str):
        """Load a .mad file into the MAD-NG environment.

        If ``vars`` is not provided, this is equivalent to ``assert(loadfile(path))`` in MAD-NG.
        If ``vars`` is provided, for each ``var`` in ``vars``, this is equivalent to ``var = require(path).var`` in MAD-NG.

        Args:
          path (str | Path): The path to the file to import.
          *vars (str): Variable length argument list of the variable(s) to import from the file.
        """
        path: Path = Path(path).resolve()
        if vars == ():
            self.__process.send(
                f"assert(loadfile('{path}', nil, {self.py_name}._env))()"
            )
        else:
            # The parent/stem is necessary, otherwise the file will not be found
            # This is thanks to the way the require function works in MAD-NG (how it searches for files)
            script = f"package.path = '{path.parent}/?.mad;' .. package.path\n"
            script += f"local __req = require('{path.stem}')"
            for var in vars:
                script += f"{var} = __req.{var}\n"
            self.__process.send(script)

    # ----------------------- Make the class work with dict and dot access ------------------------#
    def __getattr__(self, item):
        if is_private(item):
            raise AttributeError(item)
        return self.__process.recv_vars(item)

    def __setitem__(self, var_name: str, var: Any) -> None:
        if not isinstance(var_name, tuple):
            var_name = (var_name,)
            var = (var,)
        if len(var) != len(var_name):
            raise ValueError(
                "Incorrect number of values to unpack, received",
                len(var),
                "variables and",
                len(var_name),
                "keys",
            )
        self.__process.send_vars(**dict(zip(var_name, var)))

    def __getitem__(self, var_name: str) -> Any:
        if isinstance(var_name, tuple):
            return self.__process.recv_vars(*var_name)
        else:
            return self.__process.recv_vars(var_name)

    # ----------------------------------------------------------------------------------------------#

    def eval(self, input: str) -> Any:
        """Evaluate an expression in MAD and return the result.

        Args:
          input (str): An expression that would like to be evaluated in MAD-NG.

        Returns:
          The evaluated result.
        """
        rtrn = self.__get_mad_reflast()
        self.send(f"{rtrn._name} =" + input)
        return rtrn.eval()

    def evaluate_in_madx_environment(self, input: str) -> None:
        """Open the MAD-X environment in MAD-NG and directly send code.

        Args:
          input (str): The code that would like to be evaluated in the MAD-X environment in MAD-NG.
        """
        self.__process.send("MADX:open_env()\n" + input + "\nMADX:close_env()")

    def quote_strings(self, input: str | list[str]) -> str | list[str]:
        """Add ' to either side of a string or each string in a list of strings.

        Args:
          input(str/list[str]): The string(s) that you would like to add ' either side to each string.

        Returns:
          A string or list of strings with ' placed at the beginning and the end of each string.
        """
        if isinstance(input, list):
            return ["'" + x + "'" for x in input]
        else:
            return "'" + input + "'"

    # ----------------------------------------------------------------------------------------------#

    # ---------------------------------------------------------------------------------------------------#

    def create_deferred_expression(self, **kwargs) -> mad_high_level_last_ref:
        """Create a deferred expression object

        For the deferred expression object, the kwargs are used as the deffered expressions, with ``=`` replaced
        with ``:=``. To assign the returned object a name, then use ``mad['name'] = mad.deffered(kwargs)``.

        Args:
          **kwargs: A variable list of keyword arguments, keyword as the name of the deffered expression within the object and the value as a string that is sent directly to the MAD-NG environment.

        Returns:
          A reference to the deffered expression object.
        """
        rtrn = self.__get_mad_reflast()
        kwargs_string, vars_to_send = format_kwargs_to_string(self.py_name, **kwargs)
        self.__process.send(
            f"{rtrn._name} = __mklast__( MAD.typeid.deferred {{ {kwargs_string.replace('=', ':=')[1:-3]} }} )"
        )
        for var in vars_to_send:
            self.send(var)
        return rtrn

    def __dir__(self) -> Iterable[str]:
        pyObjs = [x for x in super(MAD, self).__dir__() if x[0] != "_"]
        pyObjs.extend(self.globals())
        pyObjs.extend(dir(self.recv_vars("_G")))
        return pyObjs

    def globals(self) -> list[str]:
        """Retreive the list of names of variables in the environment of MAD

        Returns:
          A list of strings indicating the globals variables and modules within the MAD-NG environment
        """
        return dir(self.__process.recv_vars(f"{self.py_name}._env"))

    def history(self) -> str:
        """Retrieve the history of strings that have been sent to MAD-NG

        Returns:
          A string containing the history of commands that have been sent to MAD-NG
        """
        # delete all lines that start py:__err and end with __err(false)\n
        history = self.__process.history
        history = history.split("\n")
        history = [x for x in history[2:] if "py:__err" not in x]
        return "\n".join(history)

    # -------------------------------For use with the "with" statement-----------------------------------#
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.__process.close()

    # ---------------------------------------------------------------------------------------------------#
