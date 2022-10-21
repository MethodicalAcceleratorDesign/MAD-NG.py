import tempfile, os, subprocess, sys, select, inspect
import numpy as np

# Working: mad.send("""MAD.send([==[mad.send('''MAD.send([=[mad.send("MAD.send([[print('hello world')]])")]=])''')]==])""")
# Working: mad.send("""py.send([=[mad.send("py.send([[print('hello')]])")]=])""")
# Working for me: mad.send("""send([==[mad.send(\"\"\"send([=[mad.send("send([[print('hello world')]])")]=])\"\"\")]==])""")


class madProcess:
    def __init__(
        self, pyName: str = "py", madPath: str = None,
    ) -> None:
        self.pyName = pyName

        madPath = madPath or os.path.dirname(os.path.abspath(__file__)) + "/mad"

        self.__process = subprocess.Popen(
            [madPath, "-q", "-i"],
            bufsize=0,
            stdout=sys.stdout,
            stderr=sys.stderr,
            stdin=subprocess.PIPE,
            text=True,
        )

        self.globalVars = {"np": np}
        self.tmpFldr = tempfile.TemporaryDirectory(prefix="pymadng-")
        self.pipeName = self.tmpFldr.name + "/pipe"

        if self.__process.poll():
            raise(OSError(
                f"Unsuccessful opening of {madPath}, process closed immediately"
            ))
            
        os.mkfifo(self.pipeName)

        self.send(
            "MAD.pymad '"
            + pyName
            + "' {} :publish() :open_pipe('"
            + self.pipeName
            + "')"
        )
        self.pyInput = os.open(self.pipeName, os.O_RDONLY)
        self.pyInPoll = select.poll()
        self.pyInPoll.register(self.pyInput, select.POLLIN)
        self.send("_PROMPT  = ''")  # Change this to change how output works
        self.send("_PROMPT2 = ''")  # Change this to change how output works
        print()

    def send(self, input: str) -> int:
        self.__process.stdin.write(
            "assert(load([==========[" + input + "]==========]))()\n"
        )

    def read(self, timeout = 10):
        if self.pyInPoll.poll(1000 * timeout) == []:  # timeout seconds poll!
            raise(TimeoutError("No commands have been send to from MAD to Py!"))
        else:
            bytesToRead = int(os.read(self.pyInput, 8))
            cmds = os.read(self.pyInput, bytesToRead)
            while len(cmds) < bytesToRead:
                cmds += os.read(self.pyInput, bytesToRead - len(cmds))
            code = compile(cmds, "pyInput", "exec")
            # This will only change the scope that this function was called from
            userFrame = inspect.stack()[1][0] 
            exec(code, userFrame.f_globals, userFrame.f_locals)
            del userFrame # prevent reference cycle

    def __del__(self):
        self.__process.terminate()
        self.__process.wait()
        self.tmpFldr.cleanup()
