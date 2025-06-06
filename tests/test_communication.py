import threading
import unittest
from unittest.mock import patch

from pymadng import MAD


class TestExecution(unittest.TestCase):
    def test_recv_and_exec(self):
        with MAD() as mad:
            mad.send("""py:send([==[mad.send('''py:send([=[mad.send("py:send([[a = 100/2]])")]=])''')]==])""")
            mad.recv_and_exec()
            mad.recv_and_exec()
            a = mad.recv_and_exec()["a"]
            self.assertEqual(a, 50)

    def test_err(self):
        with MAD(stdout="/dev/null", redirect_stderr=True) as mad:
            mad.send("py:__err(true)")  
            mad.send("1+1") #Load error
            self.assertRaises(RuntimeError, mad.recv)
            mad.send("py:__err(true)")
            mad.send("print(nil/2)") #Runtime error
            self.assertRaises(RuntimeError, mad.recv)

class TestStrings(unittest.TestCase):
    def test_recv(self):
        with MAD() as mad:
            mad.send("py:send('hi')")
            mad.send("""py:send([[Multiline string should work

Like So.]])""")
            self.assertEqual(mad.recv(), 'hi')
            self.assertEqual(mad.receive(), 'Multiline string should work\n\nLike So.')

    def test_send(self):
        with MAD() as mad:
            initString = "asdfghjkl;"
            mad.send("str = py:recv(); py:send(str .. str)")
            mad.send(initString)
            self.assertEqual(mad.recv(), initString * 2)
            mad.send("str2 = py:recv(); py:send(str2 .. str2)")
            initString = """Py Multiline string should work

Like So.]])"""
            mad.send(initString)
            self.assertEqual(mad.recv(), initString * 2)

    def test_protected_send(self):
        with MAD(stdout="/dev/null", redirect_stderr=True, raise_on_madng_error=False) as mad:
            mad.send("py:send('hello world'); a = nil/2")
            self.assertEqual(mad.recv(), "hello world") # python should not crash
            mad.send("py:send(1)")
            self.assertEqual(mad.recv(), 1) # Check that the error did not affect the pipe
            
            mad.protected_send("a = nil/2")
            self.assertRaises(RuntimeError, mad.recv)   # python should receive an error
            
            mad.psend("a = nil/2")
            self.assertRaises(RuntimeError, mad.recv)


class TestOutput(unittest.TestCase):

    def test_print(self):
        with MAD() as mad:
            mad.send("py:send('hello world')")
            self.assertEqual(mad.recv(), "hello world") # Check printing does not affect pipe

class TestSignalHandler(unittest.TestCase):
    @patch("pymadng.madp_pymad.mad_process._setup_signal_handler")
    def test_signal_handler_called_in_main_thread(self, mock_setup_signal_handler):
        with patch("pathlib.Path.exists", return_value=True):
            MAD()
        mock_setup_signal_handler.assert_called_once()

    @patch("pymadng.madp_pymad.mad_process._setup_signal_handler")
    def test_signal_handler_not_called_in_non_main_thread(self, mock_setup_signal_handler):
        def create_mad_process():
            with patch("pathlib.Path.exists", return_value=True):
                MAD()

        thread = threading.Thread(target=create_mad_process)
        thread.start()
        thread.join()
        mock_setup_signal_handler.assert_not_called()

if __name__ == "__main__":
    unittest.main()