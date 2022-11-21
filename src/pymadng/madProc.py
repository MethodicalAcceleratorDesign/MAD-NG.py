import struct, os, subprocess, sys, select, time, signal
from typing import Union, Tuple
from types import MappingProxyType, NoneType
import numpy as np
from .pymadClasses import madObject

# Working: mad.send("""py:send([==[mad.send('''py:send([=[mad.send("py:send([[print('hello world')]])")]=])''')]==])""")
# Working: mad.send("""py:send([=[mad.send("py:send([[print('hello')]])")]=])""")
# Working for me: mad.send("""send([==[mad.send(\"\"\"send([=[mad.send("send([[print('hello world')]])")]=])\"\"\")]==])""")

class mad_process:
    __data_types = MappingProxyType({
    NoneType              :   "nil_",
    str                   :   "str_",
    int                   :   "int_",
    float                 :   "num_",
    complex               :   "cnum",
    bool                  :   "bool",
    list                  :   "tbl_",
    np.dtype("float64")   :   "mat_",
    np.dtype('complex128'):   "cmat",
    np.dtype("int32")     :   "imat",
    })
    
    __data_sizes = MappingProxyType({
    np.float64   :   8,
    np.complex128:   16,
    np.int32     :   4,
    })

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
            preexec_fn=os.setpgrp, #Don't forward signals
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
            "np": np,
            "struct": struct,
            "superClass": superClass,
            "madObject": madObject,
        }
        self.fpyInput = os.fdopen(self.pyInput, "rb")
        self.pyInPoll = select.poll()
        self.pyInPoll.register(self.pyInput, select.POLLIN)

        self.fun_send = {
            "nil_": self.__send_nil ,
            "str_": self.__send_str ,
            "int_": self.__send_int ,
            "num_": self.__send_num ,
            "cnum": self.__send_cpx ,
            "bool": self.__send_bool,
            "tbl_": self.__send_list,
            "mat_": self.__send_mat ,
            "cmat": self.__send_cmat,
            "imat": self.__send_imat,
        }
        self.fun_recv = {
            b"nil_": self.__recv_nil ,
            b"ref_": self.__recv_ref ,
            b"obj_": self.__recv_obj ,
            b"str_": self.__recv_str ,
            b"int_": self.__recv_int ,
            b"num_": self.__recv_num ,
            b"cnum": self.__recv_cpx ,
            b"bool": self.__recv_bool,
            b"tbl_": self.__recv_list,
            b"mat_": self.__recv_mat ,
            b"cmat": self.__recv_cmat,
            b"imat": self.__recv_imat,
            b"rng_": self.__recv_rng,
            b"irng": self.__recv_irng ,
            b"lrng": self.__recv_lrng,
        }

    def __get_typestring(self, a: Union[str, int, float, np.ndarray, bool, list]):
        if isinstance(a, np.ndarray):
            return a.dtype
        else:
            return type(a)

    #--------------------------------------- Sending data ---------------------------------------#
    def __send_nil(self, input: None) -> str:
        return

    def __send_str(self, input: str) -> str:
        self.__send_int(len(input))
        self.process.stdin.write(input.encode("utf-8"))

    def __send_int(self, input: int) -> str:
        self.process.stdin.write(input.to_bytes(4, self.nativeByteOrder)) #Therefore must be int32

    def __send_num(self, input: float) -> str:
        self.process.stdin.write(struct.pack("d", input))
    
    def __send_cpx(self, input: complex) -> str:
        self.process.stdin.write(struct.pack("dd", input.real, input.imag))
        
    def __send_bool(self, input: bool) -> str:
        self.process.stdin.write(struct.pack("?", input))

    def __send_shape(self, shape: Tuple[int, int]) -> None:
        self.__send_int(shape[0])
        self.__send_int(shape[1])
    
    def __send_gmat(self, mat: np.ndarray) -> str:
        assert((len(mat.shape) == 2), "Matrix must be of two dimensions")
        self.__send_shape(mat.shape)
        self.process.stdin.write(mat.tobytes())

    def __send_mat(self, mat: np.ndarray) -> str: #reduce the three below into above
        self.__send_gmat(mat)

    def __send_cmat(self, mat: np.ndarray) -> str:
        self.__send_gmat(mat)
    
    def __send_imat(self, mat: np.ndarray) -> str:
        self.__send_gmat(mat)

    def __send_list(self, lst: list):
        n = len(lst)
        self.__send_int(n)
        for i in range(n): 
            self.send(lst[i]) # deep copy
        return self

    
    #--------------------------------------------------------------------------------------------#

    #--------------------------------------- Receiving data -------------------------------------#
    def __recv_nil(self) -> None: 
        return None
    
    def __recv_ref(self) -> str:
        return "MAD_REFERENCE"

    def __recv_obj(self) -> madObject:
        myobject = madObject(self.varname, self.superClass)
        if self.varname:
            self.superClass.__dict__[self.varname] = myobject 
        return myobject

    def __recv_str(self) -> str:
        str_len = self.__recv_int()
        return self.fpyInput.read(str_len).decode("utf-8")

    def __recv_int(self) -> int:
        return int.from_bytes(self.fpyInput.read(4), self.nativeByteOrder) #Therefore must be int32

    def __recv_num(self) -> float:
        return np.frombuffer(self.fpyInput.read(8), dtype=np.float64)[0]
    
    def __recv_cpx(self) -> complex:
        return np.frombuffer(self.fpyInput.read(16), dtype=np.complex128)[0]
        
    def __recv_bool(self) -> str:
        return np.frombuffer(self.fpyInput.read(1), dtype=np.bool_)[0]

    def __recv_shape(self) -> Tuple[int, int]:
        return struct.unpack("ii", self.fpyInput.read(8))
    
    def __recv_gmat(self, dtype: np.dtype) -> str:
        shape = self.__recv_shape()
        arraySize = shape[0] * shape[1] * self.__data_sizes[dtype]
        return np.frombuffer(self.fpyInput.read(arraySize), dtype=dtype).reshape(shape)

    def __recv_mat(self) -> str:
        return self.__recv_gmat(np.float64)

    def __recv_cmat(self) -> str:
        return self.__recv_gmat(np.complex128)
    
    def __recv_imat(self) -> str:
        return self.__recv_gmat(np.int32)
    
    def __recv_list(self) -> list:
        list_len = self.__recv_int()
        if list_len < 0:
            return lambda name: madObject(name, self)
        else:
            return [self.recv() for i in range(list_len)]
    
    def __recv_rng(self) -> np.ndarray:
        start, stop, length = struct.unpack("ddd", self.fpyInput.read(24))
        return np.linspace(start, stop, int(length))

    def __recv_irng(self) -> np.ndarray:
        start, stop, length = struct.unpack("iii", self.fpyInput.read(12))
        return np.linspace(start, stop, length)
    
    def __recv_lrng(self) -> np.ndarray:
        start, stop, length = struct.unpack("ddd", self.fpyInput.read(24))
        return np.logspace(start, stop, int(length))


    #--------------------------------------------------------------------------------------------#

    def send(self, input: Union[str, int, float, np.ndarray, bool, list]) -> None:
        try:
            typ = self.__data_types[self.__get_typestring(input)]
            self.process.stdin.write(typ.encode("utf-8"))
            self.fun_send[typ](input)
            return
        except KeyError: #raise not in exception to reduce error output
            pass
        raise TypeError("Cannot send data, innapropriate argument type")

    def recv(self, varname: str = None) -> Union[str, int, float, np.ndarray, bool, list]:
        typ = self.fpyInput.read(4)
        self.varname = varname
        return self.fun_recv[typ]()

    def recv_and_exec(self, env:dict={}) -> dict:
        code = compile(self.recv(), "pyInput", "exec")
        env.update({"mad": self})
        exec(code, self.globalVars, env)
        # del env["mad"] # necessary?
        return env

    def readTable(self, tableLength):
        table = []
        for _ in range(tableLength):
            table.append(self.read(newData=False)["tabledataval"])
        return table

    def __del__(self):
        self.process.terminate()
        self.process.wait()
