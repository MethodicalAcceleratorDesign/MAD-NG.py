import tempfile, select, os, subprocess, sys
import numpy as np

#Working: mad.send("""send([==[self.send('''send([=[self.send("send([[print('hello world')]])")]=])''')]==])""")
#Working: mad.send("""send([=[self.send("send([[print('hello')]])")]=])""")

class madProcess:
    globalVars = {"np": np}

    def __init__(self) -> None:
        self.__tmpFldr = tempfile.TemporaryDirectory(prefix="pymadng-")
        self.pipeDir = self.__tmpFldr.name + "/pipe"
        os.mkfifo(self.pipeDir)

        self.process = subprocess.Popen(
            [os.path.dirname(os.path.abspath(__file__)) + "/mad",  "-q",  "-i"],
            bufsize=0,
            stdout=sys.stdout,
            stderr=sys.stdout,
            stdin=subprocess.PIPE,
        )
        self.send(f"""
        send = require ("madl_buffer").send
        local openPipe in require("madl_buffer")
        openPipe("{self.pipeDir}")
        """)

        self.pipe = os.open(self.pipeDir, os.O_RDONLY)
        self.pollIn = select.poll()
        self.pollIn.register(self.pipe, select.POLLIN)
        self.send("_PROMPT = ''") #Change this to change how output works

    def send(self, input: str) -> int:
        self.process.stdin.write(("load([==========[" + input + "]==========])()\n").encode("utf-8"))
        self.process.stdin.flush()
    
    def readPipe(self, timeout = 60):
        """Read the pipe, timing out after 'timeout' seconds."""
        if self.pollIn.poll(1000*timeout) == []:  # 1 Minute poll!
            raise(TimeoutError("Mad has not sent anything"))
        else:
            pipeText = os.read(self.pipe, 8192)
            code = compile(pipeText, "pipe", "exec")
            exec(code, self.globalVars, {"self": self})

    def __del__(self):
        self.__tmpFldr.cleanup()
        self.process.terminate()
        self.process.wait()