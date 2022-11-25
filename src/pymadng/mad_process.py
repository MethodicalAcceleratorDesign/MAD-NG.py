import struct, os, subprocess, sys
from typing import Union, Tuple
from types import NoneType
import numpy as np
from .pymadClasses import madObject, madReference, madFunctor

__all__ = ["mad_process"]

data_types = { 
        NoneType                : "nil_",
        str                     : "str_",
        int                     : "int_",
        np.int32                : "int_",
        float                   : "num_",
        np.float64              : "num_",
        complex                 : "cnum",
        np.complex128           : "cnum",
        bool                    : "bool",
        list                    : "tbl_",
        range                   : "irng",
        np.dtype("float64")     : "mat_",
        np.dtype("complex128")  : "cmat",
        np.dtype("int32")       : "imat",
        madObject               : "obj_",
        madReference            : "ref_",
        madFunctor              : "fun_",
}

class mad_process:
    def __init__(
        self, pyName: str = "py", madPath: str = None, debug=False, mad_class=None
    ) -> None:
        self.pyName = pyName
        self.mad_class = mad_class

        madPath = madPath or os.path.dirname(os.path.abspath(__file__)) + "/mad"

        self.from_mad, mad_side = os.pipe()
        startupChunk = (
            "MAD.pymad '"
            + pyName
            + "' {_dbgf = "
            + str(debug).lower()
            + "} :start("
            + str(mad_side)
            + ")"
        )

        self.process = subprocess.Popen(
            [madPath, "-q", "-e", startupChunk],
            bufsize=0,
            stdout=sys.stdout,
            stderr=sys.stderr,
            stdin=subprocess.PIPE,
            preexec_fn=os.setpgrp,  # Don't forward signals
            pass_fds=[mad_side],
        )
        os.close(mad_side)

        self.globalVars = {
            "np"        : np        ,
            "mad": mad_class,
        }
        self.ffrom_mad = os.fdopen(self.from_mad, "rb")

        self.fun = {
            "nil_": {"recv": recv_nil , "send": send_nil      },
            "bool": {"recv": recv_bool, "send": send_bool     },
            "str_": {"recv": recv_str , "send": send_str      },
            "tbl_": {"recv": recv_list, "send": send_list     },
            "ref_": {"recv": recv_ref , "send": send_ref      },
            "fun_": {"recv": recv_fun , "send": send_ref      },
            "obj_": {"recv": recv_obj , "send": send_ref      },
            "int_": {"recv": recv_int , "send": send_int      },
            "num_": {"recv": recv_num , "send": send_num      },
            "cnum": {"recv": recv_cpx , "send": send_cpx      },
            "mat_": {"recv": recv_mat , "send": send_gmat     },
            "cmat": {"recv": recv_cmat, "send": send_gmat     },
            "imat": {"recv": recv_imat, "send": send_gmat     },
            "rng_": {"recv": recv_rng ,                       },
            "lrng": {"recv": recv_lrng,                       },
            "irng": {"recv": recv_irng, "send": send_irng     },
        }
        mad_return = 0
        try: 
            self.send(f"{self.pyName}:send(1)")
            mad_return = self.recv()
        except:
            pass
        if mad_return != 1: #Need to check number?
            raise (OSError(f"Unsuccessful starting of {madPath} process"))

    def send_rng(self, rng: Union[np.ndarray, list]):
        """Send a numpy array as a rng to MAD"""
        self.process.stdin.write(b"rng_")
        send_grng(self, rng)

    def send_lrng(self, lrng: Union[np.ndarray, list]):
        """Send a numpy array as a logrange to MAD"""
        self.process.stdin.write(b"lrng")
        send_grng(self, lrng)

    def send(self, data: Union[str, int, float, np.ndarray, bool, list]) -> None:
        """Send data to MAD"""
        try:
            typ = data_types[get_typestring(data)]
            self.process.stdin.write(typ.encode("utf-8"))
            self.fun[typ]["send"](self, data)
            return
        except KeyError:  # raise not in exception to reduce error output
            raise TypeError(f"\nUnsupported data type, expected a type in: \n{list(data_types.keys())}")

    def recv(
        self, varname: str = None
    ) -> Union[str, int, float, np.ndarray, bool, list]:
        """Receive data from MAD"""
        typ = self.ffrom_mad.read(4).decode("utf-8")
        self.varname = varname #For mad reference
        return self.fun[typ]["recv"](self)

    def recv_and_exec(self, env: dict = {}) -> dict:
        """Read data from MAD and execute it"""
        exec(compile(self.recv(), "ffrom_mad", "exec"), self.globalVars, env)
        return env

    def __del__(self):
        self.ffrom_mad.close()
        self.process.stdin.close()
        self.process.terminate()
        self.process.wait()

def get_typestring(a: Union[str, int, float, np.ndarray, bool, list]):
    if isinstance(a, np.ndarray): 
        return a.dtype
    else:
        return type(a)

# --------------------------------------- Sending data ---------------------------------------#
send_nil = lambda self, input: None

def send_ref(self: mad_process, obj: madReference):
    if obj.__name__ == "__last__":
        self.send(f"return table.unpack({obj.__name__})")
    else:
        self.send(f"return {obj.__name__}")

def send_str(self: mad_process, input: str):
    send_int(self, len(input))
    self.process.stdin.write(input.encode("utf-8"))

def send_int(self: mad_process, input: int):
    self.process.stdin.write(struct.pack("i", input))  

def send_num(self: mad_process, input: float):
    self.process.stdin.write(struct.pack("d", input))

def send_cpx(self: mad_process, input: complex):
    self.process.stdin.write(struct.pack("dd", input.real, input.imag))

def send_bool(self: mad_process, input: bool):
    self.process.stdin.write(struct.pack("?", input))

def send_shape(self: mad_process, shape: Tuple[int, int]) -> None:
    send_int(self, shape[0])
    send_int(self, shape[1])

def send_gmat(self: mad_process, mat: np.ndarray) -> str:
    assert len(mat.shape) == 2, "Matrix must be of two dimensions"
    send_shape(self, mat.shape)
    self.process.stdin.write(mat.tobytes())

def send_list(self: mad_process, lst: list):
    n = len(lst)
    send_int(self, n)
    for i in range(n):
        self.send(lst[i])  # deep copy
    return self

def send_grng(self: mad_process, rng: Union[np.ndarray, list]):
    self.process.stdin.write(struct.pack("ddi", rng[0], rng[-1], len(rng)))

def send_irng(self: mad_process, rng: range):
    self.process.stdin.write(struct.pack("iii", rng.start, rng.stop, rng.step))

# --------------------------------------------------------------------------------------------#

# --------------------------------------- Receiving data -------------------------------------#
recv_nil = lambda self: None

def recv_ref(self: mad_process) -> madReference:
    return madReference(self.varname, self.mad_class)

def recv_obj(self: mad_process) -> madObject:
    return madObject(self.varname, self.mad_class)

def recv_fun(self: mad_process) -> madFunctor:
    return madFunctor(self.varname, self.mad_class)

def recv_str(self: mad_process) -> str:
    return self.ffrom_mad.read(recv_int(self)).decode("utf-8")

def recv_int(self: mad_process) -> int: # Must be int32
    return np.frombuffer(self.ffrom_mad.read(4), dtype=np.int32)[0] 

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
    return [
        self.recv(self.varname and self.varname + f"[{i+1}]")
        for i in range(recv_int(self))
    ]

def recv_irng(self: mad_process) -> range:
    start, stop, step = np.frombuffer(self.ffrom_mad.read(12), dtype=np.int32)
    return range(start, stop+1, step) #MAD is inclusive at both ends

def recv_rng(self: mad_process) -> np.ndarray:
    return np.linspace(*struct.unpack("ddi", self.ffrom_mad.read(20)))

def recv_lrng(self: mad_process) -> np.ndarray:
    return np.logspace(*struct.unpack("ddi", self.ffrom_mad.read(20)))

# --------------------------------------------------------------------------------------------#
