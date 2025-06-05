from __future__ import annotations

import os
import select
import signal
import struct
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any, TYPE_CHECKING, TextIO
from contextlib import suppress

import numpy as np

if TYPE_CHECKING:
    from collections.abc import Callable

# TODO: look at cpymad for the suppression of the error messages at exit - copy? (jgray 2024)


def is_private(varname):
    """Check if the variable name is considered private.
    
    Args:
        varname (str): The variable name to check.
        
    Returns:
        bool: True if the variable name is private, False otherwise.
    """
    assert isinstance(varname, str), "Variable name to receive must be a string"
    if varname[0] == "_" and varname[:6] != "_last[":
        return True
    return False


class mad_process:
    def __init__(
        self,
        mad_path: str | Path,
        py_name: str = "py",
        raise_on_madng_error: bool = True,
        debug: bool = False,
        stdout: str | Path | TextIO = None,
        redirect_stderr: bool = False,
    ) -> None:
        self.py_name = py_name

        # Set the error handler to be off during initialization
        self.raise_on_madng_error = False

        mad_path = Path(mad_path)
        if not mad_path.exists():
            raise FileNotFoundError(f"Could not find MAD executable at {mad_path}")

        # Create the pipes for communication
        self.mad_output_pipe, mad_write = os.pipe()
        mad_read, self.mad_input_pipe = os.pipe()

        # Open the pipes for communication to MAD (the stdin of MAD)
        self.mad_input_stream = os.fdopen(self.mad_input_pipe, "wb", buffering=0)

        # Convert stdout to a TextIO object
        if stdout is None:
            stdout = sys.stdout
        elif isinstance(stdout, str) or isinstance(stdout, Path):
            self.stdout_file = open(Path(stdout), "w")
            stdout = self.stdout_file

        # Convert stdout to a file descriptor
        try:
            stdout = stdout.fileno()
        except AttributeError as e:
            raise TypeError(
                "Stdout must be a file name, file descriptor, or an object with the fileno method"
            ) from e

        # Redirect stderr to stdout, if specified
        if redirect_stderr:
            stderr = stdout
        else:
            stderr = sys.stderr.fileno()

        # Create a chunk of code to start the process
        lua_debug_flag = "true" if debug else "false"
        startupChunk = (
            f"MAD.pymad '{py_name}' {{_dbg = {lua_debug_flag}}} :__ini({mad_write})"
        )

        if threading.current_thread() is threading.main_thread():
            self._setup_signal_handler()

        # Start the process
        self.process = subprocess.Popen(
            [str(mad_path), "-q", "-e", startupChunk],
            bufsize=0,
            stdin=mad_read,  # Set the stdin of MAD to the read end of the pipe
            stdout=stdout,  # Forward stdout
            stderr=stderr,  # Forward stderr
            pass_fds=[
                mad_write,
                stdout,
                sys.stderr.fileno(),
            ],  # Don't close these (python closes all fds by default)
        )

        # Close the ends of the pipes that are not used by the process
        os.close(mad_write)
        os.close(mad_read)

        # Create a global variable dictionary for the exec function (could be extended to include more variables)
        self.python_exec_context = {"np": np}

        # Open the pipe from MAD (this is where MAD will no longer hang)
        self.mad_read_stream = os.fdopen(self.mad_output_pipe, "rb")
        self.history = ""  # Begin the recording of the history
        self.debug = debug  # Record debug mode status

        # stdout should be line buffered by default, but for jupyter notebook,
        # stdout is redirected and not line buffered by default
        self.send("io.stdout:setvbuf('line')")

        # Check if MAD started successfully
        self.send(f"{self.py_name}:send('started')")
        startup_status_checker = select.select(
            [self.mad_read_stream], [], [], 10
        )  # May not work on windows

        # Check if MAD started successfully using select
        mad_rtrn = self.recv()
        if not startup_status_checker[0] or mad_rtrn != "started":
            self.close()
            if mad_rtrn == "started":
                raise OSError(
                    f"Could not establish communication with {mad_path} process"
                )
            else:
                raise OSError(
                    f"Could not start {mad_path} process, received: {mad_rtrn}"
                )

        # Set the error handler to be on by default
        if raise_on_madng_error:
            self.set_error_handler(True)
            self.raise_on_madng_error = True

    def _setup_signal_handler(self):
        original_sigint_handler = signal.getsignal(signal.SIGINT)

        def delete_process(sig, frame):
            self.close()
            signal.signal(signal.SIGINT, original_sigint_handler)
            raise KeyboardInterrupt("MAD process was interrupted, and has been deleted")

        signal.signal(signal.SIGINT, delete_process)

    def send_range(self, start: float, stop: float, size: int) -> None:
        """Send a linear range (numpy array) to MAD-NG.

        Constructs a numpy.linspace array based on start, stop, and size and sends it over the MAD pipe.
        """
        self.mad_input_stream.write(b"rng_")
        send_generic_range(self, start, stop, size)

    def send_logrange(self, start: float, stop: float, size: int) -> None:
        """Send a logarithmic range (numpy array) to MAD-NG.

        Builds an array equivalent to numpy.geomspace from start to stop with given size.
        """
        self.mad_input_stream.write(b"lrng")
        send_generic_range(self, start, stop, size)

    def send_tpsa(self, monos: np.ndarray, coefficients: np.ndarray) -> None:
        """Transmit TPSA data to MAD-NG.

        Sends the monomials and their corresponding coefficients to construct a TPSA table.
        """
        self.mad_input_stream.write(b"tpsa")
        send_generic_tpsa(self, monos, coefficients, send_num)

    def send_cpx_tpsa(self, monos: np.ndarray, coefficients: np.ndarray) -> None:
        """Transmit a complex TPSA to MAD-NG.

        Sends complex monomials and coefficients to MAD-NG for table creation.
        """
        self.mad_input_stream.write(b"ctpa")
        send_generic_tpsa(self, monos, coefficients, send_cpx)

    def send(self, data: str | int | float | np.ndarray | bool | list | dict) -> mad_process:
        """Send data to the MAD-NG process.

        Accepts several types (str, int, float, ndarray, bool, list, dict) and sends them using the appropriate serialization.
        Returns self to allow method chaining.
        """
        try:
            typ = type_str[get_typestr(data)]
            self.mad_input_stream.write(typ.encode("utf-8"))
            type_fun[typ]["send"](self, data)
            return self
        except KeyError:  # raise not in exception to reduce error output
            raise TypeError(
                f"Unsupported data type, expected a type in: \n{list(type_str.keys())}, got {type(data)}"
            ) from None

    def protected_send(self, string: str) -> mad_process:
        """Send a command string to MAD-NG with temporary error handling.

        If error handling is enabled, any errors in MAD-NG will be reported back.
        """
        if self.raise_on_madng_error:
            # If the user has specified that they want to raise an error always, skip the error handling on and off
            return self.send(string)
        return self.send(
            f"{self.py_name}:__err(true); {string}; {self.py_name}:__err(false);"
        )

    def protected_variable_retrieval(self, name: str, shallow_copy: bool = False) -> Any:
        """Safely retrieve a variable from MAD-NG.

        Enables temporary error handling while retrieving a variable.
        Args:
            name (str): The MAD-NG variable name to retrieve.
            shallow_copy (bool): If True, retrieves a shallow copy of the variable. This has no effect for most types, but tables in MAD-NG are sent as references by default, so if you want to retrieve a copy of the table, set this to True.
        Returns:
            The value of the variable.
        """
        shallow_copy = str(shallow_copy).lower()
        if self.raise_on_madng_error:
            return self.send(f"py:send({name}, {shallow_copy})").recv(name)
        self.send(
            f"{self.py_name}:__err(true):send({name}, {shallow_copy}):__err(false)"
        )  # Enable error handling, ask for the variable, and disable error handling
        return self.recv(name)

    def set_error_handler(self, on_off: bool) -> mad_process:
        """Toggle error handling in the MAD-NG process.

        This determines whether errors are raised immediately.
        Args:
            on_off (bool): If True, errors will be raised immediately; if False, errors will not be raised.
        Returns:
            mad_process: Returns self to allow method chaining.
        """
        if self.raise_on_madng_error:
            return  # If the user has specified that they want to raise an error always, skip the error handling on and off
        self.send(f"{self.py_name}:__err({str(on_off).lower()})")

    def recv(self, varname: str = None) -> Any:
        """Receive data from MAD-NG.

        Reads 4 bytes to detect the data type and then extracts the corresponding value.
        Optional varname is used for reference purposes.
        Args:
            varname (str): The variable name to use for reference in MAD-NG.
        Returns:
            Any: The value received from MAD-NG, which can be of various types (str, int, float, ndarray, bool, list, dict).
        """
        typ = self.mad_read_stream.read(4).decode("utf-8")
        self.varname = varname  # For mad reference
        return type_fun[typ]["recv"](self)

    def recv_and_exec(self, env: dict = {}) -> dict:
        """Receive a command string from MAD-NG and execute it.

        The execution context includes numpy as np and the mad process instance.
        Returns the updated execution environment.
        Args:
            env (dict): The environment dictionary to execute the received command in.
        Returns:
            dict: The updated environment dictionary after executing the received command.
        """
        # Check if user has already defined mad (madp_object will have mad defined), otherwise define it
        try:
            env["mad"]
        except KeyError:
            env["mad"] = self

        exec(compile(self.recv(), "ffrom_mad", "exec"), self.python_exec_context, env)
        return env

    # ----------------- Dealing with communication of variables ---------------- #
    def send_vars(self, **vars) -> mad_process:
        """Send multiple variables to MAD-NG.

        Each keyword argument becomes a variable in the MAD-NG environment.
        If a variable is a mad_ref, it is sent as its name; otherwise, the value is sent directly.
        Args:
            **vars: Keyword arguments representing variable names and their values.
        Returns:
            mad_process: Returns self to allow method chaining.
        """
        for name, var in vars.items():
            if isinstance(var, mad_ref):
                self.send(f"{name} = {var._name}")
            else:
                self.send(f"{name} = {self.py_name}:recv()").send(var)

    def recv_vars(self, *names, shallow_copy: bool = False) -> Any:
        """Receive one or multiple variables from MAD-NG.

        For a single variable (excluding internal names) a direct value is returned.
        For multiple variables, a tuple of values is returned.
        Args:
            *names: Variable names to retrieve from MAD-NG.
            shallow_copy (bool): If True, retrieves a shallow copy of the variable. This has no effect for most types, but tables in MAD-NG are sent as references by default, so if you want to retrieve a copy of the table, set this to True.
        Returns:
            Any: The value of the variable if a single name is provided, or a tuple of values if multiple names are provided.
        """
        if len(names) == 1:
            if not is_private(names[0]):
                return self.protected_variable_retrieval(names[0], shallow_copy)
        else:
            return tuple(
                self.protected_variable_retrieval(name, shallow_copy)
                for name in names
                if not is_private(name)
            )

    # -------------------------------------------------------------------------- #

    def close(self) -> None:
        """Terminate the MAD-NG process.

        Closes all communication pipes and waits for the subprocess to finish.
        """
        if self.process.poll() is None:  # If process is still running
            self.send(f"{self.py_name}:__fin()")  # Tell the mad side to finish
            open_pipe = select.select([self.mad_read_stream], [], [])
            if open_pipe[0]:
                # Wait for the mad side to finish (variable name in case of errors that need to be caught elsewhere)
                close_msg = self.recv("closing")
                if close_msg != "<closing pipe>":
                    Warning(
                        f"Unexpected message received: {close_msg}, MAD-NG may not have completed properly"
                    )
            self.process.terminate()  # Terminate the process on the python side

        # Close the debug file if it exists
        with suppress(AttributeError):
            self.stdout_file.close()

        # Close the pipes
        if not self.mad_read_stream.closed:
            self.mad_read_stream.close()
        if not self.mad_input_stream.closed:
            self.mad_input_stream.close()

        # Wait for the process to finish
        self.process.wait()

    def __del__(self):
        """Destructor: Close the MAD process gracefully."""
        self.close()


class mad_ref(object):
    """A reference to a variable in MAD-NG.
    This class allows for the retrieval of variables from MAD-NG without
    having to send them explicitly.
    """
    def __init__(self, name: str, mad_proc: mad_process):
        assert name is not None, (
            "Reference must have a variable to reference to."
            "Did you forget to put a name in the receive functions?"
        )
        self._name = name
        self._mad = mad_proc

    def __getattr__(self, item):
        """Retrieve attribute corresponding to a variable in MAD-NG.
        
        Args:
            item (str): The attribute name.
        
        Returns:
            Any: The value of the variable in MAD-NG.
        
        Raises:
            AttributeError: If the attribute is not found.
        """
        if not is_private(item):
            try:
                return self[item]
            except (IndexError, KeyError):
                pass
        raise AttributeError(item)  # For python

    def __getitem__(self, item: str | int):
        """Retrieve item from MAD-NG using indexing.
        
        Args:
            item (str | int): The key or index.
        
        Returns:
            Any: The value corresponding to the item.
        
        Raises:
            IndexError: If the index is out of range.
            KeyError: If the key is not present.
            TypeError: If the item type is not valid.
        """
        if isinstance(item, int):
            result = self._mad.protected_variable_retrieval(f"{self._name}[{item + 1}]")
            if result is None:
                raise IndexError(item)  # For python
        elif isinstance(item, str):
            result = self._mad.protected_variable_retrieval(f"{self._name}['{item}']")
            if result is None:
                raise KeyError(item)  # For python
        else:
            raise TypeError("Cannot index type of ", type(item))

        return result

    def eval(self) -> Any:
        """Evaluate the reference and return the value."""
        return self._mad.recv_vars(self._name, shallow_copy=True)


# data transfer -------------------------------------------------------------- #


# Data ----------------------------------------------------------------------- #
def write_serial_data(self: mad_process, dat_fmt: str, *dat: Any) -> int:
    """Write data to the MAD-NG pipe in a specific format."

    Args:
        dat_fmt (str): The format string for struct.pack.
        *dat: The data to be packed and written.

    Returns:
        int: The number of bytes written to the MAD-NG input stream.
    """
    return self.mad_input_stream.write(struct.pack(dat_fmt, *dat))


def read_data_stream(self: mad_process, dat_sz: int, dat_typ: np.dtype) -> np.ndarray:
    """Read data from the MAD-NG pipe in a specific format.
    
    Args:
        dat_sz (int): The size of the data to read.
        dat_typ (np.dtype): The data type for numpy conversion.

    Returns:
        np.ndarray: The data read from the MAD-NG input stream, converted to the specified numpy type.
    """
    return np.frombuffer(self.mad_read_stream.read(dat_sz), dtype=dat_typ)


# None ----------------------------------------------------------------------- #
def send_nil(self: mad_process, input):
    """Send a nil value to MAD-NG.

    This is a placeholder function as nil is not sent down the pipe, but rather
    the sending of the type is used to tell MAD-NG that the value is nil.
    The function is included for consistency with the other send functions.

    Args:
        self (mad_process): The MAD-NG process instance.
        input: The input value (not used).

    Returns:
        None: No value is sent, but the function is included for consistency.
    """
    return None


def recv_nil(self: mad_process):
    """Receive a nil value from MAD-NG.
    
    This is a placeholder function as nil is not sent down the pipe, but rather
    the receiving of the type is used to tell MAD-NG that the value is nil.
    
    Args:
        self (mad_process): The MAD-NG process instance.
        
    Returns:
        None: No value is received.
    """
    return None


# Boolean -------------------------------------------------------------------- #
def send_bool(self: mad_process, input: bool) -> int:
    """Write a boolean value to the MAD-NG pipe.

    Args:
        self (mad_process): The MAD-NG process instance.
        input (bool): The boolean value to send.

    Returns:
        int: The number of bytes written to the MAD-NG input stream.
    """
    return self.mad_input_stream.write(struct.pack("?", input))


def recv_bool(self: mad_process) -> bool:
    """Read a boolean value from the MAD-NG pipe.
    
    Args:
        self (mad_process): The MAD-NG process instance.

    Returns:
        bool: The boolean value received from MAD-NG.
    """
    return read_data_stream(self, 1, np.bool_)[0]


# int32 ---------------------------------------------------------------------- #
def send_int(self: mad_process, input: int) -> int:
    """Send a 32-bit integer to the MAD-NG pipe.

    Args:
        self (mad_process): The MAD-NG process instance.
        input (int): The integer value to send.

    Returns:
        int: The number of bytes written to the MAD-NG input stream.
    """
    return write_serial_data(self, "i", input)


def recv_int(self: mad_process) -> int:
    """Receive a 32-bit integer from the MAD-NG pipe.

    Args:
        self (mad_process): The MAD-NG process instance.

    Returns:
        int: The integer value received from MAD-NG.
    """
    return read_data_stream(self, 4, np.int32)[0]


# String --------------------------------------------------------------------- #
def send_str(self: mad_process, input: str) -> int:
    """Send a string to the MAD-NG pipe.
    
    Args:
        self (mad_process): The MAD-NG process instance.
        input (str): The string value to send.

    Returns:
        int: The number of bytes written to the MAD-NG input stream.
    """
    # Only store history if debug mode is enabled
    if getattr(self, "debug", False):
        self.history += input + "\n"
    send_int(self, len(input))
    return self.mad_input_stream.write(input.encode("utf-8"))


def recv_str(self: mad_process) -> str:
    """Receive a string from the MAD-NG pipe.

    Args:
        self (mad_process): The MAD-NG process instance.

    Returns:
        str: The string value received from MAD-NG.
    """
    res = self.mad_read_stream.read(recv_int(self)).decode("utf-8")
    return res


# number (in lua, float64 in python) ----------------------------------------- #
def send_num(self: mad_process, input: float) -> int:
    """Send a 64-bit float to the MAD-NG pipe.

    Args:
        self (mad_process): The MAD-NG process instance.
        input (float): The float value to send.
    
    Returns:
        int: The number of bytes written to the MAD-NG input stream.
    """
    return write_serial_data(self, "d", input)


def recv_num(self: mad_process) -> np.float64:
    """Receive a 64-bit float from the MAD-NG pipe.

    Args:
        self (mad_process): The MAD-NG process instance.
    
    Returns:
        np.float64: The float value received from MAD-NG.
    """
    return read_data_stream(self, 8, np.float64)[0]


# Complex (complex128) ------------------------------------------------------- #
def send_cpx(self: mad_process, input: complex) -> int:
    """Send a complex number to the MAD-NG pipe.
    
    Args:
        self (mad_process): The MAD-NG process instance.
        input (complex): The complex number to send.

    Returns:
        int: The number of bytes written to the MAD-NG input stream.
    """
    return write_serial_data(self, "dd", input.real, input.imag)


def recv_cpx(self: mad_process) -> complex:
    """Receive a complex number from the MAD-NG pipe.
    
    Args:
        self (mad_process): The MAD-NG process instance.
    
    Returns:
        complex: The received complex number.
    """
    return read_data_stream(self, 16, np.complex128)[0]


# Range ---------------------------------------------------------------------- #
def send_generic_range(self, start: float, stop: float, size: int):
    """Send a generic range to MAD-NG.
    
    Args:
        self (mad_process): The MAD-NG process instance.
        start (float): The starting value of the range.
        stop (float): The ending value of the range.
        size (int): The number of points in the range.
    
    Returns:
        None
    """
    write_serial_data(self, "ddi", start, stop, size)


def recv_range(self: mad_process) -> np.ndarray:
    """Receive a linear range from the MAD-NG pipe.
    
    Returns:
        np.ndarray: The range as a numpy array.
    """
    return np.linspace(*struct.unpack("ddi", self.mad_read_stream.read(20)))


def recv_logrange(self: mad_process) -> np.ndarray:
    """Receive a logarithmic range from the MAD-NG pipe.
    
    Returns:
        np.ndarray: The logarithmic range as a numpy array.
    """
    return np.geomspace(*struct.unpack("ddi", self.mad_read_stream.read(20)))


# irange --------------------------------------------------------------------- #
def send_int_range(self: mad_process, rng: range):
    """Send an integer range to the MAD-NG pipe.
    
    Args:
        self (mad_process): The MAD-NG process instance.
        rng (range): The range object to send.
    
    Returns:
        int: The number of bytes written.
    """
    return write_serial_data(self, "iii", rng.start, rng.stop, rng.step)


def recv_int_range(self: mad_process) -> range:
    """Receive an inclusive integer range from the MAD-NG pipe.
    
    Returns:
        range: The received range, inclusive of both ends.
    """
    start, stop, step = read_data_stream(self, 12, np.int32)
    return range(start, stop + 1, step)  # MAD is inclusive at both ends


# matrix --------------------------------------------------------------------- #
def send_generic_matrix(self: mad_process, mat: np.ndarray):
    """Send a 2D matrix to MAD-NG.
    
    Args:
        self (mad_process): The MAD-NG process instance.
        mat (np.ndarray): A 2-dimensional numpy array to send.
    
    Returns:
        None
    """
    assert len(mat.shape) == 2, "Matrix must be of two dimensions"
    write_serial_data(self, "ii", *mat.shape)
    self.mad_input_stream.write(mat.tobytes())


def recv_generic_matrix(self: mad_process, dtype: np.dtype) -> str:
    """Receive a generic matrix from the MAD-NG pipe.
    
    Args:
        self (mad_process): The MAD-NG process instance.
        dtype (np.dtype): The numpy data type of the matrix.
    
    Returns:
        str: A string representation of the matrix (reshaped numpy array).
    """
    shape = read_data_stream(self, 8, np.int32)
    return read_data_stream(self, shape[0] * shape[1] * dtype.itemsize, dtype).reshape(
        shape
    )


def recv_matrix(self: mad_process) -> np.ndarray:
    """Receive a matrix of 64-bit floats from the MAD-NG pipe.
    
    Returns:
        np.ndarray: The received matrix.
    """
    return recv_generic_matrix(self, np.dtype("float64"))


def recv_cpx_matrix(self: mad_process) -> np.ndarray:
    """Receive a matrix of complex numbers from the MAD-NG pipe.
    
    Returns:
        np.ndarray: The received complex matrix.
    """
    return recv_generic_matrix(self, np.dtype("complex128"))


def recv_int_matrix(self: mad_process) -> np.ndarray:
    """Receive a matrix of 32-bit integers from the MAD-NG pipe.
    
    Returns:
        np.ndarray: The received integer matrix.
    """
    return recv_generic_matrix(self, np.dtype("int32"))


# monomial ------------------------------------------------------------------- #
def send_monomial(self: mad_process, mono: np.ndarray):
    """Send a monomial to MAD-NG.
    
    Args:
        self (mad_process): The MAD-NG process instance.
        mono (np.ndarray): A numpy array representing the monomial.
    
    Returns:
        None
    """
    send_int(self, mono.size)
    self.mad_input_stream.write(mono.tobytes())


def recv_monomial(self: mad_process) -> np.ndarray:
    """Receive a monomial from MAD-NG.
    
    Returns:
        np.ndarray: The received monomial as an array of 8-bit unsigned integers.
    """
    return read_data_stream(self, recv_int(self), np.ubyte)


# TPSA ----------------------------------------------------------------------- #
def send_generic_tpsa(
    self: mad_process,
    monos: np.ndarray,
    coefficients: np.ndarray,
    send_num: Callable[[mad_process, float | complex], None],
):
    """Send a generic TPSA table to MAD-NG.
    
    Args:
        self (mad_process): The MAD-NG process instance.
        monos (np.ndarray): 2D array of monomials (must be uint8).
        coefficients (np.ndarray): Array of coefficients corresponding to the monomials.
        send_num (Callable): The function to send a numeric (float or complex) value.
    
    Returns:
        None
    """
    assert len(monos.shape) == 2, "The list of monomials must have two dimensions"
    assert len(monos) == len(coefficients), (
        "The number of monomials must be equal to the number of coefficients"
    )
    assert monos.dtype == np.uint8, (
        "The monomials must be of type 8-bit unsigned integer "
    )
    write_serial_data(self, "ii", len(monos), len(monos[0]))
    for mono in monos:
        self.mad_input_stream.write(mono.tobytes())
    for coefficient in coefficients:
        send_num(self, coefficient)


def recv_generic_tpsa(self: mad_process, dtype: np.dtype) -> np.ndarray:
    """Receive a generic TPSA table from MAD-NG.
    
    Args:
        self (mad_process): The MAD-NG process instance.
        dtype (np.dtype): The numeric data type for coefficients.
    
    Returns:
        np.ndarray: A tuple (monomial list, coefficients array).
    """
    num_mono, mono_len = read_data_stream(self, 8, np.int32)
    mono_list = np.reshape(
        read_data_stream(self, mono_len * num_mono, np.ubyte),
        (num_mono, mono_len),
    )
    coefficients = read_data_stream(self, num_mono * dtype.itemsize, dtype)
    return mono_list, coefficients


def recv_cpx_tpsa(self: mad_process):
    """Receive a complex TPSA table from the MAD-NG pipe.
    
    Returns:
        tuple: A tuple containing the monomial list and coefficients.
    """
    return recv_generic_tpsa(self, np.dtype("complex128"))


def recv_dbl_tpsa(self: mad_process):
    """Receive a double TPSA table from the MAD-NG pipe.
    
    Returns:
        tuple: A tuple containing the monomial list and coefficients.
    """
    return recv_generic_tpsa(self, np.dtype("float64"))


# lists ---------------------------------------------------------------------- #
# Lists of strings are really slow to send, is there a way to improve this? (jgray 2024)
def send_list(self: mad_process, lst: list):
    """Send a list to the MAD-NG pipe.
    
    Args:
        self (mad_process): The MAD-NG process instance.
        lst (list): The list to send.
    
    Returns:
        None
    """
    send_int(self, len(lst))
    for item in lst:
        self.send(item)


def recv_list(self: mad_process) -> list:
    """Receive a list from the MAD-NG pipe.
    
    Returns:
        list: The received list.
    """
    varname = self.varname  # cache
    lstLen = recv_int(self)
    vals = [self.recv(varname and varname + f"[{i + 1}]") for i in range(lstLen)]
    self.varname = varname  # reset
    return vals

def send_dict(self: mad_process, dct: dict):
    """Send a dictionary to the MAD-NG pipe.
    
    Args:
        self (mad_process): The MAD-NG process instance.
        dct (dict): The dictionary to send.
    
    Returns:
        int: The number of bytes written to the MAD-NG input stream.

    Raises:
        ValueError: If a key in the dictionary is None, as nil keys are not allowed in Lua.
    """
    for key, value in dct.items():
        if key is None:
            self.send(None) # Stop the communication of the dictionary to MAD-NG
            raise ValueError("nil key in a dictionary is not allowed in lua, remove the key None from the dictionary")
        self.send(key)
        self.send(value)
    self.send(None)

def recv_dict(self: mad_process) -> dict:
    """Receive a dictionary from the MAD-NG pipe.
    
    Returns:
        dict: The received dictionary.
    """
    varname = self.varname  # cache
    dct = {}
    while True:
        key = self.recv()
        if key is None:  # End of dictionary
            break
        if isinstance(key, np.int32):
            key = int(key)
        value = self.recv(varname and f"{varname}['{key}']")
        dct[key] = value
    self.varname = varname  # reset
    return dct


# object (table with metatable are treated as pure reference) ---------------- #
def recv_reference(self: mad_process):
    """Receive a reference to an object from MAD-NG.
    
    Returns:
        mad_ref: A reference object corresponding to the received variable.
    """
    return mad_ref(self.varname, self)


def send_reference(self, obj: mad_ref):
    """Send a reference to an object in MAD-NG.
    
    Args:
        self (mad_process): The MAD-NG process instance.
        obj (mad_ref): The reference object to send.
    
    Returns:
        int: The number of bytes written to the MAD-NG input stream.
    """
    return send_str(self, f"return {obj._name}")


# error ---------------------------------------------------------------------- #
def recv_err(self: mad_process):
    """Receive an error message from MAD-NG and raise an exception.
    
    Args:
        self (mad_process): The MAD-NG process instance.
    
    Raises:
        RuntimeError: Always raised with the error message from MAD-NG.
    """
    self.set_error_handler(False)
    raise RuntimeError("MAD Errored (see the MAD error output)")


# ---------------------------- dispatch tables ------------------------------- #
type_fun = {
    "nil_": {"recv": recv_nil, "send": send_nil},
    "bool": {"recv": recv_bool, "send": send_bool},
    "str_": {"recv": recv_str, "send": send_str},
    "lst_": {"recv": recv_list, "send": send_list},
    "dct_": {"recv": recv_dict, "send": send_dict},
    "ref_": {"recv": recv_reference, "send": send_reference},
    "fun_": {"recv": recv_reference, "send": send_reference},
    "obj_": {"recv": recv_reference, "send": send_reference},
    "int_": {"recv": recv_int, "send": send_int},
    "num_": {"recv": recv_num, "send": send_num},
    "cpx_": {"recv": recv_cpx, "send": send_cpx},
    "mat_": {"recv": recv_matrix, "send": send_generic_matrix},
    "cmat": {"recv": recv_cpx_matrix, "send": send_generic_matrix},
    "imat": {"recv": recv_int_matrix, "send": send_generic_matrix},
    "rng_": {"recv": recv_range},
    "lrng": {"recv": recv_logrange},
    "irng": {"recv": recv_int_range, "send": send_int_range},
    "mono": {"recv": recv_monomial, "send": send_monomial},
    "tpsa": {"recv": recv_dbl_tpsa},
    "ctpa": {"recv": recv_cpx_tpsa},
    "err_": {"recv": recv_err},
    "": {"recv": BrokenPipeError},
}


def get_typestr(
    a: str | int | float | np.ndarray | bool | list | dict | tuple | range | mad_ref,
) -> type:
    """Determine the type string for the given input.
    
    Args:
        a: The data for which to determine the type.
    
    Returns:
        type: The corresponding type used for serialization.
    """
    if isinstance(a, np.ndarray):
        return a.dtype
    elif type(a) is int:  # Check for signed 32 bit int
        if a.bit_length() < 31:
            return int
        else:
            return float
    else:
        return type(a)


type_str = {
    type(None): "nil_",
    bool: "bool",
    str: "str_",
    list: "lst_",
    dict: "dct_",
    tuple: "lst_",
    mad_ref: "ref_",
    int: "int_",
    np.int32: "int_",
    float: "num_",
    np.float64: "num_",
    complex: "cpx_",
    np.complex128: "cpx_",
    range: "irng",
    np.dtype("float64"): "mat_",
    np.dtype("complex128"): "cmat",
    np.dtype("int32"): "imat",
    np.dtype("ubyte"): "mono",
}
# ---------------------------------------------------------------------------- #
