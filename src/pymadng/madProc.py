import tempfile, select, os, re, subprocess, sys
import numpy as np

class madProcess:
    process = None
    mad_is_running_scipt = False
    pipeRead = ""
    globalVars = {"np": np}

    def __init__(self) -> None:
        # Init temp files
        self.__tmpFldr = tempfile.TemporaryDirectory(prefix="pymadng-")
        self.__madScript = tempfile.NamedTemporaryFile(prefix="madscript-", dir=self.__tmpFldr)
        self.__pyScript = tempfile.NamedTemporaryFile(prefix="pyscript-", dir=self.__tmpFldr)
        
        self.PATH_TO_MAD = os.path.dirname(os.path.abspath(__file__)) + "/mad"
        self.pipeDir = self.__tmpFldr + "pipe"

        # Setup communication pipe
        os.mkfifo(self.pipeDir)

        # Create initial file when MAD process is created
        INITIALISE_SCRIPT = f"""
        writeToPipe, setupScript = require ("madl_buffer").writeToPipe, require ("madl_buffer").setupScript
        local openPipe in require("madl_buffer")
        openPipe("{self.pipeDir}")
        setupScript("{self.__pyScript.name}")
        """

        # shell = True; security problems?
        self.process = subprocess.Popen(
            self.PATH_TO_MAD + " -q" + " -i",
            shell=True,
            bufsize=0,
            stdout=sys.stdout,
            stderr=sys.stdout,
            stdin=subprocess.PIPE,
        )  # , universal_newlines=True)
        try:  # See if it closes in 10 ms (1 ms is too quick)
            self.process.wait(0.1)
            self.close()
            raise (
                OSError(
                    f"Unsuccessful opening of {self.PATH_TO_MAD}, process closed immediately"
                )
            )
        except subprocess.TimeoutExpired:
            pass

        # Wait for mad to be ready for input
        self.sendScript(INITIALISE_SCRIPT, False)

        # Now read from pipe as write end is open
        self.pipe = os.open(self.pipeDir, os.O_RDONLY)
        self.pollIn = select.poll()
        self.pollIn.register(self.pipe, select.POLLIN)
        self.writeToProcess("_PROMPT = ''") #Change this to change how output works

        def __del__(self):
            self.__tmpFldr.cleanup()