from __future__ import annotations

import os
import select
import signal
import struct
import subprocess
import sys
from pathlib import Path
from typing import Any, TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ["mad_process"]


def is_private(varname):
    assert isinstance(varname, str), "Variable name to receive must be a string"
    if varname[0] == "_" and varname[:6] != "_last[":
        return True
    return False


class mad_process:
    def __init__(
        self,
        mad_path: str | Path,
        py_name: str = "py",
        debug: int | str | Path | bool = False,
    ) -> None:
        self.py_name = py_name

        mad_path = Path(mad_path)
        if not mad_path.exists():
            raise FileNotFoundError(f"Could not find MAD executable at {mad_path}")

        # Create the pipes for communication
        self.mad_output_pipe, mad_write = os.pipe()
        mad_read, self.mad_input_pipe = os.pipe()

        # Open the pipes for communication to MAD (the stdin of MAD)
        self.mad_input_stream = os.fdopen(self.mad_input_pipe, "wb", buffering=0)

        if isinstance(debug, str) or isinstance(debug, Path):
            debug = Path(debug)
            self.debug_file = open(debug, "w")
            stdout = self.debug_file.fileno()
        elif isinstance(debug, bool):
            stdout = sys.stdout.fileno()
        elif isinstance(debug, int):
            stdout = debug
        else:
            raise TypeError("Debug must be a file name, file descriptor or a boolean")

        # Create a chunk of code to start the process
        startupChunk = f"MAD.pymad '{py_name}' {{_dbg = {str(bool(debug)).lower()}}} :__ini({mad_write})"
        original_sigint_handler = signal.getsignal(signal.SIGINT)

        def delete_process(sig, frame):
            self.close()
            signal.signal(signal.SIGINT, original_sigint_handler)
            raise KeyboardInterrupt("MAD process was interrupted, and has been deleted")

        signal.signal(
            signal.SIGINT, delete_process
        )  # Delete the process if interrupted

        # Start the process
        self.process = subprocess.Popen(
            [str(mad_path), "-q", "-e", startupChunk],
            bufsize=0,
            stdin=mad_read,  # Set the stdin of MAD to the read end of the pipe
            stdout=stdout,  # Forward stdout
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

        # stdout should be line buffered by default, but for jupyter notebook,
        # stdout is redirected and not line buffered by default
        self.send("io.stdout:setvbuf('line')")

        # Check if MAD started successfully
        self.send(f"{self.py_name}:send(1)")
        startup_status_checker = select.select(
            [self.mad_read_stream], [], [], 10
        )  # May not work on windows

        # Check if MAD started successfully using select
        if not startup_status_checker[0] or self.recv() != 1:  # Need to check number?
            self.close()
            raise OSError(f"Unsuccessful starting of {mad_path} process")

    def send_range(self, start: float, stop: float, size: int) -> None:
        """Send a numpy array as a range to MAD"""
        self.mad_input_stream.write(b"rng_")
        send_generic_range(self, start, stop, size)

    def send_logrange(self, start: float, stop: float, size: int) -> None:
        """Send a numpy array as a logrange to MAD"""
        self.mad_input_stream.write(b"lrng")
        send_generic_range(self, start, stop, size)

    def send_tpsa(self, monos: np.ndarray, coefficients: np.ndarray) -> None:
        """Send the monomials and coeeficients of a TPSA to MAD, creating a table representing the TPSA object"""
        self.mad_input_stream.write(b"tpsa")
        send_generic_tpsa(self, monos, coefficients, send_num)

    def send_cpx_tpsa(self, monos: np.ndarray, coefficients: np.ndarray) -> None:
        """Send the monomials and coeeficients of a complex TPSA to MAD, creating a table representing the complex TPSA object"""
        self.mad_input_stream.write(b"ctpa")
        send_generic_tpsa(self, monos, coefficients, send_cpx)

    def send(self, data: str | int | float | np.ndarray | bool | list) -> mad_process:
        """Send data to MAD, returns self for chaining"""
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
        """Perform a protected send to MAD, by first enabling error handling, so that if an error occurs, an error is returned"""
        return self.send(
            f"{self.py_name}:__err(true); {string}; {self.py_name}:__err(false);"
        )

    def protected_variable_retrieval(self, name: str) -> Any:
        """Perform a protected variable retrieval from MAD, by first enabling error handling, so that if an error occurs, an error is returned

        Args:
            name (str): The name of the variable to retrieve from MAD

        Returns:
            Any: The value of the variable retrieved from MAD
        """
        self.send(
            f"{self.py_name}:__err(true):send({name}):__err(false)"
        )  # Enable error handling, ask for the variable, and disable error handling
        return self.recv(name)

    def set_error_handler(self, on_off: bool) -> mad_process:
        """Enable or disable error handling"""
        self.send(f"{self.py_name}:__err({str(on_off).lower()})")

    def recv(self, varname: str = None) -> Any:
        """Receive data from MAD, if a function is returned, it will be executed with the argument mad_communication"""
        typ = self.mad_read_stream.read(4).decode("utf-8")
        self.varname = varname  # For mad reference
        return type_fun[typ]["recv"](self)

    def recv_and_exec(self, env: dict = {}) -> dict:
        """Read data from MAD and execute it"""
        # Check if user has already defined mad (madp_object will have mad defined), otherwise define it
        try:
            env["mad"]
        except KeyError:
            env["mad"] = self

        exec(compile(self.recv(), "ffrom_mad", "exec"), self.python_exec_context, env)
        return env

    # ----------------- Dealing with communication of variables ---------------- #
    def send_vars(self, **vars) -> mad_process:
        for name, var in vars.items():
            if isinstance(var, mad_ref):
                self.send(f"{name} = {var._name}")
            else:
                self.send(f"{name} = {self.py_name}:recv()").send(var)

    def recv_vars(self, *names) -> Any:
        if len(names) == 1:
            if not is_private(names[0]):
                return self.protected_variable_retrieval(names[0])
        else:
            return tuple(
                self.protected_variable_retrieval(name)
                for name in names
                if not is_private(name)
            )

    # -------------------------------------------------------------------------- #

    def close(self) -> None:
        """Close the pipes and wait for the process to finish"""
        if self.process.poll() is None:  # If process is still running
            self.send(f"{self.py_name}:__fin()")  # Tell the mad side to finish
            open_pipe = select.select([self.mad_read_stream], [], [], 10)
            if open_pipe[0]:
                # Wait for the mad side to finish (variable name in case of errors that need to be caught elsewhere)
                close_msg = self.recv("closing")
                if close_msg != "<closing pipe>":
                    Warning(
                        f"Unexpected message received: {close_msg}, MAD-NG may not have completed properly"
                    )
            self.process.terminate()  # Terminate the process on the python side
        
        # Close the debug file if it exists
        try:
            self.debug_file.close()
        except AttributeError:
            pass

        # Close the pipes
        if not self.mad_read_stream.closed:
            self.mad_read_stream.close()
        if not self.mad_input_stream.closed:
            self.mad_input_stream.close()

        # Wait for the process to finish
        self.process.wait()

    def __del__(self):
        self.close()


class mad_ref(object):
    def __init__(self, name: str, mad_proc: mad_process):
        assert (
            name is not None
        ), "Reference must have a variable to reference to. Did you forget to put a name in the receive functions?"
        self._name = name
        self._mad = mad_proc

    def __getattr__(self, item):
        if not is_private(item):
            try:
                return self[item]
            except (IndexError, KeyError):
                pass
        raise AttributeError(item)  # For python

    def __getitem__(self, item: str | int):
        if isinstance(item, int):
            result = self._mad.protected_variable_retrieval(f"{self._name}[{item+1}]")
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
        return self._mad.recv_vars(self._name)


# data transfer -------------------------------------------------------------- #


# Data ----------------------------------------------------------------------- #
def write_serial_data(self: mad_process, dat_fmt: str, *dat: Any):
    self.mad_input_stream.write(struct.pack(dat_fmt, *dat))


def read_data_stream(self: mad_process, dat_sz: int, dat_typ: np.dtype):
    return np.frombuffer(self.mad_read_stream.read(dat_sz), dtype=dat_typ)


# None ----------------------------------------------------------------------- #
def send_nil(self: mad_process, input):
    return None


def recv_nil(self: mad_process):
    return None


# Boolean -------------------------------------------------------------------- #
def send_bool(self: mad_process, input: bool):
    return self.mad_input_stream.write(struct.pack("?", input))


def recv_bool(self: mad_process) -> bool:
    return read_data_stream(self, 1, np.bool_)[0]


# int32 ---------------------------------------------------------------------- #
def send_int(self: mad_process, input: int):
    return write_serial_data(self, "i", input)


def recv_int(self: mad_process) -> int:
    return read_data_stream(self, 4, np.int32)[0]


# String --------------------------------------------------------------------- #
def send_str(self: mad_process, input: str):
    self.history += input + "\n"
    send_int(self, len(input))
    self.mad_input_stream.write(input.encode("utf-8"))


def recv_str(self: mad_process) -> str:
    res = self.mad_read_stream.read(recv_int(self)).decode("utf-8")
    return res


# number (in lua, float64 in python) ----------------------------------------- #
def send_num(self: mad_process, input: float):
    return write_serial_data(self, "d", input)


def recv_num(self: mad_process) -> float:
    return read_data_stream(self, 8, np.float64)[0]


# Complex (complex128) ------------------------------------------------------- #
def send_cpx(self: mad_process, input: complex):
    return write_serial_data(self, "dd", input.real, input.imag)


def recv_cpx(self: mad_process) -> complex:
    return read_data_stream(self, 16, np.complex128)[0]


# Range ---------------------------------------------------------------------- #
def send_generic_range(self, start: float, stop: float, size: int):
    write_serial_data(self, "ddi", start, stop, size)


def recv_range(self: mad_process) -> np.ndarray:
    return np.linspace(*struct.unpack("ddi", self.mad_read_stream.read(20)))


def recv_logrange(self: mad_process) -> np.ndarray:
    return np.geomspace(*struct.unpack("ddi", self.mad_read_stream.read(20)))


# irange --------------------------------------------------------------------- #
def send_int_range(self: mad_process, rng: range):
    return write_serial_data(self, "iii", rng.start, rng.stop, rng.step)


def recv_int_range(self: mad_process) -> range:
    start, stop, step = read_data_stream(self, 12, np.int32)
    return range(start, stop + 1, step)  # MAD is inclusive at both ends


# matrix --------------------------------------------------------------------- #
def send_generic_matrix(self: mad_process, mat: np.ndarray):
    assert len(mat.shape) == 2, "Matrix must be of two dimensions"
    write_serial_data(self, "ii", *mat.shape)
    self.mad_input_stream.write(mat.tobytes())


def recv_generic_matrix(self: mad_process, dtype: np.dtype) -> str:
    shape = read_data_stream(self, 8, np.int32)
    return read_data_stream(self, shape[0] * shape[1] * dtype.itemsize, dtype).reshape(
        shape
    )


def recv_matrix(self: mad_process) -> np.ndarray:
    return recv_generic_matrix(self, np.dtype("float64"))


def recv_cpx_matrix(self: mad_process) -> np.ndarray:
    return recv_generic_matrix(self, np.dtype("complex128"))


def recv_int_matrix(self: mad_process) -> np.ndarray:
    return recv_generic_matrix(self, np.dtype("int32"))


# monomial ------------------------------------------------------------------- #
def send_monomial(self: mad_process, mono: np.ndarray):
    send_int(self, mono.size)
    self.mad_input_stream.write(mono.tobytes())


def recv_monomial(self: mad_process) -> np.ndarray:
    return read_data_stream(self, recv_int(self), np.ubyte)


# TPSA ----------------------------------------------------------------------- #
def send_generic_tpsa(
    self: mad_process,
    monos: np.ndarray,
    coefficients: np.ndarray,
    send_num: Callable[[mad_process, float | complex], None],
):
    assert len(monos.shape) == 2, "The list of monomials must have two dimensions"
    assert len(monos) == len(
        coefficients
    ), "The number of monomials must be equal to the number of coefficients"
    assert (
        monos.dtype == np.uint8
    ), "The monomials must be of type 8-bit unsigned integer "
    write_serial_data(self, "ii", len(monos), len(monos[0]))
    for mono in monos:
        self.mad_input_stream.write(mono.tobytes())
    for coefficient in coefficients:
        send_num(self, coefficient)


def recv_generic_tpsa(self: mad_process, dtype: np.dtype) -> np.ndarray:
    num_mono, mono_len = read_data_stream(self, 8, np.int32)
    mono_list = np.reshape(
        read_data_stream(self, mono_len * num_mono, np.ubyte),
        (num_mono, mono_len),
    )
    coefficients = read_data_stream(self, num_mono * dtype.itemsize, dtype)
    return mono_list, coefficients


def recv_cpx_tpsa(self: mad_process):
    return recv_generic_tpsa(self, np.dtype("complex128"))


def recv_dbl_tpsa(self: mad_process):
    return recv_generic_tpsa(self, np.dtype("float64"))


# lists ---------------------------------------------------------------------- #
# Lists of strings are really slow to send, is there a way to improve this? (jgray 2024)
def send_list(self: mad_process, lst: list):
    send_int(self, len(lst))
    for item in lst:
        self.send(item)


def recv_list(self: mad_process) -> list:
    varname = self.varname  # cache
    haskeys = recv_bool(self)
    lstLen = recv_int(self)
    vals = [self.recv(varname and varname + f"[{i+1}]") for i in range(lstLen)]
    self.varname = varname  # reset
    if haskeys:
        return type_fun["ref_"]["recv"](self)
    else:
        return vals


# object (table with metatable are treated as pure reference) ---------------- #
def recv_reference(self: mad_process):
    return mad_ref(self.varname, self)


def send_reference(self, obj: mad_ref):
    return send_str(self, f"return {obj._name}")


# error ---------------------------------------------------------------------- #


def recv_err(self: mad_process):
    self.set_error_handler(False)
    raise RuntimeError("MAD Errored (see the MAD error output)")


# ---------------------------- dispatch tables ------------------------------- #
type_fun = {
    "nil_": {"recv": recv_nil, "send": send_nil},
    "bool": {"recv": recv_bool, "send": send_bool},
    "str_": {"recv": recv_str, "send": send_str},
    "tbl_": {"recv": recv_list, "send": send_list},
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
    ""    : {"recv": BrokenPipeError},
}


def get_typestr(
    a: str | int | float | np.ndarray | bool | list | tuple | range | mad_ref,
) -> type:
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
    list: "tbl_",
    tuple: "tbl_",
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
