# translated from
# https://github.com/davepl/pdpsrc/blob/main/bsd/basic/basic.c
# With help of Gemini 3.5

import sys
import math
import random
import time
import re
from typing import List, Dict, Optional, Union, Any, Tuple
from dataclasses import dataclass, field

# --- Configuration Constants ---
MAX_STR_LEN = 256
DEFAULT_ARRAY_SIZE = 11
PRINT_WIDTH = 80


# --- Exceptions ---
class BasicRuntimeError(Exception):
    """Custom exception for runtime errors in the interpreter."""
    pass


# --- Data Structures ---

@dataclass
class Line:
    """Represents a single line of BASIC code."""
    number: int
    text: str


@dataclass
class GosubFrame:
    """Stack frame for GOSUB/RETURN."""
    line_index: int
    resume_pos: int


@dataclass
class ForFrame:
    """Stack frame for FOR/NEXT loops."""
    var_name: str
    end_value: float
    step: float
    line_index: int
    resume_pos: int


class Scanner:
    """
    Manages parsing position within a string.
    Acts as the equivalent of the 'char **p' pointer in the C code.
    """

    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.length = len(text)

    def remaining(self) -> str:
        return self.text[self.pos:]

    def peek(self) -> str:
        if self.pos < self.length:
            return self.text[self.pos]
        return ""

    def advance(self, count: int = 1):
        self.pos = min(self.pos + count, self.length)

    def skip_spaces(self):
        while self.pos < self.length and self.text[self.pos] in (' ', '\t'):
            self.pos += 1

    def match_keyword(self, keyword: str) -> bool:
        """
        Checks if the current position starts with a keyword (case-insensitive).
        Ensures the keyword is followed by a delimiter or space.
        """
        rem = self.remaining()
        if not rem.upper().startswith(keyword.upper()):
            return False

        # Check boundary
        end_idx = len(keyword)
        if end_idx >= len(rem):
            return True

        char_after = rem[end_idx]
        if char_after in (' ', '\t', ':', '(', ')', '<', '>', '='):
            return True
        return False

    def consume_keyword(self, keyword: str) -> bool:
        if self.match_keyword(keyword):
            self.pos += len(keyword)
            return True
        return False


# --- The Interpreter ---

class BasicInterpreter:
    def __init__(self):
        self.lines: List[Line] = []
        self.vars: Dict[str, Any] = {}  # Scalar variables
        self.arrays: Dict[str, List[Any]] = {}  # Array variables

        self.gosub_stack: List[GosubFrame] = []
        self.for_stack: List[ForFrame] = []

        self.current_line_index: int = 0
        self.scanner: Optional[Scanner] = None
        self.halted: bool = False
        self.print_col: int = 0

    def load_program_from_file(self, filepath: str):
        try:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                for raw_line in f:
                    raw_line = raw_line.strip()
                    if not raw_line:
                        continue

                    # Split into line number and text
                    match = re.match(r'^(\d+)\s*(.*)', raw_line)
                    if not match:
                        continue

                    num = int(match.group(1))
                    text = match.group(2)
                    self._add_line(num, text)

            # Sort lines by number
            self.lines.sort(key=lambda x: x.number)

        except FileNotFoundError:
            print(f"Error: Cannot open {filepath}")
            sys.exit(1)

    def _add_line(self, number: int, text: str):
        # Remove existing line if it exists
        self.lines = [l for l in self.lines if l.number != number]
        self.lines.append(Line(number, text))

    def run(self):
        self.halted = False
        self.current_line_index = 0
        self.scanner = None
        self.print_col = 0

        while not self.halted and 0 <= self.current_line_index < len(self.lines):
            # precise logic to handle multi-statement lines (colon separated)
            if self.scanner is None:
                line_obj = self.lines[self.current_line_index]
                self.scanner = Scanner(line_obj.text)

            self.scanner.skip_spaces()
            if self.scanner.peek() == "":
                # End of line, move to next
                self.current_line_index += 1
                self.scanner = None
                continue

            self._execute_statement()

            if self.halted:
                break

            # If scanner is still active, check for separator or end
            if self.scanner:
                self.scanner.skip_spaces()
                char = self.scanner.peek()
                if char == ':':
                    self.scanner.advance()
                    continue
                elif char == "":
                    self.current_line_index += 1
                    self.scanner = None
                else:
                    # Trailing junk or implicit execution?
                    # The C code usually stops or moves next.
                    # We'll assume move next line if not a separator.
                    self.current_line_index += 1
                    self.scanner = None

    def _error(self, message: str):
        print(f"\nError: {message}")
        self.halted = True
        raise BasicRuntimeError(message)

    # --- Variable Handling ---

    def _normalize_name(self, name: str) -> Tuple[str, bool]:
        """
        CBM BASIC v2 limits variable names to 2 characters + type suffix.
        Returns (Key, IsString)
        """
        is_string = name.endswith('$')
        clean_name = name[:-1] if is_string else name

        # Take first 2 chars, uppercase
        if len(clean_name) >= 2:
            key = clean_name[:2].upper()
        elif len(clean_name) == 1:
            key = clean_name[0].upper() + " "
        else:
            return "", False  # Should not happen

        if is_string:
            key += "$"

        return key, is_string

    def _get_var_ref(self) -> Tuple[str, bool, int]:
        """
        Parses a variable identifier.
        Returns: (Normalized Key, IsArray, ArrayIndex)
        ArrayIndex is -1 if scalar.
        """
        if not self.scanner: raise BasicRuntimeError("Scanner error")

        self.scanner.skip_spaces()
        match = re.match(r'^[A-Za-z][A-Za-z0-9]*\$?', self.scanner.remaining())
        if not match:
            self._error("Expected variable")
            return "", False, 0

        raw_name = match.group(0)
        self.scanner.advance(len(raw_name))

        key, is_string = self._normalize_name(raw_name)

        self.scanner.skip_spaces()
        is_array = False
        idx = -1

        if self.scanner.peek() == '(':
            is_array = True
            self.scanner.advance()
            idx_val = self._eval_expr()

            if not isinstance(idx_val, (int, float)):
                self._error("Array index must be numeric")

            self.scanner.skip_spaces()
            if self.scanner.peek() != ')':
                self._error("Missing ')'")
            self.scanner.advance()

            idx = int(idx_val)
            if idx < 0:
                self._error("Negative array index")

        # Auto-initialize if missing
        if is_array:
            if key not in self.arrays:
                # Default size 11 (0-10)
                default_val = "" if is_string else 0.0
                self.arrays[key] = [default_val] * DEFAULT_ARRAY_SIZE

            # Auto-resize if index out of bounds
            if idx >= len(self.arrays[key]):
                extension_size = idx - len(self.arrays[key]) + 1
                default_val = "" if is_string else 0.0
                self.arrays[key].extend([default_val] * extension_size)
        else:
            if key not in self.vars:
                self.vars[key] = "" if is_string else 0.0

        return key, is_array, idx

    def _set_variable(self, val: Union[float, str]):
        key, is_array, idx = self._get_var_ref()

        is_string_var = key.endswith('$')
        is_val_string = isinstance(val, str)

        if is_string_var != is_val_string:
            self._error("Type mismatch")

        if is_array:
            self.arrays[key][idx] = val
        else:
            self.vars[key] = val

    def _get_variable_value(self, key: str, is_array: bool, idx: int) -> Union[float, str]:
        if is_array:
            if key not in self.arrays:
                # Should have been created by _get_var_ref logic inside caller or previous DIM
                self._error(f"Undefined array {key}")
            if idx >= len(self.arrays[key]):
                self._error("Array index out of bounds")
            return self.arrays[key][idx]
        else:
            return self.vars.get(key, "" if key.endswith('$') else 0.0)

    # --- Expression Evaluation (Recursive Descent) ---

    def _eval_expr(self) -> Union[float, str]:
        left = self._eval_term()
        while self.scanner:
            self.scanner.skip_spaces()
            op = self.scanner.peek()
            if op in ('+', '-'):
                self.scanner.advance()
                right = self._eval_term()
                if op == '+':
                    if isinstance(left, str) or isinstance(right, str):
                        left = str(left) + str(right)
                    else:
                        left = left + right
                else:
                    if isinstance(left, str) or isinstance(right, str):
                        self._error("Cannot subtract strings")
                    left = float(left) - float(right)  # type: ignore
            else:
                break
        return left

    def _eval_term(self) -> Union[float, str]:
        left = self._eval_power()
        while self.scanner:
            self.scanner.skip_spaces()
            op = self.scanner.peek()
            if op in ('*', '/'):
                self.scanner.advance()
                right = self._eval_power()
                if isinstance(left, str) or isinstance(right, str):
                    self._error("Type mismatch in math operation")

                if op == '*':
                    left = float(left) * float(right)  # type: ignore
                else:
                    if float(right) == 0:
                        self._error("Division by zero")
                    left = float(left) / float(right)  # type: ignore
            else:
                break
        return left

    def _eval_power(self) -> Union[float, str]:
        left = self._eval_factor()
        self.scanner.skip_spaces()
        if self.scanner and self.scanner.peek() == '^':
            self.scanner.advance()
            right = self._eval_power()
            if isinstance(left, str) or isinstance(right, str):
                self._error("Type mismatch in power")
            return math.pow(float(left), float(right))  # type: ignore
        return left

    def _eval_factor(self) -> Union[float, str]:
        if not self.scanner: raise BasicRuntimeError("Scanner error")
        self.scanner.skip_spaces()
        char = self.scanner.peek()

        # Parentheses
        if char == '(':
            self.scanner.advance()
            val = self._eval_expr()
            self.scanner.skip_spaces()
            if self.scanner.peek() != ')':
                self._error("Missing ')'")
            self.scanner.advance()
            return val

        # String Literal
        if char == '"':
            self.scanner.advance()
            start = self.scanner.pos
            while self.scanner.peek() != '"' and self.scanner.peek() != "":
                self.scanner.advance()

            text = self.scanner.text[start: self.scanner.pos]
            if self.scanner.peek() == '"':
                self.scanner.advance()
            else:
                self._error("Unterminated string")
            return text

        # Unary Minus
        if char == '-':
            self.scanner.advance()
            val = self._eval_factor()
            if isinstance(val, str):
                self._error("Type mismatch (negating string)")
            return -val

        # Unary Plus
        if char == '+':
            self.scanner.advance()
            return self._eval_factor()

        # Functions
        rem = self.scanner.remaining().upper()
        for func in ["SIN", "COS", "TAN", "ABS", "INT", "SQR", "SGN", "EXP", "LOG", "RND", "LEN", "VAL", "STR$", "CHR$",
                     "ASC", "TAB"]:
            # Need to ensure func is followed by ( or space, not part of variable name
            if self.scanner.match_keyword(func):
                self.scanner.advance(len(func))
                self.scanner.skip_spaces()
                if self.scanner.peek() != '(':
                    self._error(f"Function {func} requires '('")
                self.scanner.advance()
                arg = self._eval_expr()
                self.scanner.skip_spaces()
                if self.scanner.peek() != ')':
                    self._error("Missing ')'")
                self.scanner.advance()
                return self._apply_function(func, arg)

        # Numbers
        # Regex to capture float or integer
        num_match = re.match(r'^[0-9]*\.?[0-9]+([eE][+-]?[0-9]+)?', self.scanner.remaining())
        if num_match:
            val_str = num_match.group(0)
            self.scanner.advance(len(val_str))
            return float(val_str)

        # Variable (Must be checked last as it starts with letters)
        if char.isalpha():
            key, is_arr, idx = self._get_var_ref()
            return self._get_variable_value(key, is_arr, idx)

        self._error("Syntax error in expression")
        return 0.0

    def _apply_function(self, func: str, arg: Union[float, str]) -> Union[float, str]:
        if func == "SIN": return math.sin(float(arg))
        if func == "COS": return math.cos(float(arg))
        if func == "TAN": return math.tan(float(arg))
        if func == "ABS": return abs(float(arg))  # type: ignore
        if func == "INT": return math.floor(float(arg))
        if func == "SQR": return math.sqrt(float(arg))
        if func == "SGN": return 1.0 if float(arg) > 0 else (-1.0 if float(arg) < 0 else 0.0)
        if func == "EXP": return math.exp(float(arg))
        if func == "LOG": return math.log(float(arg))
        if func == "RND":
            if float(arg) < 0: random.seed(abs(float(arg)))
            return random.random()
        if func == "LEN": return float(len(str(arg)))
        if func == "VAL":
            try:
                return float(str(arg))
            except ValueError:
                return 0.0
        if func == "STR$": return str(float(arg))
        if func == "CHR$": return chr(int(arg))
        if func == "ASC": return float(ord(str(arg)[0])) if str(arg) else 0.0

        if func == "TAB":
            # TAB is technically a print control, but often parsed in exprs in simple interpreters
            # In this architecture, we return a string of spaces
            target = int(arg)
            current = self.print_col % PRINT_WIDTH
            if target < current:
                return "\n" + (" " * target)
            return " " * (target - current)

        return 0.0

    def _eval_condition(self) -> bool:
        left = self._eval_expr()
        self.scanner.skip_spaces()
        if not self.scanner: return False  # Should not happen

        # Look for operator
        op = ""
        rem = self.scanner.remaining()
        if rem.startswith("<="):
            op = "<="
        elif rem.startswith(">="):
            op = ">="
        elif rem.startswith("<>"):
            op = "<>"
        elif rem.startswith("<"):
            op = "<"
        elif rem.startswith(">"):
            op = ">"
        elif rem.startswith("="):
            op = "="

        if not op:
            # BASIC allows "IF X THEN" where X!=0 is true
            if isinstance(left, str): return len(left) > 0
            return float(left) != 0.0

        self.scanner.advance(len(op))
        right = self._eval_expr()

        # Type check
        if isinstance(left, str) != isinstance(right, str):
            self._error("Type mismatch in comparison")

        if op == "=": return left == right
        if op == "<>": return left != right
        if op == "<": return left < right  # type: ignore
        if op == ">": return left > right  # type: ignore
        if op == "<=": return left <= right  # type: ignore
        if op == ">=": return left >= right  # type: ignore
        return False

    # --- Statements ---

    def _execute_statement(self):
        if not self.scanner: return
        self.scanner.skip_spaces()
        rem = self.scanner.remaining().upper()

        # Check for empty or comment
        if not rem or rem.startswith("'") or rem.startswith("REM"):
            self.scanner.pos = self.scanner.length  # Skip rest of line
            return

        if self.scanner.peek() == '?':
            self.scanner.advance()
            self._stmt_print()
            return

        # Keyword mapping
        if self.scanner.consume_keyword("PRINT"):
            self._stmt_print()
        elif self.scanner.consume_keyword("INPUT"):
            self._stmt_input()
        elif self.scanner.consume_keyword("LET"):
            self._stmt_let()
        elif self.scanner.consume_keyword("GOTO"):
            self._stmt_goto()
        elif self.scanner.consume_keyword("GOSUB"):
            self._stmt_gosub()
        elif self.scanner.consume_keyword("RETURN"):
            self._stmt_return()
        elif self.scanner.consume_keyword("IF"):
            self._stmt_if()
        elif self.scanner.consume_keyword("FOR"):
            self._stmt_for()
        elif self.scanner.consume_keyword("NEXT"):
            self._stmt_next()
        elif self.scanner.consume_keyword("DIM"):
            self._stmt_dim()
        elif self.scanner.consume_keyword("SLEEP"):
            self._stmt_sleep()
        elif self.scanner.consume_keyword("END"):
            self.halted = True
        elif self.scanner.consume_keyword("STOP"):
            self.halted = True
        elif self.scanner.remaining()[0].isalpha():
            # Implicit LET
            self._stmt_let()
        else:
            self._error("Unknown statement")

    def _stmt_print(self):
        newline = True
        while self.scanner and self.scanner.pos < self.scanner.length:
            self.scanner.skip_spaces()
            char = self.scanner.peek()
            if char == ':' or char == "": break

            if char == ';':
                newline = False
                self.scanner.advance()
                continue
            elif char == ',':
                newline = False
                self.scanner.advance()
                # Zone logic (10 chars wide)
                cur_zone = self.print_col // 10
                next_pos = (cur_zone + 1) * 10
                spaces = next_pos - self.print_col
                print(" " * spaces, end='')
                self.print_col += spaces
                continue

            val = self._eval_expr()

            # Format output
            out_str = ""
            if isinstance(val, float):
                if val == int(val):
                    out_str = f" {int(val)} "
                else:
                    out_str = f" {val} "
            else:
                out_str = str(val)

            print(out_str, end='')

            # Update column (handling potential newlines inside strings)
            lines = out_str.split('\n')
            if len(lines) > 1:
                self.print_col = len(lines[-1])
            else:
                self.print_col += len(lines[0])

            if self.print_col >= PRINT_WIDTH:
                print()
                self.print_col = 0

            newline = True

        if newline:
            print()
            self.print_col = 0

        sys.stdout.flush()

    def _stmt_input(self):
        self.scanner.skip_spaces()
        prompt = "? "

        # Check for prompt string
        if self.scanner.peek() == '"':
            prompt_val = self._eval_factor()
            if isinstance(prompt_val, str):
                prompt = prompt_val
            self.scanner.skip_spaces()
            if self.scanner.peek() in (';', ','):
                self.scanner.advance()

        while True:
            self.scanner.skip_spaces()
            key, is_array, idx = self._get_var_ref()
            is_string_var = key.endswith('$')

            try:
                raw_in = input(prompt)
            except EOFError:
                self._error("Unexpected end of input")
                return

            val: Union[float, str]
            if is_string_var:
                val = raw_in
            else:
                try:
                    val = float(raw_in)
                except ValueError:
                    val = 0.0  # BASIC behavior on bad input type

            if is_array:
                self.arrays[key][idx] = val
            else:
                self.vars[key] = val

            self.scanner.skip_spaces()
            if self.scanner.peek() == ',':
                self.scanner.advance()
                prompt = "? "  # Subsequent prompts usually just ?
                continue
            break

    def _stmt_let(self):
        self._set_variable(0)  # Logic handled inside set_variable

        # Note: _set_variable calls _get_var_ref which consumes the name.
        # But _set_variable logic needs to see the "=" and the RHS.
        # Let's rewrite this slightly because _set_variable was designed abstractly above.
        # Re-implementing logic here for linear flow:

        # 1. Backtrack? No, let's just parse manually here.
        pass

    # Override the _stmt_let because the abstract helper I wrote earlier was a bit too abstract
    def _stmt_let(self):
        # 1. Parse LHS
        key, is_array, idx = self._get_var_ref()

        self.scanner.skip_spaces()
        if self.scanner.peek() != '=':
            self._error("Expected '='")
        self.scanner.advance()

        # 2. Parse RHS
        val = self._eval_expr()

        # 3. Type check and Assignment
        is_str_var = key.endswith('$')
        is_str_val = isinstance(val, str)

        if is_str_var != is_str_val:
            self._error("Type mismatch")

        if is_array:
            self.arrays[key][idx] = val
        else:
            self.vars[key] = val

    def _find_line(self, line_num: int) -> int:
        for i, line in enumerate(self.lines):
            if line.number == line_num:
                return i
        return -1

    def _stmt_goto(self):
        self.scanner.skip_spaces()
        match = re.match(r'^\d+', self.scanner.remaining())
        if not match:
            self._error("Expected line number")
            return

        target = int(match.group(0))
        self.scanner.advance(len(match.group(0)))

        idx = self._find_line(target)
        if idx == -1:
            self._error(f"Line {target} not found")

        self.current_line_index = idx
        self.scanner = None  # Reset scanner to force load of new line

    def _stmt_gosub(self):
        self.scanner.skip_spaces()
        match = re.match(r'^\d+', self.scanner.remaining())
        if not match:
            self._error("Expected line number")
            return

        target = int(match.group(0))
        self.scanner.advance(len(match.group(0)))

        idx = self._find_line(target)
        if idx == -1:
            self._error(f"Line {target} not found")

        # Push return address
        frame = GosubFrame(self.current_line_index, self.scanner.pos)
        self.gosub_stack.append(frame)

        self.current_line_index = idx
        self.scanner = None

    def _stmt_return(self):
        if not self.gosub_stack:
            self._error("RETURN without GOSUB")

        frame = self.gosub_stack.pop()
        self.current_line_index = frame.line_index
        # Restore scanner to that line and position
        self.scanner = Scanner(self.lines[self.current_line_index].text)
        self.scanner.pos = frame.resume_pos

    def _stmt_if(self):
        condition = self._eval_condition()
        self.scanner.skip_spaces()

        if not self.scanner.consume_keyword("THEN"):
            self._error("Expected THEN")

        if condition:
            self.scanner.skip_spaces()
            # Handle "IF X THEN 100" shorthand
            if re.match(r'^\d', self.scanner.remaining()):
                self._stmt_goto()
            else:
                # Continue execution on this line
                pass
        else:
            # Skip rest of line
            self.scanner.pos = self.scanner.length

    def _stmt_for(self):
        key, is_array, idx = self._get_var_ref()
        if is_array: self._error("FOR variable cannot be an array")
        if key.endswith('$'): self._error("FOR variable must be numeric")

        self.scanner.skip_spaces()
        if self.scanner.peek() != '=': self._error("Expected '='")
        self.scanner.advance()

        start_val = self._eval_expr()
        if not isinstance(start_val, (int, float)): self._error("Numeric required")

        self.scanner.skip_spaces()
        if not self.scanner.consume_keyword("TO"): self._error("Expected TO")

        end_val = self._eval_expr()
        if not isinstance(end_val, (int, float)): self._error("Numeric required")

        step_val = 1.0
        self.scanner.skip_spaces()
        if self.scanner.consume_keyword("STEP"):
            step_val = self._eval_expr()
            if not isinstance(step_val, (int, float)): self._error("Numeric required")

        # Initialize Loop Var
        self.vars[key] = float(start_val)

        # Push frame
        frame = ForFrame(
            var_name=key,
            end_value=float(end_val),
            step=float(step_val),
            line_index=self.current_line_index,
            resume_pos=self.scanner.pos
        )
        self.for_stack.append(frame)

    def _stmt_next(self):
        self.scanner.skip_spaces()
        var_name = ""
        # Optional variable name
        if self.scanner.remaining() and self.scanner.remaining()[0].isalpha():
            # Peek at the name without fully consuming via _get_var_ref to verify it matches
            # But strictly, we can just look at top of stack
            # Let's read it to be safe
            match = re.match(r'^[A-Za-z][A-Za-z0-9]*', self.scanner.remaining())
            if match:
                raw = match.group(0)
                self.scanner.advance(len(raw))
                var_name, _ = self._normalize_name(raw)

        if not self.for_stack:
            self._error("NEXT without FOR")

        # Find matching frame
        frame_idx = -1
        if var_name:
            for i in range(len(self.for_stack) - 1, -1, -1):
                if self.for_stack[i].var_name == var_name:
                    frame_idx = i
                    break
            if frame_idx == -1: self._error("NEXT variable mismatch")
        else:
            frame_idx = len(self.for_stack) - 1

        # Pop inner loops if we jumped out
        while len(self.for_stack) > frame_idx + 1:
            self.for_stack.pop()

        frame = self.for_stack[frame_idx]

        # Increment
        val = self.vars.get(frame.var_name, 0.0)
        val += frame.step
        self.vars[frame.var_name] = val

        # Check condition
        loop_continues = False
        if frame.step >= 0:
            if val <= frame.end_value: loop_continues = True
        else:
            if val >= frame.end_value: loop_continues = True

        if loop_continues:
            self.current_line_index = frame.line_index
            self.scanner = Scanner(self.lines[self.current_line_index].text)
            self.scanner.pos = frame.resume_pos
        else:
            self.for_stack.pop()

    def _stmt_dim(self):
        while True:
            self.scanner.skip_spaces()
            match = re.match(r'^[A-Za-z][A-Za-z0-9]*\$?', self.scanner.remaining())
            if not match: self._error("Expected array name")

            raw_name = match.group(0)
            self.scanner.advance(len(raw_name))
            key, is_string = self._normalize_name(raw_name)

            self.scanner.skip_spaces()
            if self.scanner.peek() != '(': self._error("DIM requires size")
            self.scanner.advance()

            size_val = self._eval_expr()
            if not isinstance(size_val, (int, float)): self._error("Size must be numeric")

            self.scanner.skip_spaces()
            if self.scanner.peek() != ')': self._error("Missing ')'")
            self.scanner.advance()

            size = int(size_val) + 1  # 0 to N
            default_val = "" if is_string else 0.0
            self.arrays[key] = [default_val] * size

            self.scanner.skip_spaces()
            if self.scanner.peek() == ',':
                self.scanner.advance()
                continue
            break

    def _stmt_sleep(self):
        # Consume optional parenthesis
        has_paren = False
        self.scanner.skip_spaces()
        if self.scanner.peek() == '(':
            self.scanner.advance()
            has_paren = True

        val = self._eval_expr()
        if not isinstance(val, (int, float)): self._error("Numeric required")

        if has_paren:
            self.scanner.skip_spaces()
            if self.scanner.peek() == ')':
                self.scanner.advance()
            else:
                self._error("Missing ')'")

        # C code converts ticks (60Hz) to seconds
        seconds = val / 60.0
        if seconds > 0:
            time.sleep(seconds)


# --- Main Entry Point ---

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <program.bas>")
        return

    interpreter = BasicInterpreter()
    try:
        interpreter.load_program_from_file(sys.argv[1])
        interpreter.run()
    except BasicRuntimeError:
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nBreak")
        sys.exit(0)


if __name__ == "__main__":
    main()