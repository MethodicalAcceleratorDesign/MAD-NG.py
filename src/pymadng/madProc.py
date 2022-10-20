import tempfile, os, subprocess, sys, select
import numpy as np

# Working: mad.send("""MAD.send([==[mad.send('''MAD.send([=[mad.send("MAD.send([[print('hello world')]])")]=])''')]==])""")
# Working: mad.send("""py.send([=[mad.send("py.send([[print('hello')]])")]=])""")
# Working for me: mad.send("""send([==[mad.send(\"\"\"send([=[mad.send("send([[print('hello world')]])")]=])\"\"\")]==])""")


class madProcess:
    def __init__(
        self, madName: str = "mad", pyName: str = "py", madPath: str = None
    ) -> None:
        self.madName = madName
        self.pyName = pyName

        madPath = madPath or os.path.dirname(os.path.abspath(__file__)) + "/mad"

        self.process = subprocess.Popen(
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
        self.send("_PROMPT = ''")  # Change this to change how output works

    def send(self, input: str) -> int:
        self.process.stdin.write(
            "assert(load([==========[" + input + "]==========]))()\n"
        )

    def read(self, timeout = 10):
        if self.pyInPoll.poll(1000 * timeout) == []:  # timeout seconds poll!
            raise(TimeoutError("No commands have been send to from MAD to Py!"))
        else:
            cmds = os.read(self.pyInput, 8192)
            code = compile(cmds, "pyInput", "exec")
            exec(code, self.globalVars, {self.madName: self})

    def __del__(self):
        self.process.terminate()
        self.process.wait()
        self.tmpFldr.cleanup()
