from pickletools import pynone
import tempfile, os, subprocess, sys, select, time
import numpy as np

# Working: mad.send("""py:send([==[mad.send('''py:send([=[mad.send("py:send([[print('hello world')]])")]=])''')]==])""")
# Working: mad.send("""py:send([=[mad.send("py:send([[print('hello')]])")]=])""")
# Working for me: mad.send("""send([==[mad.send(\"\"\"send([=[mad.send("send([[print('hello world')]])")]=])\"\"\")]==])""")


class madProcess:
    def __init__(self, pyName: str = "py", madPath: str = None, debug=False) -> None:
        self.pyName = pyName

        madPath = madPath or os.path.dirname(os.path.abspath(__file__)) + "/mad"

        self.pyInput, pyOutput = os.pipe()

        self.process = subprocess.Popen(
            [madPath, "-q", "-i"],
            bufsize=0,
            stdout=sys.stdout,
            stderr=sys.stderr,
            stdin=subprocess.PIPE,
            pass_fds=[pyOutput],
            # text=True,
        )
        os.close(pyOutput)

        if self.process.poll():  # Required?
            raise (
                OSError(
                    f"Unsuccessful opening of {madPath}, process closed immediately"
                )
            )

        self.globalVars = {"np": np}

        self.send(
            "MAD.pymad '"
            + pyName
            + "' {dispdbgf = "
            + str(debug).lower()
            + "} :publish() :open_pipe("
            + str(pyOutput)
            + ")"
        )
        self.fpyInput = os.fdopen(self.pyInput, "rb")
        self.pyInPoll = select.poll()
        self.pyInPoll.register(self.pyInput, select.POLLIN)
        self.send("_PROMPT  = ''")  # Change this to change how output works
        self.send("_PROMPT2 = ''")  # Change this to change how output works
        # print()

    def send(self, input: str):
        self.process.stdin.write(
            ("assert(load([==========[" + input + "]==========]))()\n").encode("utf-8")
        )

    def rawRead(self):
        bytesToRead = int(self.fpyInput.read(10))
        cmds = self.fpyInput.read(bytesToRead)
        if len(cmds) != bytesToRead:
            raise (
                EOFError(
                    "Too much data attempted to be written from MAD, the amount of data exceeded your free RAM"  # Check if universal!
                )
            )
        return cmds

    def read(self, env={}, timeout=10) -> dict:
        if self.pyInPoll.poll(1000 * timeout) == []:  # timeout seconds poll!
            raise (TimeoutError("No commands have been send to from MAD to Py!"))
        code = compile(self.rawRead(), "pyInput", "exec")
        env.update({"mad": self})
        exec(code, self.globalVars, env)
        # del env["mad"] # necessary?
        return env

    def __del__(self):
        self.process.terminate()
        self.process.wait()
