import tempfile, os, subprocess, sys
import numpy as np

#Working: mad.send("""MAD.send([==[mad.send('''MAD.send([=[mad.send("MAD.send([[print('hello world')]])")]=])''')]==])""")
#Working: mad.send("""MAD.send([=[mad.send("MAD.send([[print('hello')]])")]=])""")
#Working for me: mad.send("""send([==[mad.send(\"\"\"send([=[mad.send("send([[print('hello world')]])")]=])\"\"\")]==])""")

class madProcess:
    globalVars = {"np": np}

    def __init__(self, className: str = "mad", pathToMAD: str = None) -> None:
        self.className = className
        self.tmpFldr = tempfile.TemporaryDirectory(prefix="pymadng-")
        self.pipeDir = self.tmpFldr.name + "/pipe"
        os.mkfifo(self.pipeDir)
        
        pathToMAD = pathToMAD or os.path.dirname(os.path.abspath(__file__)) + "/mad"
        self.process = subprocess.Popen(
            [pathToMAD,  "-q",  "-i"],
            bufsize=0,
            stdout=sys.stdout,
            stderr=sys.stdout,
            stdin=subprocess.PIPE,
            text=True
        )
        self.send(f"""
        send = require ("madl_pymad").send
        local openPipeToPython in require("madl_pymad")
        openPipeToPython("{self.pipeDir}")
        """)

        self.MADToPyPipe = os.open(self.pipeDir, os.O_RDONLY)
        self.send("_PROMPT = ''") #Change this to change how output works

    def send(self, input: str) -> int:
        self.process.stdin.write(("load([==========[" + input + "]==========])()\n"))
    
    def read(self):
        pipeText = os.read(self.MADToPyPipe, 8192)
        code = compile(pipeText, "pipe", "exec")
        exec(code, self.globalVars, {self.className: self})

    def __del__(self):
        self.tmpFldr.cleanup()
        self.process.terminate()
        self.process.wait()