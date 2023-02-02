from .mad_process import mad_process
from .mad_classes import mad_ref
from .mad_last import last_counter
from .mad_strings import mad_strings
from typing import Any

class mad_comm(object):
    """An object that provides a layer over the mad_process for more advanced features and communication with MAD"""

    def __init__(self, py_name, mad_path, debug, num_temp_vars, ipython_use_jedi) -> None:
        self.process = mad_process(py_name, mad_path, debug, self)
        self.mad_strs = mad_strings(py_name)
        self.last_counter = last_counter(num_temp_vars)
        self.ipython_use_jedi = ipython_use_jedi
        self.py_name = py_name
        self.process.send(
            """
        function __mklast__ (a, b, ...)
            if MAD.typeid.is_nil(b) then return a
            else return {a, b, ...}
            end
        end
        __last__ = {}
        """
        )
    def __getattr__(self, name: str) -> Any: # Forwards all other attributes to the mad_process
        return getattr(self.process, name)

    def errhdlr(self, on_off: bool):
        self.process.send(f"py:__err("+ str(on_off).lower() + ")")

    def safe_send(self, string: str):
        return self.process.send(f"py:__err(true); {string}; py:__err(false);")
    
        # -------------------------------- Dealing with communication of variables --------------------------------#
    def send_vars(self, names, vars):
        if isinstance(names, str): 
            names = [names]
            vars = [vars]
        else:
            assert isinstance(vars, list), "A list of names must be matched with a list of variables"
            assert len(vars) == len(names), "The number of names must match the number of variables"
        for i, var in enumerate(vars):
            if isinstance(vars[i], mad_ref):
                self.process.send(f"{names[i]} = {var.__name__}")
            else:
                self.process.send(f"{names[i]} = {self.py_name}:recv()")
                self.process.send(var)

    def recv_vars(self, names) -> Any:
        if isinstance(names, str): 
            names = [names]
            cnvrt = lambda rtrn: rtrn[0]
        else: 
            cnvrt = lambda rtrn: tuple(rtrn)

        rtrn_vars = []
        for name in names:
            if name[:2] != "__" or name[:8] == "__last__":  # Check for private variables
                self.process.send(f"{self.py_name}:__err(true):send({name}):__err(false)")
                rtrn_vars.append(self.process.recv(name))
        
        return cnvrt(rtrn_vars)

    # -------------------------------------------------------------------------------------------------------------#
    
