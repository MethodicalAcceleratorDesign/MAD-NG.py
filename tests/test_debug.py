import unittest
from pathlib import Path
from pymadng import MAD
import time

inputs_folder = Path(__file__).parent / "inputs"

class TestDebug(unittest.TestCase):
    test_log1 = inputs_folder / "test.log"

    def test_logfile(self):
        example_log = inputs_folder / "example.log"
        test_log2 = inputs_folder / "test2.log"

        with MAD(stdout=self.test_log1, debug=True, raise_on_madng_error=False) as mad: 
            pass
        time.sleep(0.1) # Wait for file to be written
        with open(self.test_log1, "r") as f:
            with open(example_log, "r") as f2:
                self.assertEqual(f.read(), f2.read())
        
        with MAD(stdout=test_log2, debug=True) as mad:
            mad.send("!This is a line that does nothing")
            mad.send("print('hello world')")

        with open(test_log2) as f:
            text = f.read()
            self.assertTrue("[!This is a line that does nothing]" in text)
            self.assertTrue("hello world\n" in text)
            self.assertTrue("[print('hello world')]" in text)

        with MAD(stdout=test_log2, debug=False) as mad:
            mad.send("!This is a line that does nothing")
            mad.send("print('hello world')")
        
        with open(test_log2) as f:
            self.assertEqual(f.read(), "hello world\n")

        self.test_log1.unlink()
        test_log2.unlink()

    def test_err(self):
        # Run debug without stderr redirection
        with open(self.test_log1, "w") as f:
            with MAD(debug=True, stdout=f, raise_on_madng_error=False) as mad:
                mad.psend("a = nil/2")
                # receive the error before closing the pipe
                self.assertRaises(RuntimeError, mad.recv)
        with open(self.test_log1) as f:
            # Check command was sent
            file_text = f.read()
            self.assertTrue("[py:__err(true); a = nil/2; py:__err(false);]" in file_text)
            # Check error was not in stdout
            self.assertFalse("***pymad.run:" in file_text)

        # Run debug with stderr redirection
        with MAD(stdout=self.test_log1, redirect_stderr=True) as mad:
            mad.psend("a = nil/2")
            # receive the error before closing the pipe
            self.assertRaises(RuntimeError, mad.recv) 
        with open(self.test_log1) as f:
            # Check command was sent
            file_text = f.read()
            # Check error was in stdout
            self.assertEqual("***pymad.run:", file_text[:13])
        self.test_log1.unlink()

if __name__ == '__main__':
    unittest.main()