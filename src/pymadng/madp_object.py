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
        redirect_stderr: bool = False,
        num_temp_vars: int = 8,
        ipython_use_jedi: bool = False,
    ):
        """
        Initialise a MAD object for communication with MAD-NG.

        This constructor starts the MAD subprocess, establishes communication pipes,
        and imports necessary MAD modules. The mad_path defaults to a bundled executable if not provided.

        Args:
            mad_path (str | Path, optional): Path to the MAD executable.
            py_name (str, optional): Name used for MAD-to-Python communication.
            raise_on_madng_error (bool, optional): If True, raises errors from MAD-NG immediately.
            debug (bool, optional): If True, enables detailed debugging output.
            stdout (TextIO | str | Path, optional): Destination for MAD-NG's standard output.
            redirect_stderr (bool, optional): If True, redirects stderr to stdout.
            num_temp_vars (int, optional): Maximum number of temporary variables to track.
            ipython_use_jedi (bool, optional): If True, allows IPython to use jedi for autocompletion.
        """
        # ------------------------- Create the process --------------------------- #
        mad_path = mad_path or bin_path / ("mad_" + platform.system())
        self.__process = mad_process(
            mad_path=mad_path,
            py_name=py_name,
            raise_on_madng_error=raise_on_madng_error,
            debug=debug,
            stdout=stdout,
            redirect_stderr=redirect_stderr,
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
        """
        Retrieve data from the MAD-NG process.

        Reads a data type identifier and then receives the corresponding value from MAD-NG.

        Args:
            varname (str, optional): Variable name used for clarity when receiving references.

        Returns:
            The value received from MAD-NG.
        """
        return self.__process.recv(varname)

    def receive(
        self, varname: str = None
    ) -> str | int | float | np.ndarray | bool | list | high_level_mad_ref:
        """
        Alias for the recv method.

        Args:
            varname (str, optional): Name of the variable to receive.

        Returns:
            The received data.
        """
        return self.__process.recv(varname)

    def recv_and_exec(self, context: dict = {}) -> dict:
        """
        Receive a string from MAD-NG and execute it.

        The provided execution context is updated with numpy (np) and the current MAD object.

        Args:
            context (dict, optional): The environment for executing the received code.

        Returns:
            dict: The updated execution environment.
        """
        context["mad"] = self
        return self.__process.recv_and_exec(context)

    # --------------------------------Sending data to subprocess------------------------------------#
    def send(self, data: str | int | float | np.ndarray | bool | list) -> MAD:
        """
        Send data to MAD-NG.

        Accepts various types of data and serialises them for transfer to MAD-NG.

        Args:
            data (str/int/float/np.ndarray/bool/list): The information to send.

        Returns:
            MAD: Returns self to facilitate method chaining.
        """
        self.__process.send(data)
        return self

    def protected_send(self, string: str) -> MAD:
        """
        Send a command to MAD-NG with error protection.

        Temporarily enables error handling so that any command errors in MAD-NG are caught and raised in Python.

        Args:
            string (str): The MAD-NG command code to send.

        Returns:
            MAD: Self for method chaining.
        """
        assert isinstance(string, str), "The input to protected_send must be a string"
        self.__process.protected_send(string)
        return self

    def psend(self, string: str) -> MAD:
        """Alias for protected_send"""
        return self.protected_send(string)

    def send_range(self, start: float, stop: float, size: int):
        """
        Send a linear range to MAD-NG.

        Builds a range analogous to numpy.linspace and sends it based on the specified boundaries and size.

        Args:
            start (float): The starting value of the range.
            stop (float): The ending value of the range (inclusive).
            size (int): The total number of elements in the range.
        """
        self.__process.send_range(start, stop, size)

    def send_logrange(self, start: float, stop: float, size: int):
        """
        Send a logarithmic range to MAD-NG.

        Generates and sends a logarithmic range equivalent to numpy.geomspace.

        Args:
            start (float): The start value.
            stop (float): The stop value.
            size (int): The number of points in the range.
        """
        self.__process.send_logrange(start, stop, size)

    def send_tpsa(self, monos: np.ndarray, coefficients: np.ndarray):
        """
        Transmit TPSA data for processing in MAD-NG.

        Sends a two-dimensional array of monomials and the associated coefficient array.

        Args:
            monos (np.ndarray): 2D array containing the monomials.
            coefficients (np.ndarray): Array of TPSA coefficients.
        """
        self.__process.send_tpsa(monos, coefficients)

    def send_cpx_tpsa(self, monos: np.ndarray, coefficients: np.ndarray):
        """
        Transmit complex TPSA data to MAD-NG.

        Sends complex-valued monomials and coefficients for TPSA table construction.

        Args:
            monos (np.ndarray): 2D array of monomials (unsigned bytes).
            coefficients (np.ndarray): Array of complex TPSA coefficients.
        """
        self.__process.send_cpx_tpsa(monos, coefficients)

    # ---------------------------------------------------------------------------------------------------------#

    # -------------------------------- Dealing with communication of variables --------------------------------#
    def send_vars(self, **vars: str | int | float | np.ndarray | bool | list):
        """
        Send multiple named variables to the MAD-NG process.

        Each keyword pair becomes a variable in the MAD-NG environment.

        Args:
            **vars: Key-value pairs representing variable names and their values.
        """
        self.__process.send_vars(**vars)

    def recv_vars(self, *names: str, shallow_copy: bool = False) -> Any:
        """
        Retrieve one or more variables from MAD-NG.

        Args:
            *names (str): The names of the variables to be fetched from MAD-NG.
            shallow_copy (bool, optional): If True, returns a shallow copy of the variables.

        Returns:
            The retrieved variable value or a tuple of values if multiple names are provided.
        """
        return self.__process.recv_vars(*names, shallow_copy=shallow_copy)

    # -------------------------------------------------------------------------------------------------------------#

    def load(self, module: str, *vars: str):
        """
        Import classes or functions from a specific MAD-NG module.

        If no specific names are provided, imports all available members from the module.

        Args:
            module (str): The module name in MAD-NG.
            *vars (str): Optional list of members to import.
        """
        script = ""
        if vars == ():
            vars = [x.strip("()") for x in dir(self.__get_mad_ref(module))]
        for className in vars:
            script += f"""{className} = {module}.{className}\n"""
        self.__process.send(script)

    def loadfile(self, path: str | Path, *vars: str):
        """
        Load and execute a .mad file in the MAD-NG environment.

        If additional variable names are provided, assign each to the corresponding member of the loaded file.

        Args:
            path (str | Path): File path for the .mad file.
            *vars (str): Optional names to bind to specific elements from the file.
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
        """
        Retrieve a MAD-NG variable using attribute access.

        Args:
            item (str): The name of the variable to retrieve.

        Returns:
            The value of the MAD-NG variable.
        """
        if is_private(item):
            raise AttributeError(item)
        return self.__process.recv_vars(item)

    def __setitem__(self, var_name: str, var: Any) -> None:
        """
        Set one or more variables in the MAD-NG process via item assignment.

        Args:
            var_name (str): The name(s) of the variable(s).
            var (Any): The value(s) to assign.

        Raises:
            ValueError: If the number of names does not match the number of values.
        """
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
        """
        Retrieve one or more variables from MAD-NG using item access.

        Args:
            var_name (str): The name or tuple of names of variables.

        Returns:
            The corresponding variable value(s) from MAD-NG.
        """
        if isinstance(var_name, tuple):
            return self.__process.recv_vars(*var_name)
        else:
            return self.__process.recv_vars(var_name)

    # ----------------------------------------------------------------------------------------------#

    def eval(self, expression: str) -> Any:
        """
        Evaluate an expression in the MAD-NG environment.

        Args:
            expression (str): The expression to evaluate.

        Returns:
            Any: The result of the evaluated expression.
        """
        rtrn = self.__get_mad_reflast()
        self.send(f"{rtrn._name} = {expression}")
        return rtrn.eval()

    def evaluate_in_madx_environment(self, input: str) -> None:
        """
        Execute code in the native MAD-X environment.

        Opens a MAD-X environment, sends the code, and then closes the environment.

        Args:
            input (str): The MAD-X code to execute.
        """
        self.__process.send("MADX:open_env()\n" + input + "\nMADX:close_env()")

    def quote_strings(self, input: str | list[str]) -> str | list[str]:
        """
        Surround the provided string or list of strings with single quotes.

        Args:
            input (str or list[str]): The input string(s) to quote.

        Returns:
            The quoted string or list of quoted strings.
        """
        if isinstance(input, list):
            return ["'" + x + "'" for x in input]
        else:
            return "'" + input + "'"

    # ----------------------------------------------------------------------------------------------#

    # ---------------------------------------------------------------------------------------------------#

    def create_deferred_expression(self, **kwargs) -> mad_high_level_last_ref:
        """
        Create a deferred expression object in MAD-NG.

        The keyword arguments represent deferred expressions using ':=' syntax.
        Intended for assigning a temporary variable that holds a lazy-evaluated result.

        Args:
            **kwargs: Expression name-value pairs.

        Returns:
            mad_high_level_last_ref: A reference to the deferred expression.
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
        pyObjs.extend(dir(self.recv_vars("_G", shallow_copy=True)))
        return pyObjs

    def globals(self) -> list[str]:
        """
        Retrieve a list of all global variable names in the MAD-NG environment.

        Returns:
            list[str]: A list containing the names of global variables.
        """
        return dir(self.__process.recv_vars(f"{self.py_name}._env", shallow_copy=True))

    def history(self) -> str:
        """
        Retrieve the command history sent to MAD-NG.

        Filters out internal error-handling commands.

        Returns:
            str: A newline-separated string of historical commands.
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
