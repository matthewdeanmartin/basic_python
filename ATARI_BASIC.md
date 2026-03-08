# Atari BASIC (Modern REPL Subset) — Compact Specification

## 1. Scope

This document specifies a modern implementation of **Atari BASIC for the 8-bit family**, focused on the distinctive **language and REPL behavior** rather than original hardware integration.

This specification:

* targets the **latest 8-bit Atari BASIC lineage**, not ST BASIC
* preserves distinctive source-level behavior where practical
* excludes hardware-specific facilities such as graphics, `PEEK`, `POKE`, `USR`, and device/tape I/O
* uses **ASCII** source text
* requires numeric evaluation with the **maximum practical precision available** in the implementation language/runtime

This is a language-and-interpreter spec for modern machines.

---

## 2. Source Form

### 2.1 Program Lines

A program line consists of:

`<line-number> <statement-list>`

Example:

```basic
10 PRINT "HELLO"
20 GOTO 10
```

Line numbers are positive integers. A newly entered line with an existing line number replaces the old line.

A line containing only a line number deletes that line.

### 2.2 Immediate Mode

Input not beginning with a line number is executed immediately.

Example:

```basic
PRINT 2+2
```

### 2.3 Character Set

Source text is ASCII. Keywords are case-insensitive. String contents preserve case.

---

## 3. Lexical Rules

### 3.1 Identifiers

Identifiers:

* begin with a letter
* may contain letters and digits
* are case-insensitive
* are significant in full; they are not truncated

Examples:

```basic
TOTAL=1
TOTAL2=2
TOTALVALUE=3
```

### 3.2 String Variables

String variable names end in `$`.

Example:

```basic
NAME$="ALICE"
```

### 3.3 Keyword Collision

Keywords may be used as variable names only when introduced by `LET`.

Example:

```basic
LET PRINT=5
PRINT PRINT
```

This behavior is distinctive and should be preserved.

---

## 4. Data Model

### 4.1 Numeric Values

Numeric values are real numbers.

The implementation shall use the **maximum practical precision** provided by the host environment. The spec does not impose 8-bit-era limits on range or precision.

### 4.2 Strings

Strings are sequences of characters.

To preserve Atari BASIC source behavior, string variables must be explicitly dimensioned before assignment.

Example:

```basic
DIM NAME$(20)
NAME$="ALICE"
```

The declared size is the maximum capacity of the string.

### 4.3 Arrays

Arrays must be explicitly dimensioned before use.

Example:

```basic
DIM A(100)
```

Undimensioned array use is an error.

### 4.4 String Arrays

This subset does **not** support string arrays.

---

## 5. Statements

Multiple statements may appear on one line separated by `:`.

Example:

```basic
10 A=1:B=2:PRINT A+B
```

### 5.1 Assignment

Both implicit and `LET` assignment are valid.

```basic
A=10
LET A=10
```

### 5.2 REM

`REM` begins a comment extending to end of line.

```basic
10 REM LOOP FOREVER
```

### 5.3 PRINT

`PRINT` outputs expressions.

```basic
PRINT "HELLO"
PRINT A
PRINT A,B
```

A semicolon suppresses the terminating newline.

```basic
PRINT "HELLO";
PRINT "WORLD"
```

### 5.4 INPUT

`INPUT` reads a value from standard input.

```basic
INPUT A
INPUT NAME$
```

### 5.5 DIM

`DIM` allocates arrays and fixed-capacity strings.

```basic
DIM A(10)
DIM NAME$(20)
```

### 5.6 IF

Form:

```basic
IF <condition> THEN <statement>
```

Example:

```basic
IF A>10 THEN PRINT "BIG"
```

`ELSE` is not part of this specification.

### 5.7 FOR / NEXT

Form:

```basic
FOR I=1 TO 10
PRINT I
NEXT I
```

Optional step:

```basic
FOR I=10 TO 1 STEP -1
PRINT I
NEXT I
```

### 5.8 GOTO

Transfers control to a line number.

```basic
GOTO 100
```

A numeric variable expression may be used as the target line.

```basic
A=100
GOTO A
```

### 5.9 GOSUB / RETURN

Subroutine call and return.

```basic
GOSUB 500
RETURN
```

### 5.10 END

Terminates program execution.

```basic
END
```

### 5.11 STOP

Suspends execution and returns control to the REPL.

```basic
STOP
```

### 5.12 SOUND (optional)

An implementation may provide:

```basic
SOUND channel, pitch, timbre, volume
```

If implemented, it should be treated as a host-level convenience feature. Exact audio behavior is implementation-defined.

---

## 6. Expressions

### 6.1 Numeric Operators

Implement at least:

* `+`
* `-`
* `*`
* `/`
* unary `+` and `-`
* `^`

### 6.2 Relational Operators

Implement at least:

* `=`
* `<>`
* `<`
* `>`
* `<=`
* `>=`

A true comparison yields a nonzero numeric value. False yields zero.

### 6.3 String Comparison

String equality and ordering comparisons may be supported using normal lexicographic ASCII order.

### 6.4 Parentheses

Parentheses may be used to group expressions.

---

## 7. REPL Commands

The implementation shall provide a line-oriented REPL with the following commands available in immediate mode.

### 7.1 LIST

Displays program lines.

```basic
LIST
LIST 100
LIST 100,200
```

### 7.2 RUN

Executes the current program.

```basic
RUN
```

### 7.3 NEW

Deletes the current program and clears runtime state as appropriate.

```basic
NEW
```

### 7.4 CONT

Continues execution after `STOP`, if continuation is valid.

```basic
CONT
```

### 7.5 CLR

Clears variables and runtime stacks without deleting the program.

```basic
CLR
```

### 7.6 ENTERED PROGRAM EDITING

The REPL shall support the classic edit model:

* entering a numbered line inserts or replaces it
* entering only a line number deletes it
* `LIST` reveals canonical stored form

This editing model is part of the language experience and should be preserved.

---

## 8. Error Behavior

The interpreter shall detect and report, at minimum:

* syntax error
* undefined line target
* use of undimensioned array or string
* return without gosub
* next without matching for
* type mismatch
* input conversion failure

Error text is implementation-defined, but should remain short and REPL-friendly.

---

## 9. Distinctive Behaviors to Preserve

A conforming implementation should preserve these Atari-BASIC-like traits:

1. **Line-oriented program storage** with numbered lines
2. **Immediate mode plus stored program mode** in one interpreter
3. **Full-significance variable names**
4. **Keyword-as-variable via `LET`**
5. **Mandatory `DIM` for strings and arrays**
6. **No `ELSE` in `IF`**
7. **Multiple statements per line with `:`**
8. **`LIST` as a first-class REPL/program editing command**
9. **Variable-valued `GOTO` targets**

These are the main source-visible features that make Atari BASIC feel like Atari BASIC in a modern implementation.

---

## 10. Minimal Conformance Example

```basic
10 DIM NAME$(20)
20 INPUT NAME$
30 IF NAME$="" THEN END
40 PRINT "HELLO, ";NAME$
50 A=100
60 GOTO A
100 STOP
```

A conforming implementation shall accept, store, list, run, stop, and continue this program according to the rules above.
