import tempfile, os, subprocess, sys, select, time
import numpy as np

# Working: mad.send("""py:send([==[mad.send('''py:send([=[mad.send("py:send([[print('hello world')]])")]=])''')]==])""")
# Working: mad.send("""py:send([=[mad.send("py:send([[print('hello')]])")]=])""")
# Working for me: mad.send("""send([==[mad.send(\"\"\"send([=[mad.send("send([[print('hello world')]])")]=])\"\"\")]==])""")


class madProcess:
    def __init__(self, pyName: str = "py", madPath: str = None, debug=False) -> None:
        self.pyName = pyName

        madPath = madPath or os.path.dirname(os.path.abspath(__file__)) + "/mad"

        self.pyInput, madOutput = os.pipe()
        startupChunk  = "MAD.pymad '" + pyName + "' {dispdbgf = " + str(debug).lower() + "} :publish() :open_pipe(" + str(madOutput) + ")"

        self.process = subprocess.Popen(
            [madPath, "-q", "-e", startupChunk],
            bufsize=0,
            stdout=sys.stdout,
            stderr=sys.stderr,
            stdin=subprocess.PIPE,
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

        self.globalVars = {"np": np}
        self.fpyInput = os.fdopen(self.pyInput, "rb")
        self.pyInPoll = select.poll()
        self.pyInPoll.register(self.pyInput, select.POLLIN)

    def send(self, input: str):
        self.rawSend(input.encode("utf-8"))

    def rawSend(self, input: str):
        bytesToRead = len(input)
        self.process.stdin.write(f"{bytesToRead}".encode("utf-8"))
        self.process.stdin.write(input)

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
