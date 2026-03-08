import unittest
import io
import os
from atari_basic import AtariBasic, BasicError

class TestAtariBasic(unittest.TestCase):
    def setUp(self):
        self.interpreter = AtariBasic()

    def run_basic(self, code):
        """Helper to run code and return stdout."""
        return self.interpreter.run_and_capture(code).strip()

    def test_arithmetic(self):
        code = """
        10 PRINT 2 + 2
        20 PRINT 10 - 4
        30 PRINT 3 * 4
        40 PRINT 12 / 3
        50 PRINT 2 ^ 3
        60 PRINT (2 + 3) * 4
        """
        output = self.run_basic(code).splitlines()
        self.assertEqual(output, ["4", "6", "12", "4", "8", "20"])

    def test_variables(self):
        code = """
        10 A = 10
        20 LET B = 20
        30 C = A + B
        40 PRINT C
        """
        self.assertEqual(self.run_basic(code), "30")

    def test_strings(self):
        code = """
        10 DIM A$(20), B$(20)
        20 A$ = "HELLO"
        30 B$ = " WORLD"
        40 PRINT A$ + B$
        50 PRINT LEN(A$)
        """
        output = self.run_basic(code).splitlines()
        self.assertEqual(output, ["HELLO WORLD", "5"])

    def test_arrays(self):
        code = """
        10 DIM A(5)
        20 A(0) = 10
        30 A(5) = 50
        40 PRINT A(0) + A(5)
        """
        self.assertEqual(self.run_basic(code), "60")

    def test_for_next(self):
        code = """
        10 FOR I = 1 TO 5
        20 PRINT I;
        30 NEXT I
        """
        self.assertEqual(self.run_basic(code), "12345")

    def test_for_next_step(self):
        code = """
        10 FOR I = 10 TO 0 STEP -2
        20 PRINT I;
        30 NEXT I
        """
        self.assertEqual(self.run_basic(code), "1086420")

    def test_if_then(self):
        code = """
        10 A = 10
        20 IF A > 5 THEN PRINT "BIG"
        30 IF A < 5 THEN PRINT "SMALL"
        40 IF A = 10 THEN GOTO 60
        50 PRINT "FAILED"
        60 PRINT "DONE"
        """
        output = self.run_basic(code).splitlines()
        self.assertEqual(output, ["BIG", "DONE"])

    def test_gosub_return(self):
        code = """
        10 PRINT "START"
        20 GOSUB 100
        30 PRINT "BACK"
        40 END
        100 PRINT "SUB"
        110 RETURN
        """
        output = self.run_basic(code).splitlines()
        self.assertEqual(output, ["START", "SUB", "BACK"])

    def test_functions(self):
        code = """
        10 PRINT INT(3.7)
        20 PRINT ABS(-10)
        30 PRINT SQR(16)
        40 PRINT SGN(-5)
        50 PRINT VAL("123")
        60 PRINT STR$(456)
        """
        output = self.run_basic(code).splitlines()
        self.assertEqual(output, ["3", "10", "4", "-1", "123", "456"])

    def test_error_undimensioned(self):
        # Atari BASIC doesn't support single quotes for strings
        # It should throw a Syntax Error (which maps to BasicError in our runner)
        # However, run_and_capture catches BasicError and prints it to stdout.
        # We need to test the underlying execute_code for exception raising.
        
        with self.assertRaises(BasicError):
            self.interpreter.execute_code("10 A$ = \"HELLO\"") # This one is fine
            self.interpreter.execute_code("20 B$ = \"BYE\"")   # Error: B$ not DIM'd
            
        self.interpreter.reset()
        with self.assertRaises(BasicError):
            self.interpreter.execute_code("10 A(1) = 10")    # Error: A not DIM'd

    def test_file_io(self):
        test_file = "test_io.txt"
        try:
            code_write = f"""
            10 OPEN #1, "{test_file}", "w"
            20 PRINT #1, "HELLO FILE"
            30 PRINT #1, 123
            40 CLOSE #1
            """
            self.interpreter.execute_code(code_write)
            
            code_read = f"""
            10 DIM S$(20)
            20 OPEN #1, "{test_file}", "r"
            30 INPUT #1, S$
            40 INPUT #1, N
            50 PRINT S$
            60 PRINT N
            70 CLOSE #1
            """
            output = self.run_basic(code_read).splitlines()
            self.assertEqual(output, ["HELLO FILE", "123"])
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    def test_inject_variable(self):
        self.interpreter.inject_variable("X", 42)
        self.interpreter.inject_variable("NAME$", "GEMINI")
        # Use execute_repl_line directly to avoid reset() in execute_code/run_and_capture
        buf = io.StringIO()
        self.interpreter.out_stream = buf
        self.interpreter.execute_repl_line("PRINT NAME$; \" \"; X")
        self.assertEqual(buf.getvalue().strip(), "GEMINI 42")

    def test_repl_delete_line(self):
        self.interpreter.execute_repl_line("10 PRINT 1")
        self.interpreter.execute_repl_line("20 PRINT 2")
        self.interpreter.execute_repl_line("10") # Delete line 10
        
        buf = io.StringIO()
        self.interpreter.out_stream = buf
        self.interpreter.execute_repl_line("RUN")
        self.assertEqual(buf.getvalue().strip(), "2")

if __name__ == '__main__':
    unittest.main()
