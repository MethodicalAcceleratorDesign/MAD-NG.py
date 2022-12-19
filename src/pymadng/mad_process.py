import struct, os, subprocess, sys, platform
from typing import Union, Tuple, Callable
import numpy as np
from .pymadClasses import madObject, madReference, madFunction

__all__ = ["mad_process"]

data_types = {
        type(None)              : "nil_",
        str                     : "str_",
        int                     : "int_",
        np.int32                : "int_",
        float                   : "num_",
        np.float64              : "num_",
        complex                 : "cpx_",
        np.complex128           : "cpx_",
        bool                    : "bool",
        list                    : "tbl_",
        range                   : "irng",
        np.dtype("float64")     : "mat_",
        np.dtype("complex128")  : "cmat",
        np.dtype("int32")       : "imat",
        madObject               : "obj_",
        madReference            : "ref_",
        madFunction             : "fun_",
        np.dtype("ubyte")       : "mono",
}


class mad_process:
    def __init__(self, py_name: str, mad_path: str, debug: bool, mad_class) -> None:
        self.pyName = py_name
        self.mad_class = mad_class

        mad_path = mad_path or os.path.dirname(os.path.abspath(__file__)) + "/mad_" + platform.system()

        self.from_mad, mad_side = os.pipe()
        startupChunk = f"MAD.pymad '{py_name}' {{_dbg = {str(debug).lower()}}} :__ini({mad_side})"

        self.process = subprocess.Popen(
            [mad_path, "-q", "-e", startupChunk],
            bufsize=0,
            stdin=subprocess.PIPE,
            preexec_fn=os.setpgrp,  # Don't forward signals
            pass_fds=[mad_side, sys.stdout.fileno(), sys.stderr.fileno()],
        )
        os.close(mad_side)

        self.globalVars = {
            "np" : np       ,
            "mad": mad_class,
        }
        self.ffrom_mad = os.fdopen(self.from_mad, "rb")

        self.fun = {
            "nil_": {"recv": recv_nil , "send": send_nil },
            "bool": {"recv": recv_bool, "send": send_bool},
            "str_": {"recv": recv_str , "send": send_str },
            "tbl_": {"recv": recv_list, "send": send_list},
            "ref_": {"recv": recv_ref , "send": send_ref },
            "fun_": {"recv": recv_fun , "send": send_ref },
            "obj_": {"recv": recv_obj , "send": send_ref },
            "int_": {"recv": recv_int , "send": send_int },
            "num_": {"recv": recv_num , "send": send_num },
            "cpx_": {"recv": recv_cpx , "send": send_cpx },
            "mat_": {"recv": recv_mat , "send": send_gmat},
            "cmat": {"recv": recv_cmat, "send": send_gmat},
            "imat": {"recv": recv_imat, "send": send_gmat},
            "rng_": {"recv": recv_rng ,                  },
            "lrng": {"recv": recv_lrng,                  },
            "irng": {"recv": recv_irng, "send": send_irng},
            "mono": {"recv": recv_mono, "send": send_mono},
            "tpsa": {"recv": recv_tpsa,                  },
            "ctpa": {"recv": recv_ctpa,                  },
            "err_": {"recv": recv_err ,                  },
        }
        # stdout should be line buffered by default, but for
        # jupyter notebook, stdout is redirected and not 
        # line buffered by default
        self.send(
            f"""io.stdout:setvbuf('line')
                {self.pyName}:send(1)"""
        )
        mad_return = self.recv()
        if mad_return != 1:  # Need to check number?
            raise (OSError(f"Unsuccessful starting of {mad_path} process"))

    def send_rng(self, start: float, stop: float, size: int):
        """Send a numpy array as a rng to MAD"""
        self.process.stdin.write(b"rng_")
        send_grng(self, start, stop, size)

    def send_lrng(self, start: float, stop: float, size: int):
        """Send a numpy array as a logrange to MAD"""
        self.process.stdin.write(b"lrng")
        send_grng(self, start, stop, size)

    def send_tpsa(self, monos: np.ndarray, coefficients: np.ndarray):
        """Send the monomials and coeeficients of a TPSA to MAD, creating a table representing the TPSA object"""
        self.process.stdin.write(b"tpsa")
        send_gtpsa(self, monos, coefficients, send_num)

    def send_ctpsa(self, monos: np.ndarray, coefficients: np.ndarray):
        """Send the monomials and coeeficients of a complex TPSA to MAD, creating a table representing the complex TPSA object"""
        self.process.stdin.write(b"ctpa")
        send_gtpsa(self, monos, coefficients, send_cpx)

    def send(self, data: Union[str, int, float, np.ndarray, bool, list]) -> None:
        """Send data to MAD"""
        try:
            typ = data_types[get_typestring(data)]
            self.process.stdin.write(typ.encode("utf-8"))
            self.fun[typ]["send"](self, data)
            return
        except KeyError:  # raise not in exception to reduce error output
            pass
        raise TypeError(
            f"Unsupported data type, expected a type in: \n{list(data_types.keys())}, got {type(data)}"
        )

    def recv(
        self, varname: str = None
    ) -> Union[str, int, float, np.ndarray, bool, list]:
        """Receive data from MAD"""
        typ = self.ffrom_mad.read(4).decode("utf-8")
        self.varname = varname  # For mad reference
        return self.fun[typ]["recv"](self)

    def recv_and_exec(self, env: dict = {}) -> dict:
        """Read data from MAD and execute it"""
        exec(compile(self.recv(), "ffrom_mad", "exec"), self.globalVars, env)
        return env

    def __del__(self):
        self.ffrom_mad.close()
        self.send("py:__fin()")
        self.process.terminate() #In case user left mad waiting
        self.process.stdin.close()
        self.process.wait()


def get_typestring(a: Union[str, int, float, np.ndarray, bool, list]):
    if isinstance(a, np.ndarray):
        return a.dtype
    else:
        return type(a)


# --------------------------------------- Sending data ---------------------------------------#
send_nil = lambda self, input: None


def send_ref(self: mad_process, obj: madReference) -> None:
    send_str(self, f"return {obj.__name__}")


def send_str(self: mad_process, input: str) -> None:
    send_int(self, len(input))
    self.process.stdin.write(input.encode("utf-8"))


def send_int(self: mad_process, input: int) -> None:
    self.process.stdin.write(struct.pack("i", input))


def send_num(self: mad_process, input: float) -> None:
    self.process.stdin.write(struct.pack("d", input))


def send_cpx(self: mad_process, input: complex) -> None:
    self.process.stdin.write(struct.pack("dd", input.real, input.imag))


def send_bool(self: mad_process, input: bool) -> None:
    self.process.stdin.write(struct.pack("?", input))


def send_shape(self: mad_process, shape: Tuple[int, int]) -> None:
    send_int(self, shape[0])
    send_int(self, shape[1])


def send_gmat(self: mad_process, mat: np.ndarray) -> None:
    assert len(mat.shape) == 2, "Matrix must be of two dimensions"
    send_shape(self, mat.shape)
    self.process.stdin.write(mat.tobytes())


def send_list(self: mad_process, lst: list) -> None:
    n = len(lst)
    send_int(self, n)
    for item in lst:
        self.send(item)  # deep copy
    return self


def send_grng(self: mad_process, start: float, stop: float, size: int) -> None:
    self.process.stdin.write(struct.pack("ddi", start, stop, size))

def send_irng(self: mad_process, rng: range) -> None:
    self.process.stdin.write(struct.pack("iii", rng.start, rng.stop, rng.step))


def send_mono(self: mad_process, mono: np.ndarray) -> None:
    send_int(self, mono.size)
    self.process.stdin.write(mono.tobytes())


def send_gtpsa(
    self: mad_process,
    monos: np.ndarray,
    coefficients: np.ndarray,
    fsendNum: Callable[[mad_process, Union[float, complex]], None],
) -> None:
    assert len(monos.shape) == 2, "The list of monomials must have two dimensions"
    assert len(monos) == len(coefficients), "The number of monomials must be equal to the number of coefficients"
    assert monos.dtype == np.uint8, "The monomials must be of type 8-bit unsigned integer "
    send_int(self, len(monos))  # Num monomials
    send_int(self, len(monos[0]))  # Monomial length
    for mono in monos:
        self.process.stdin.write(mono.tobytes())
    for coefficient in coefficients:
        fsendNum(self, coefficient)

# --------------------------------------------------------------------------------------------#

# --------------------------------------- Receiving data -------------------------------------#
recv_nil = lambda self: None


def recv_ref(self: mad_process) -> madReference:
    return madReference(self.varname, self.mad_class)


def recv_obj(self: mad_process) -> madObject:
    return madObject(self.varname, self.mad_class)


def recv_fun(self: mad_process) -> madFunction:
    return madFunction(self.varname, self.mad_class)


def recv_str(self: mad_process) -> str:
    return self.ffrom_mad.read(recv_int(self)).decode("utf-8")


def recv_int(self: mad_process) -> int:  # Must be int32
    return int.from_bytes(self.ffrom_mad.read(4), sys.byteorder)


def recv_num(self: mad_process) -> float:
    return np.frombuffer(self.ffrom_mad.read(8), dtype=np.float64)[0]


def recv_cpx(self: mad_process) -> complex:
    return np.frombuffer(self.ffrom_mad.read(16), dtype=np.complex128)[0]


def recv_bool(self: mad_process) -> str:
    return np.frombuffer(self.ffrom_mad.read(1), dtype=np.bool_)[0]


def recv_gmat(self: mad_process, dtype: np.dtype) -> str:
    shape = np.frombuffer(self.ffrom_mad.read(8), dtype=np.int32)
    arraySize = shape[0] * shape[1] * dtype.itemsize
    return np.frombuffer(self.ffrom_mad.read(arraySize), dtype=dtype).reshape(shape)


def recv_mat(self: mad_process) -> str:
    return recv_gmat(self, np.dtype("float64"))


def recv_cmat(self: mad_process) -> str:
    return recv_gmat(self, np.dtype("complex128"))


def recv_imat(self: mad_process) -> str:
    return recv_gmat(self, np.dtype("int32"))


def recv_list(self: mad_process) -> list:
    varname = self.varname  # cache
    haskeys = recv_bool(self)
    lstLen = recv_int(self)
    vals = [self.recv(varname and varname + f"[{i+1}]") for i in range(lstLen)]
    self.varname = varname  # reset
    if haskeys and lstLen == 0:
        return recv_ref(self)
    elif haskeys:
        return vals, recv_ref(self)
    else:
        return vals


def recv_irng(self: mad_process) -> range:
    start, stop, step = np.frombuffer(self.ffrom_mad.read(12), dtype=np.int32)
    return range(start, stop + 1, step)  # MAD is inclusive at both ends


def recv_rng(self: mad_process) -> np.ndarray:
    return np.linspace(*struct.unpack("ddi", self.ffrom_mad.read(20)))


def recv_lrng(self: mad_process) -> np.ndarray:
    return np.geomspace(*struct.unpack("ddi", self.ffrom_mad.read(20)))


def recv_mono(self: mad_process) -> np.ndarray:
    mono_len = recv_int(self)
    return np.frombuffer(self.ffrom_mad.read(mono_len), dtype=np.ubyte)


def recv_gtpsa(self: mad_process, dtype: np.dtype) -> np.ndarray:
    num_mono, mono_len = np.frombuffer(self.ffrom_mad.read(8), dtype=np.int32)
    mono_list = np.reshape(
        np.frombuffer(self.ffrom_mad.read(mono_len * num_mono), dtype=np.ubyte),
        (num_mono, mono_len),
    )
    coefficients = np.frombuffer(
        self.ffrom_mad.read(num_mono * dtype.itemsize), dtype=dtype
    )
    return mono_list, coefficients


def recv_ctpa(self: mad_process):
    return recv_gtpsa(self, np.dtype("complex128"))


def recv_tpsa(self: mad_process):
    return recv_gtpsa(self, np.dtype("float64"))


def recv_err(self: mad_process):
    self.mad_class._MAD__errhdlr(False)
    raise RuntimeError("MAD Errored (see the MAD error output)")
# --------------------------------------------------------------------------------------------#
