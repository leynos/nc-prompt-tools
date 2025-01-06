#!/usr/bin/env python3.13
"""
balance_checker.py

A script that checks if a given file contains:
1) Balanced parentheses inside braced expressions.
2) Well-formed control structures of the form:
   {#if (...)} ... {#else} ... {#endif}
   (including nested if/else statements).

Optionally, it attempts a naive fix for one common exporter bug that
strips out a final parenthesis before a break.

This script uses Python 3.13 features (including modern type hints) and
adheres to best practices and PEP standards.
"""

from __future__ import annotations

import dataclasses
import enum
import json
import re
import argparse
from pathlib import Path
from enum import Enum, auto
import typing


class CheckFileBalanceResult(Enum):
    OK = auto()
    ILLEGAL_NESTING = auto()
    MISMATCHED_PARENTHESIS = auto()
    MISMATCHED_BRACES = auto()
    INVALID_FLOW_CONTROL = auto()


class ParenthesisMismatchError(Exception):
    """Raised when parentheses are unbalanced or mismatched."""


class IllegalNestingError(Exception):
    """
    Raised when braces are nested (which is disallowed)
    """


class BraceMismatchError(Exception):
    """Raised when braces are unbalanced or mismatched."""


class IfControlMismatchError(Exception):
    """Raised when there is a mismatch in {#if}, {#else}, or {#endif} usage."""


def parse_braced_expressions(
    file_content: str,
) -> list[tuple[int, int, str]]:
    """
    Extract all top-level braced expressions from the file content,
    along with their start and end indices in the original string.

    Since the problem statement guarantees that:
    1. Braced expressions do not nest.
    2. Parentheses are only considered part of the language inside braces.

    Parameters
    ----------
    file_content : str
        The full contents of the file as a single string.

    Returns
    -------
    list of tuple of (int, int, str)
        Each tuple contains:
        - The index of the '{' character (start index).
        - The index of the '}' character (end index).
        - The contents (i.e. everything between '{' and '}').

    Raises
    ------
    IllegalNestingError
        If nested braces or unmatched braces are encountered.
    """
    expressions: list[tuple[int, int, str]] = []
    brace_buffer: list[str] = []
    inside_brace = False
    brace_start_index = -1

    for i, char in enumerate(file_content):
        if char == "{":
            if inside_brace:
                # Braced expressions cannot contain other braces.
                raise IllegalNestingError(
                    "Nested braces encountered, which is not allowed."
                )
            inside_brace = True
            brace_start_index = i
            brace_buffer = []
        elif char == "}":
            if not inside_brace:
                # Unmatched closing brace
                raise BraceMismatchError(
                    "Encountered a closing brace without an opening brace."
                )
            inside_brace = False
            expressions.append((brace_start_index, i, "".join(brace_buffer)))
            brace_buffer = []
        else:
            if inside_brace:
                brace_buffer.append(char)

    if inside_brace:
        # We opened a brace but never closed it
        raise BraceMismatchError("Unmatched opening brace found in file.")

    return expressions


def check_parentheses_balance(expression: str) -> bool:
    """
    Check whether parentheses in a single braced expression are balanced.

    Uses a simple stack-based approach: every '(' pushes to the stack,
    every ')' pops from the stack. If the stack is empty when trying
    to pop or remains non-empty at the end, balance is not achieved.

    Parameters
    ----------
    expression : str
        The string content of a single braced expression.

    Returns
    -------
    bool
        True if all parentheses within the expression are balanced,
        False otherwise.
    """
    stack: list[str] = []
    for char in expression:
        if char == "(":
            stack.append(char)
        elif char == ")":
            if not stack:
                return False
            stack.pop()
    return len(stack) == 0


def naive_fix_expression_if_needed(expression: str, start_idx: int) -> str:
    """
    Attempt a naive fix for the common issue where a final parenthesis
    might be stripped out by an exporter before a break. If the difference
    between '(' and ')' is exactly +1, appends a ')' and re-checks.

    Parameters
    ----------
    expression : str
        The string content of a braced expression.

    Returns
    -------
    str
        The potentially fixed expression. If the fix is not applicable
        or doesn't resolve the balance issue, returns the original.
    """
    if check_parentheses_balance(expression):
        return expression

    print(f"Attempting naive fix for expression at byte {start_idx} ({expression!r})")

    open_count = expression.count("(")
    close_count = expression.count(")")
    if open_count - close_count == 1:
        # Attempt to fix by adding one closing parenthesis at the end
        fixed = expression + ")"
        if check_parentheses_balance(fixed):
            return fixed

    return expression


class ControlFlowToken(enum.StrEnum):
    IF = "IF"
    ELSEIF = "ELSEIF"
    ELSE = "ELSE"
    ENDIF = "ENDIF"


def parse_control_flow_tokens(
    file_content: str,
) -> list[tuple[int, ControlFlowToken, str]]:
    """
    Parse the file content for tokens of the form:
      {#if ( ... )}  {#elseif ( ... )}  {#else}  {#endif}

    Returns a list of tokens in the order they appear, where each token
    is (position_in_file, token_name, optional_text). For #if and #elseif tokens,
    the optional_text is the expression inside (...). For #else and
    #endif, optional_text will be ''.

    Raises
    ------
    ParenthesisMismatchError
        If the parentheses in #if or #elseif expressions are unbalanced.
    """
    tokens: list[tuple[int, ControlFlowToken, str]] = []

    pattern = re.compile(
        r"""
        (?P<if>\{\#if\s*(?P<if_expr>[^}]*)\})          # e.g. {#if (condition)}
        |(?P<elseif>\{\#elseif\s*(?P<elif_expr>[^}]*)\})  # e.g. {#elseif (condition)}
        |(?P<else>\{\#else\})                          # e.g. {#else}
        |(?P<endif>\{\#endif\})                        # e.g. {#endif}
        """,
        re.VERBOSE,
    )

    for match in pattern.finditer(file_content):
        start_idx = match.start()
        if match.group("if"):
            expr = match.group("if_expr") or ""
            # Check parentheses are balanced in the #if expression
            if not check_parentheses_balance(expr):
                raise ParenthesisMismatchError(
                    f"Unbalanced parentheses in #if expression at position {start_idx}: '{expr}'"
                )
            tokens.append((start_idx, ControlFlowToken.IF, expr))
        elif match.group("elseif"):
            expr = match.group("elif_expr") or ""
            # Check parentheses are balanced in the #elseif expression
            if not check_parentheses_balance(expr):
                raise ParenthesisMismatchError(
                    f"Unbalanced parentheses in #elseif expression at position {start_idx}: '{expr}'"
                )
            tokens.append((start_idx, ControlFlowToken.ELSEIF, expr))
        elif match.group("else"):
            tokens.append((start_idx, ControlFlowToken.ELSE, ""))
        elif match.group("endif"):
            tokens.append((start_idx, ControlFlowToken.ENDIF, ""))

    # Sort tokens by appearance order (though finditer typically is in order)
    tokens.sort(key=lambda t: t[0])
    return tokens


@dataclasses.dataclass(slots=True, frozen=True)
class IfBlockState:
    """Tracks the state of an #if/#else/#endif block."""

    has_else: bool = False
    has_elseif: bool = False

    def with_else(self) -> "IfBlockState":
        """Return a new state with else flag set."""
        return IfBlockState(has_else=True, has_elseif=self.has_elseif)

    def with_elseif(self) -> "IfBlockState":
        """Return a new state with elseif flag set."""
        return IfBlockState(has_else=False, has_elseif=True)


def check_if_else_endif_structure(file_content: str) -> bool:
    """
    Check that each {#if (...)} statement is matched with a corresponding
    {#endif} or {#else}/{#elseif} {#endif}, and that each {#else}/{#elseif}
    is matched with a corresponding {#if} that has not yet used a terminal else, etc.

    This supports nested if-else blocks and allows multiple elseif statements
    before an optional final else.
    Parameters
    ----------
    file_content : str

    Returns
    -------
    bool
        True if the control flow structure is correct, False otherwise.

    Raises
    ------
    IfControlMismatchError
        If the if/else/endif structure is invalid (e.g., elseif after else,
        leftover if, unmatched endif).
    """
    tokens = parse_control_flow_tokens(file_content)

    # Stack for #if blocks: we track whether we've hit a terminal else
    stack: list[IfBlockState] = []

    for _, token_type, _ in tokens:
        match token_type:
            case ControlFlowToken.IF:
                stack.append(IfBlockState())
            case ControlFlowToken.ELSEIF:
                if not stack:
                    raise IfControlMismatchError(
                        "Encountered {#elseif} without matching {#if}."
                    )
                current = stack[-1]
                if current.has_else:  # Terminal else already seen
                    raise IfControlMismatchError(
                        "Encountered {#elseif} after {#else} in the same {#if} block."
                    )
                stack[-1] = current.with_elseif()
            case ControlFlowToken.ELSE:
                if not stack:
                    raise IfControlMismatchError(
                        "Encountered {#else} without matching {#if}."
                    )
                current = stack[-1]
                if current.has_else:  # Terminal else already seen
                    raise IfControlMismatchError(
                        "Encountered second {#else} for the same {#if}."
                    )
                stack[-1] = current.with_else()
            case ControlFlowToken.ENDIF:
                if not stack:
                    raise IfControlMismatchError(
                        "Encountered {#endif} without matching {#if}."
                    )
                stack.pop()

    if stack:
        # leftover #if
        raise IfControlMismatchError("Unmatched {#if} (missing {#endif}).")

    return True


def check_file_balance(file_content: str) -> CheckFileBalanceResult:
    """
    Check file content for structural validity and balanced expressions.

    Validates that the content satisfies:
      1) Balanced parentheses in all braced expressions
      2) Correct if/else/endif structure
      3) Legal nesting of control structures

    Parameters
    ----------
    file_content : str
        The content to validate

    Returns
    -------
    CheckFileBalanceResult
        OK: All checks pass
        ILLEGAL_NESTING: Invalid nesting of braced expressions found
        MISMATCHED_PARENTHESIS: Unbalanced parentheses in expressions
        INVALID_FLOW_CONTROL: Invalid if/else/endif structure
    """
    # 1) Braced expressions check
    try:
        braced_expressions = parse_braced_expressions(file_content)
    except IllegalNestingError:
        return CheckFileBalanceResult.ILLEGAL_NESTING
    except BraceMismatchError:
        return CheckFileBalanceResult.MISMATCHED_BRACES

    # Check each braced expression for parenthesis balance
    for _, _, expr in braced_expressions:
        if not check_parentheses_balance(expr):
            return CheckFileBalanceResult.MISMATCHED_PARENTHESIS

    # 2) If/else/endif structure check
    try:
        check_if_else_endif_structure(file_content)
    except ParenthesisMismatchError:
        return CheckFileBalanceResult.MISMATCHED_PARENTHESIS
    except IfControlMismatchError:
        return CheckFileBalanceResult.INVALID_FLOW_CONTROL

    return CheckFileBalanceResult.OK


def fix_message_content(content: str) -> str:
    """
    Attempt to fix the file contents by appending a missing final parenthesis
    in each braced expression if appropriate. Rebuilds the file content with
    any expressions that were successfully fixed.

    (Does not fix if/else/endif control flow errors.)

    Parameters
    ----------
    content : str

    Returns
    -------
    str
        The modified file contents after attempting naive fixes for parentheses.
    """
    try:
        expressions_with_positions = parse_braced_expressions(content)
    except (IllegalNestingError, BraceMismatchError):
        # If braces are invalid, naive fix won't help; return as-is
        return content

    new_content_parts: list[str] = []
    prev_end = 0

    for start_idx, end_idx, expr in expressions_with_positions:
        # Copy everything from previous end up to the opening brace
        new_content_parts.append(content[prev_end:start_idx])
        # Add the opening brace
        new_content_parts.append("{")

        # Attempt naive fix

        fixed_expr = naive_fix_expression_if_needed(expr, start_idx)
        new_content_parts.append(fixed_expr)

        # Add closing brace
        new_content_parts.append("}")

        prev_end = end_idx + 1

    # Append any leftover content
    new_content_parts.append(content[prev_end:])
    return "".join(new_content_parts)


def process_message_check_result(
    content: str, do_fix: bool = False
) -> tuple[bool, str | None]:
    """Process file validation results and optionally apply fixes.

    Checks if a file has balanced parentheses and correct control flow.
    If fixes are requested and the file is invalid, attempts to fix the issues
    and writes the result to a new file.

    Parameters
    ----------
    content : str
        The content of the message to validate and potentially fix
    do_fix : bool, optional
        If True, attempts to fix any validation issues found, by default False

    Returns
    -------
    int
        Exit code - 0 if valid or fixed successfully, 1 if validation failed
    """
    fixable = False
    match check_file_balance(content):
        case CheckFileBalanceResult.OK:
            return True, None
        case CheckFileBalanceResult.ILLEGAL_NESTING:
            print("Validation failed: illegal nesting of braced expressions detected.")
        case CheckFileBalanceResult.MISMATCHED_PARENTHESIS:
            print("Validation failed: unbalanced parentheses detected.")
            fixable = True
        case CheckFileBalanceResult.MISMATCHED_BRACES:
            print("Validation failed: unbalanced braces detected.")
        case CheckFileBalanceResult.INVALID_FLOW_CONTROL:
            print("Validation failed: incorrect control flow structure detected.")

    if not fixable or not do_fix:
        return False, None

    # Attempt fixes
    fixed_content = fix_message_content(content)
    fix_succeeded = check_file_balance(fixed_content) == CheckFileBalanceResult.OK
    return fix_succeeded, fixed_content


def load_messages(json_data: typing.Any) -> list[dict[str, str]]:
    """
    Given loaded JSON, extract the list of message objects.

    We data in the form:

    1) {
         "messages": [
            {"text": "..."},
            {"text": "..."}
         ]
       }

    Returns
    -------
    list of dict with key "text"
    """
    match json_data:
        case {"messages": list() as messages}:
            return messages

    # Otherwise, we don't know how to parse
    raise ValueError('JSON must be in the form {"messages": [...]}')


@dataclasses.dataclass(slots=True, frozen=True)
class LintResult:
    """Represents the result of a linting operation, tracking success and changes."""

    success: bool
    had_changes: bool

    def tally(self, other) -> LintResult:
        """Combines this result with another, returning a new LintResult."""
        return LintResult(
            success=self.success and other.success,
            had_changes=self.had_changes or other.had_changes,
        )


def lint_prompt(prompt: dict, fix: bool) -> LintResult:
    # Extract message objects
    try:
        messages = load_messages(prompt)
    except ValueError as e:
        print(f"Error: {e}")
        exit(8)

    # Lint each message
    had_errors = []
    had_changes = []
    for i, msg_obj in enumerate(messages):
        text = msg_obj.get("text", "")
        result = process_message_check_result(text, fix)
        match result:
            case (True, str() as new_text):
                # We have a fix
                print(f"Message index {i} passed all checks following fixes")
                msg_obj["text"] = new_text
                had_changes.append(True)
                had_errors.append(True)
            case (False, _):
                if not fix:
                    print(
                        f"Message index {i} has errors, but may be fixable (use --fix to try)"
                    )
                else:
                    print(f"Message index {i} could not be fixed")
                had_changes.append(False)
                had_errors.append(True)
            case _:
                print(f"Message index {i} passed all checks")
    success = not any(err and not fixed for err, fixed in zip(had_errors, had_changes))
    return LintResult(success=success, had_changes=any(had_changes))


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Lint messages from a Novelcrafter JSON prompt file "
            "(with inline or bundled dependencies). "
            "Exits 0 if all messages pass lint or can be fixed automatically."
        )
    )
    parser.add_argument("file", type=str, help="Path to the JSON prompt file.")
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Attempt to fix automatically fixable lint problems.",
    )
    args = parser.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"File not found: {path}")
        exit(8)

    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        exit(8)

    match data:
        case dict():
            result = lint_prompt(data, args.fix)
        case list():
            result = LintResult(success=True, had_changes=False)
            for index, item in enumerate(data):
                if index == 0:
                    print("Checking prompt")
                else:
                    print(f"Checking dependency {index}")
                result = result.tally(lint_prompt(item, args.fix))
        case _:
            print("Unsupported JSON data type")
            exit(8)

    # If we used --fix and we changed something, write out the result
    if args.fix and result.had_changes:
        # E.g., write to <stem>_fixed<suffix>
        fixed_path = path.parent / f"{path.stem}_fixed{path.suffix}"
        with fixed_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        if result.success:
            print(f"Fixes applied and written to {fixed_path}")
        else:
            print(
                f"Fixes applied and written to {fixed_path}, but some errors could not be automatically fixed"
            )
            exit(1)

    # If we get here, everything is good (or good after fixes).
    exit(0)


if __name__ == "__main__":
    main()
