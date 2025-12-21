# Python BASIC Interpreter

This code

https://github.com/davepl/pdpsrc/blob/main/bsd/basic/basic.c

translated into python by Gemini 3 Thinking mode

## My Notes

Surprisingly short.

Runs at an acceptable speed.


## Overview

This project is a direct port of a minimal C-based BASIC interpreter into Python 3. It replicates the behavior of 6502
Microsoft/Commodore BASIC v2, including its specific quirks (like variable name truncation) and execution flow.

## How It Works

The interpreter is built around a standard fetch-execute cycle, managing program state through distinct data structures
for lines, variables, and control flow stacks.

### 1. Program Loading & Storage

When a file is loaded, the interpreter reads it line-by-line.

* **Parsing Line Numbers:** Lines starting with an integer are stored as `Line` objects containing the number and the
  raw text.
* **Sorting:** The lines are sorted by line number to ensure correct execution order, regardless of the order they
  appeared in the source file.
* **Mapping:** Internally, the interpreter maps the BASIC line number (e.g., `100`) to a physical list index (e.g.,
  index `5` in the `lines` list) to facilitate fast jumps.

### 2. The Execution Loop

The core of the interpreter is a `while` loop in the `run()` method:

1. **Fetch:** It retrieves the `Line` object at the `current_line_index`.
2. **Scan:** A `Scanner` object is created for that line. This acts like a cursor, moving through the text character by
   character.
3. **Execute:** The scanner identifies the statement keyword (e.g., `PRINT`, `IF`, `FOR`) and dispatches execution to
   the corresponding method.
4. **Advance:**

* **Sequential:** If no jump occurs, the `current_line_index` increments.
* **Jumps:** Commands like `GOTO` or `GOSUB` manually update the `current_line_index` to point to a new location.

### 3. Expression Evaluation (Recursive Descent)

Mathematical and logical expressions are evaluated using a **Recursive Descent Parser**. This handles operator
precedence (PEMDAS) automatically by nesting function calls:

* `_eval_expr`: Handles addition and subtraction (`+`, `-`).
* `_eval_term`: Handles multiplication and division (`*`, `/`).
* `_eval_power`: Handles exponentiation (`^`).
* `_eval_factor`: Handles base units: numbers, variables, strings, parenthesis `()`, and function calls (e.g., `SIN()`).

When `_eval_expr` is called, it calls `_eval_term`, which calls `_eval_power`, ensuring that `3 + 4 * 5` is correctly
evaluated as `23` and not `35`.

### 4. Variable Storage & "The Two-Letter Rule"

Variables are stored in two Python dictionaries: `vars` (scalars) and `arrays`.

* **Normalization:** Following CBM BASIC v2 standards, variable names are significant only up to the first two
  characters. `SCORE` and `SCARY` both map to the key `SC`.
* **Types:** The interpreter distinguishes between strings and numbers based on the `$` suffix. `A` is a number; `A$` is
  a string.

### 5. Control Flow Stacks

To support nested loops and subroutines, the interpreter uses Python lists as stacks:

* **`gosub_stack`**: When `GOSUB 100` is called, the current line index and character position are pushed onto this
  stack. `RETURN` pops this frame to resume execution exactly where it left off.
* **`for_stack`**: When `FOR I = 1 TO 10` is encountered, a `ForFrame` is pushed, tracking the loop variable, target
  value, step size, and the location of the loop's start. `NEXT` checks this stack to decide whether to loop back or
  continue.

---

## Addendum: Implemented BASIC Features

This interpreter implements a subset of BASIC v2 compatible commands.

### Statements

| Command             | Description                                                                |
|---------------------|----------------------------------------------------------------------------|
| **PRINT**           | Output text/vars to stdout. Supports `;` (no newline) and `,` (tab zones). |
| **INPUT**           | Read user input into a variable. Supports custom prompts.                  |
| **LET**             | Assign values to variables (e.g., `LET A=10`). The keyword is optional.    |
| **IF / THEN**       | Conditional logic. Supports implicit GOTO (e.g., `IF X=5 THEN 100`).       |
| **GOTO**            | Unconditional jump to a line number.                                       |
| **GOSUB**           | Jump to a subroutine.                                                      |
| **RETURN**          | Return from a subroutine.                                                  |
| **FOR / TO / STEP** | Loop initialization.                                                       |
| **NEXT**            | Loop termination/increment.                                                |
| **DIM**             | Allocate memory for arrays (e.g., `DIM A(20)`).                            |
| **REM** or **'**    | Comments. Ignored by the interpreter.                                      |
| **SLEEP**           | Pause execution (e.g., `SLEEP 60` sleeps for 1 second/60 ticks).           |
| **END / STOP**      | Terminate program execution.                                               |

### Intrinsic Functions

* **Math:** `SIN`, `COS`, `TAN`, `ABS`, `INT` (floor), `SQR` (sqrt), `SGN` (sign), `EXP`, `LOG`, `RND`.
* **String:** `LEN`, `VAL` (string to num), `STR$` (num to string), `CHR$` (ASCII to char), `ASC` (char to ASCII).
* **Formatting:** `TAB(n)` (move cursor to column n).

### Operators

* **Arithmetic:** `+`, `-`, `*`, `/`, `^` (power).
* **Relational:** `=`, `<>`, `<`, `>`, `<=`, `>=`.
* **String:** `+` (concatenation).

### Known Quirks

1. **Variable Truncation:** `COUNT` and `COST` are the same variable (`CO`).
2. **Array Default:** Using an array without `DIM` creates it with size 11 (indices 0-10).
3. **Line Numbers:** Programs must use integer line numbers.


## Prior Art

- https://github.com/pahandav/basic-wrangler/tree/master
- https://github.com/richpl/PyBasic
- https://www.youtube.com/watch?v=hK2OxjhH3dw&start=0
- https://zserge.com/posts/langs-basic/
- https://github.com/maksimKorzh/BASIC/blob/main/tutorial/part7/basic.py
- and corresponding youtube video: https://www.youtube.com/watch?v=WShuQV1XjVM
