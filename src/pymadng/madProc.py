import tempfile, os, subprocess, sys, select, inspect
import numpy as np
import time

# Working: mad.send("""MAD.send([==[mad.send('''MAD.send([=[mad.send("MAD.send([[print('hello world')]])")]=])''')]==])""")
# Working: mad.send("""py.send([=[mad.send("py.send([[print('hello')]])")]=])""")
# Working for me: mad.send("""send([==[mad.send(\"\"\"send([=[mad.send("send([[print('hello world')]])")]=])\"\"\")]==])""")

class madProcess:
    def __init__(
        self, pyName: str = "py", madPath: str = None, debug = False
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

        if self.__process.poll(): # Required?
            raise(OSError(
                f"Unsuccessful opening of {madPath}, process closed immediately"
            ))

        self.globalVars = {"np": np}
        self.tmpFldr = tempfile.TemporaryDirectory(prefix="pymadng-")
        self.pipeName = self.tmpFldr.name + "/pipe"

        os.mkfifo(self.pipeName)

        self.send(
            "MAD.pymad '"
            + pyName
            + "' {dispdbgf = "
            + str(debug).lower()
            + "} :publish() :open_pipe('"
            + self.pipeName
            + "')"
        )
        self.pyInput = os.open(self.pipeName, os.O_RDONLY)
        self.pyInPoll = select.poll()
        self.pyInPoll.register(self.pyInput, select.POLLIN)
        self.send("_PROMPT  = ''")  # Change this to change how output works
        self.send("_PROMPT2 = ''")  # Change this to change how output works
        print()

    def send(self, input: str):
        self.__process.stdin.write(
            "assert(load([==========[" + input + "]==========]))()\n"
        )

    def read(self, env = {}, timeout = 10) -> dict:
        if self.pyInPoll.poll(1000 * timeout) == []:  # timeout seconds poll!
            raise(TimeoutError("No commands have been send to from MAD to Py!"))

        bytesToRead = int(os.read(self.pyInput, 8))
        cmds = os.read(self.pyInput, bytesToRead)
        while len(cmds) < bytesToRead:
            cmds += os.read(self.pyInput, bytesToRead - len(cmds))
        code = compile(cmds, "pyInput", "exec")

        env.update({"mad": self})
        exec(code, self.globalVars, env)
        # del env["mad"] # necessary?
        return env

    def __del__(self):
        self.__process.terminate()
        self.__process.wait()
        if hasattr(self, "tmpFldr"):
            self.tmpFldr.cleanup()
