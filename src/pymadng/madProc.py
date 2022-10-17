import tempfile, select, os, re, subprocess, sys
import numpy as np

#Working: mad.send("""send([==[self.send('''send([=[self.send("send([[print('hello world')]])")]=])''')]==])""")
#Working: mad.send("""send([=[self.send("send([[print('hello')]])")]=])""")

class madProcess:
    globalVars = {"np": np}
    # pipe = None

    def __init__(self) -> None:
        self.__tmpFldr = tempfile.TemporaryDirectory(prefix="pymadng-") #I don't need temp files, with a temp dir
        self.__madScript = tempfile.mkstemp(prefix="madscript-", dir=self.__tmpFldr.name) #If named temporary file is used, cleanup errors occur
        self.__pyScript = tempfile.mkstemp(prefix="pyscript-", dir=self.__tmpFldr.name)
        
        self.pipeDir = self.__tmpFldr.name + "/pipe"
        os.mkfifo(self.pipeDir)

        self.process = subprocess.Popen(
            os.path.dirname(os.path.abspath(__file__)) + "/mad" + " -q" + " -i",
            shell=True,
            bufsize=0,
            stdout=sys.stdout,
            stderr=sys.stdout,
            stdin=subprocess.PIPE,
        )
        self.sendScript(f"""
        send = require ("madl_buffer").send
        local openPipe, setupScript in require("madl_buffer")
        openPipe("{self.pipeDir}")
        setupScript("{self.__pyScript[1]}")
        """)

        self.pipe = os.open(self.pipeDir, os.O_RDONLY)
        self.pollIn = select.poll()
        self.pollIn.register(self.pipe, select.POLLIN)
        self.send("_PROMPT = ''") #Change this to change how output works

    def send(self, input: str) -> int:
        self.process.stdin.write((input+"\n").encode("utf-8"))
        self.process.stdin.flush()

    def sendScript(self, fileInput: str) -> int:  
        with open(self.__madScript[1], "w") as file:
            file.write(fileInput)
        self.send(f'assert(loadfile("{self.__madScript[1]}"))()')
    
    def readPipe(self):
        if self.pollIn.poll(1000*60*1) == []:  # 1 Minute poll!
            raise(TimeoutError("Mad has not sent anything"))
        else:
            pipeText = os.read(self.pipe, 8192)#.decode("utf-8").replace("\x00", "")
            code = compile(pipeText, "pipe", "exec")
            exec(code, self.globalVars, {"self": self})

    def readScript(self):
        with open(self.__pyScript[1], "r") as file:
            code = compile(file.read(), self.__pyScript[1], "exec")
            exec(code, self.globalVars, {"self": self})

    def __del__(self):
        self.__tmpFldr.cleanup()
        self.process.terminate()
        self.process.wait()