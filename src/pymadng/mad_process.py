import struct, os, subprocess, sys, select
from typing import Union, Tuple, Callable
from types import MappingProxyType, NoneType
import numpy as np
from .pymadClasses import madObject, madReference, madFunctor

# Working: mad.send("""py:send([==[mad.send('''py:send([=[mad.send("py:send([[print('hello world')]])")]=])''')]==])""")
# Working: mad.send("""py:send([=[mad.send("py:send([[print('hello')]])")]=])""")
# Working for me: mad.send("""send([==[mad.send(\"\"\"send([=[mad.send("send([[print('hello world')]])")]=])\"\"\")]==])""")


class mad_process:
    __data_types = MappingProxyType(
        {  # Proxy type means object cannot be changed
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
    )

    def __init__(
        self, pyName: str = "py", madPath: str = None, debug=False, superClass=None
    ) -> None:
        self.pyName = pyName
        self.superClass = superClass
        self.nativeByteOrder = sys.byteorder

        madPath = madPath or os.path.dirname(os.path.abspath(__file__)) + "/mad"

        self.pyInput, madOutput = os.pipe()
        startupChunk = (
            "MAD.pymad '"
            + pyName
            + "' {dispdbgf = "
            + str(debug).lower()
            + "} :start("
            + str(madOutput)
            + ")"
        )

        self.process = subprocess.Popen(
            [madPath, "-q", "-e", startupChunk],
            bufsize=0,
            stdout=sys.stdout,
            stderr=sys.stderr,
            stdin=subprocess.PIPE,
            preexec_fn=os.setpgrp,  # Don't forward signals
            pass_fds=[madOutput],
            # text=True, # Makes sending byte data easy
        )
        os.close(madOutput)

        if self.process.poll():  # Required?
            raise (
                OSError(
                    f"Unsuccessful opening of {madPath}, process closed immediately"
                )
            )

        self.globalVars = {
            "np"        : np        ,
            "superClass": superClass,
        }
        self.fpyInput = os.fdopen(self.pyInput, "rb")

        self.fun = {
            "nil_": {"recv": self.__recv_nil , "send": self.__send_nil },
            "ref_": {"recv": self.__recv_ref , "send": self.__send_ref },
            "obj_": {"recv": self.__recv_obj , "send": self.__send_ref },
            "fun_": {"recv": self.__recv_fun , "send": self.__send_ref },
            "str_": {"recv": self.__recv_str , "send": self.__send_str },
            "int_": {"recv": self.__recv_int , "send": self.__send_int },
            "num_": {"recv": self.__recv_num , "send": self.__send_num },
            "cnum": {"recv": self.__recv_cpx , "send": self.__send_cpx },
            "bool": {"recv": self.__recv_bool, "send": self.__send_bool},
            "tbl_": {"recv": self.__recv_list, "send": self.__send_list},
            "mat_": {"recv": self.__recv_mat , "send": self.__send_gmat},
            "cmat": {"recv": self.__recv_cmat, "send": self.__send_gmat},
            "imat": {"recv": self.__recv_imat, "send": self.__send_gmat},
            "rng_": {"recv": self.__recv_rng , "send": self.send_rng   },
            "irng": {"recv": self.__recv_irng, "send": self.__send_irng},
            "lrng": {"recv": self.__recv_lrng, "send": self.send_lrng  },
        }

    def __get_typestring(self, a: Union[str, int, float, np.ndarray, bool, list]):
        if isinstance(a, np.ndarray):
            return a.dtype
        else:
            return type(a)

    # --------------------------------------- Sending data ---------------------------------------#
    __send_nil = lambda self, input: None

    def __send_ref(self, obj: madReference):
        if obj.__name__ == "__last__":
            self.send(f"return table.unpack({obj.__name__})")
        else:
            self.send(f"return {obj.__name__}")

    def __send_str(self, input: str):
        self.__send_int(len(input))
        self.process.stdin.write(input.encode("utf-8"))

    def __send_int(self, input: int):
        self.process.stdin.write(input.to_bytes(4, self.nativeByteOrder))  
        # Therefore must be int32

    def __send_num(self, input: float):
        self.process.stdin.write(struct.pack("d", input))

    def __send_cpx(self, input: complex):
        self.process.stdin.write(struct.pack("dd", input.real, input.imag))

    def __send_bool(self, input: bool):
        self.process.stdin.write(struct.pack("?", input))

    def __send_shape(self, shape: Tuple[int, int]) -> None:
        self.__send_int(shape[0])
        self.__send_int(shape[1])

    def __send_gmat(self, mat: np.ndarray) -> str:
        assert len(mat.shape) == 2, "Matrix must be of two dimensions"
        self.__send_shape(mat.shape)
        self.process.stdin.write(mat.tobytes())

    def __send_list(self, lst: list):
        n = len(lst)
        self.__send_int(n)
        for i in range(n):
            self.send(lst[i])  # deep copy
        return self

    def __send_grng(self, rng: Union[np.ndarray, list]):
        self.process.stdin.write(struct.pack("ddi", rng[0], rng[-1], len(rng)))

    def send_rng(self, rng: Union[np.ndarray, list]):
        self.process.stdin.write("rng_".encode("utf-8"))
        self.__send_grng(rng)

    def send_lrng(self, lrng: Union[np.ndarray, list]):
        self.process.stdin.write("lrng".encode("utf-8"))
        self.__send_grng(lrng)

    def __send_irng(self, rng: range):
        self.process.stdin.write(struct.pack("iii", rng.start, rng.stop, rng.step))

    # --------------------------------------------------------------------------------------------#

    # --------------------------------------- Receiving data -------------------------------------#
    __recv_nil = lambda self: None

    def __recv_ref(self) -> madReference:
        return self.__recv_gref(madReference)

    def __recv_obj(self) -> madObject:
        return self.__recv_gref(madObject)

    def __recv_fun(self) -> madFunctor:
        return self.__recv_gref(madFunctor)

    def __recv_gref(self, ctor) -> Union[madObject, madReference, madFunctor]:
        return ctor(self.varname, self.superClass)

    def __recv_str(self) -> str:
        str_len = self.__recv_int()
        return self.fpyInput.read(str_len).decode("utf-8")

    def __recv_int(self) -> int: # Must be int32
        return int.from_bytes(self.fpyInput.read(4), self.nativeByteOrder) 

    def __recv_num(self) -> float:
        return np.frombuffer(self.fpyInput.read(8), dtype=np.float64)[0]

    def __recv_cpx(self) -> complex:
        return np.frombuffer(self.fpyInput.read(16), dtype=np.complex128)[0]

    def __recv_bool(self) -> str:
        return np.frombuffer(self.fpyInput.read(1), dtype=np.bool_)[0]

    def __recv_gmat(self, dtype: np.dtype) -> str:
        shape = np.frombuffer(self.fpyInput.read(8), dtype=np.int32)
        arraySize = shape[0] * shape[1] * dtype.itemsize
        return np.frombuffer(self.fpyInput.read(arraySize), dtype=dtype).reshape(shape)

    def __recv_mat(self) -> str:
        return self.__recv_gmat(np.dtype("float64"))

    def __recv_cmat(self) -> str:
        return self.__recv_gmat(np.dtype("complex128"))

    def __recv_imat(self) -> str:
        return self.__recv_gmat(np.dtype("int32"))

    def __recv_list(self) -> list:
        list_len = self.__recv_int()
        return [
            self.recv(self.varname and self.varname + f"[{i+1}]")
            for i in range(list_len)
        ]

    def __recv_rng(self) -> np.ndarray:
        return np.linspace(*struct.unpack("ddi", self.fpyInput.read(20)))

    def __recv_lrng(self) -> np.ndarray:
        return np.logspace(*struct.unpack("ddi", self.fpyInput.read(20)))

    def __recv_irng(self) -> np.ndarray:
        start, stop, step = np.frombuffer(self.fpyInput.read(12), dtype=np.int32)
        return range(start, stop+1, step)

    # --------------------------------------------------------------------------------------------#

    def send(self, input: Union[str, int, float, np.ndarray, bool, list]) -> None:
        try:
            typ = self.__data_types[self.__get_typestring(input)]
            self.process.stdin.write(typ.encode("utf-8"))
            self.fun[typ]["send"](input)
            return
        except KeyError:  # raise not in exception to reduce error output
            pass
        raise TypeError(f"\nCannot send data, innapropriate argument type, expected a type in: \n{list(self.__data_types.keys())}")

    def recv(
        self, varname: str = None
    ) -> Union[str, int, float, np.ndarray, bool, list]:
        typ = self.fpyInput.read(4).decode("utf-8")
        self.varname = varname
        return self.fun[typ]["recv"]()

    def recv_and_exec(self, env: dict = {}) -> dict:
        code = compile(self.recv(), "pyInput", "exec")
        env.update({"mad": self})
        exec(code, self.globalVars, env)
        # del env["mad"] # necessary?
        return env

    def __del__(self):
        self.fpyInput.close()
        self.process.stdin.close()
        self.process.terminate()
        self.process.wait()
