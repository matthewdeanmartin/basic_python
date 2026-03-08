import unittest
import math
from atari_basic import AtariBasic

class TestExhaustiveFunctions(unittest.TestCase):
    def setUp(self):
        self.interpreter = AtariBasic()

    def run_basic(self, code):
        return self.interpreter.run_and_capture(code).strip()

    def test_trig_functions(self):
        # Testing SIN, COS, TAN
        # Atari BASIC uses radians for math functions
        code = """
        10 PRINT SIN(0)
        20 PRINT COS(0)
        30 PRINT TAN(0)
        40 PRINT SIN(3.14159 / 2)
        """
        output = self.run_basic(code).splitlines()
        self.assertEqual(float(output[0]), 0.0)
        self.assertEqual(float(output[1]), 1.0)
        self.assertEqual(float(output[2]), 0.0)
        self.assertAlmostEqual(float(output[3]), 1.0, places=5)

    def test_log_exp_functions(self):
        code = """
        10 PRINT EXP(1)
        20 PRINT LOG(2.7182818)
        """
        output = self.run_basic(code).splitlines()
        self.assertAlmostEqual(float(output[0]), math.e, places=5)
        self.assertAlmostEqual(float(output[1]), 1.0, places=5)

    def test_rnd_function(self):
        # RND(0) returns 0 to 1
        # RND(-X) seeds the generator
        code = """
        10 A = RND(-42)
        20 B = RND(0)
        30 C = RND(-42)
        40 D = RND(0)
        50 PRINT B = D
        """
        # Since we seeded with the same value, B and D should be identical
        # Relational operator = returns 1 for True
        self.assertEqual(self.run_basic(code), "1")

    def test_string_conversion(self):
        code = """
        10 PRINT CHR$(65)
        20 PRINT ASC("B")
        30 PRINT STR$(123.45)
        40 PRINT VAL("67.89")
        """
        output = self.run_basic(code).splitlines()
        self.assertEqual(output[0], "A")
        self.assertEqual(output[1], "66")
        self.assertEqual(output[2], "123.45")
        self.assertEqual(output[3], "67.89")

    def test_relational_operators(self):
        code = """
        10 PRINT 5 = 5
        20 PRINT 5 <> 5
        30 PRINT 10 > 5
        40 PRINT 10 < 5
        50 PRINT 5 >= 5
        60 PRINT 5 <= 4
        """
        output = self.run_basic(code).splitlines()
        # 1 for True, 0 for False
        self.assertEqual(output, ["1", "0", "1", "0", "1", "0"])

    def test_string_relational(self):
        code = """
        10 DIM A$(10), B$(10)
        20 A$ = "APPLE": B$ = "BANANA"
        30 PRINT A$ < B$
        40 PRINT A$ = "APPLE"
        50 PRINT A$ <> B$
        """
        output = self.run_basic(code).splitlines()
        self.assertEqual(output, ["1", "1", "1"])

    def test_nested_functions(self):
        code = """
        10 PRINT INT(ABS(SGN(-5) * 10.5))
        """
        # SGN(-5) = -1
        # -1 * 10.5 = -10.5
        # ABS(-10.5) = 10.5
        # INT(10.5) = 10
        self.assertEqual(self.run_basic(code), "10")

if __name__ == '__main__':
    unittest.main()
