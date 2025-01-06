import pytest

from nc_prompt_tools.prompt_lint import (
    CheckFileBalanceResult,
    ControlFlowToken,
    parse_braced_expressions,
    check_parentheses_balance,
    naive_fix_expression_if_needed,
    parse_control_flow_tokens,
    check_if_else_endif_structure,
    check_file_balance,
    fix_message_content,
    ParenthesisMismatchError,
    IllegalNestingError,
    IfControlMismatchError,
    BraceMismatchError,
)


class TestBracedExpressionParsing:
    def test_basic(self):
        file_content = "Some text {abc (xyz)} more text {123 (abc)} end"
        expressions = parse_braced_expressions(file_content)
        # We expect two expressions
        assert len(expressions) == 2
        # Check actual extracted contents
        assert expressions[0][2] == "abc (xyz)"
        assert expressions[1][2] == "123 (abc)"

    def test_nested_braces(self):
        # Attempting nested braces is disallowed, so we should get IllegalNestingError
        file_content = "Text {outer {nested} stuff} more text"
        with pytest.raises(IllegalNestingError):
            _ = parse_braced_expressions(file_content)

    def test_unmatched_closing(self):
        file_content = "Text stuff} unbalanced"
        with pytest.raises(BraceMismatchError):
            _ = parse_braced_expressions(file_content)

    def test_unmatched_opening(self):
        file_content = "Something {abc def"
        with pytest.raises(BraceMismatchError):
            _ = parse_braced_expressions(file_content)


class TestParenthesesHandling:
    @pytest.mark.parametrize(
        "expression,expected",
        [
            ("", True),
            ("(abc)", True),
            ("(abc", False),
            ("(abc)(def)", True),
            ("(abc)(def", False),
            ("(()())", True),
            ("(()", False),
        ],
    )
    def test_balance_check(self, expression, expected):
        assert check_parentheses_balance(expression) == expected

    @pytest.mark.parametrize(
        "expression,expected_fixed",
        [
            # Balanced expressions stay the same
            ("(abc)", "(abc)"),
            # Missing one closing parenthesis
            ("(abc", "(abc)"),
            # More complex mismatch: naive fix won't resolve double '('
            ("((abc)", "((abc))"),
            # Already balanced multiple groups
            ("(a)(b)", "(a)(b)"),
        ],
    )
    def test_naive_fix(self, expression, expected_fixed):
        assert naive_fix_expression_if_needed(expression, 0) == expected_fixed


class TestControlFlowParsing:
    def test_basic_structure(self):
        file_content = """
            {#if (x > 0)}
            Some text
            {#else}
            Other text
            {#endif}
        """
        tokens = parse_control_flow_tokens(file_content)
        assert len(tokens) == 3
        # Check the types in order
        assert tokens[0][1] == ControlFlowToken.IF
        assert tokens[1][1] == ControlFlowToken.ELSE
        assert tokens[2][1] == ControlFlowToken.ENDIF
        # Check that the expression in the IF is 'x > 0'
        assert tokens[0][2].strip() == "(x > 0)"

    def test_balanced_if_expression(self):
        file_content = "{#if ((x > 0) && (y < 0))}stuff{#endif}"
        tokens = parse_control_flow_tokens(file_content)
        assert len(tokens) == 2
        assert tokens[0][1] == ControlFlowToken.IF
        # Should not raise any error
        assert tokens[0][2] == "((x > 0) && (y < 0))"

    def test_unbalanced_if_expression(self):
        file_content = "{#if ((x > 0) && (y < 0)}stuff{#endif}"
        with pytest.raises(ParenthesisMismatchError, match="Unbalanced parentheses"):
            _ = parse_control_flow_tokens(file_content)

    def test_elseif_basic_structure(self):
        file_content = """
            {#if (x > 0)}
            First block
            {#elseif (y < 0)}
            Second block
            {#else}
            Third block
            {#endif}
        """
        tokens = parse_control_flow_tokens(file_content)
        assert len(tokens) == 4
        # Check the types in order
        assert tokens[0][1] == ControlFlowToken.IF
        assert tokens[0][2].strip() == "(x > 0)"
        assert tokens[1][1] == ControlFlowToken.ELSEIF
        assert tokens[1][2].strip() == "(y < 0)"
        assert tokens[2][1] == ControlFlowToken.ELSE
        assert tokens[3][1] == ControlFlowToken.ENDIF

    def test_elseif_balanced_expression(self):
        file_content = "{#if (x > 0)}{#elseif ((y < 0) && (z == 1))}{#endif}"
        tokens = parse_control_flow_tokens(file_content)
        assert len(tokens) == 3
        assert tokens[0][1] == ControlFlowToken.IF
        assert tokens[1][1] == ControlFlowToken.ELSEIF
        assert tokens[1][2].strip() == "((y < 0) && (z == 1))"
        assert tokens[2][1] == ControlFlowToken.ENDIF


class TestIfElseEndifStructure:
    def test_basic_validation(self):
        # Well-formed nested example
        file_content = """
            {#if (a)}
            stuff
            {#if (b)} nested {#endif}
            {#else}
            alt
            {#if (c)} c branch {#else} c alt {#endif}
            {#endif}
        """
        assert check_if_else_endif_structure(file_content) is True

    def test_elseif_validation(self):
        # Well-formed elseif example
        file_content = """
            {#if (a)}
            first block
            {#elseif (b)}
            second block
            {#elseif (c)}
            third block
            {#else}
            final block
            {#endif}
        """
        assert check_if_else_endif_structure(file_content) is True

        # Nested elseif example
        file_content_nested = """
            {#if (x)}
                outer if
                {#if (y)}
                    nested if
                {#elseif (z)}
                    nested elseif
                {#endif}
            {#elseif (w)}
                outer elseif
            {#endif}
        """
        assert check_if_else_endif_structure(file_content_nested) is True

    def test_invalid_elseif_structures(self):
        # elseif after else
        file_content_elseif_after_else = """
            {#if (a)}
            first
            {#else}
            else block
            {#elseif (b)}
            invalid position
            {#endif}
        """
        with pytest.raises(
            IfControlMismatchError, match="Encountered {#elseif} after {#else}"
        ):
            check_if_else_endif_structure(file_content_elseif_after_else)

        # Missing endif with elseif
        file_content_missing_endif = """
            {#if (a)}
            first
            {#elseif (b)}
            second
        """
        with pytest.raises(IfControlMismatchError, match="Unmatched {#if}"):
            check_if_else_endif_structure(file_content_missing_endif)

    def test_error_double_else(self):
        # Missing #endif
        file_content_missing = "{#if (a)} {#else}"
        with pytest.raises(IfControlMismatchError, match="Unmatched {#if}"):
            check_if_else_endif_structure(file_content_missing)

        # Double else for same if
        file_content_double_else = """
            {#if (a)}
            stuff
            {#else}
            alt
            {#else}
            should not happen
            {#endif}
        """
        with pytest.raises(IfControlMismatchError, match="Encountered second {#else}"):
            check_if_else_endif_structure(file_content_double_else)

    def test_error_standalone_elseif(self):
        # Standalone elseif without if
        file_content_standalone_elseif = """
            some text
            {#elseif (x)}
            invalid
            {#endif}
        """
        with pytest.raises(
            IfControlMismatchError,
            match="Encountered {#elseif} without matching {#if}",
        ):
            check_if_else_endif_structure(file_content_standalone_elseif)


class TestFileBalanceChecking:
    def test_valid_structure(self):
        file_content = """
            Some text {abc (xyz)}
            {#if (test)}
            {abc (def)}
            {#else}
            {xyz (uvw)}
            {#endif}
        """
        assert check_file_balance(file_content) == CheckFileBalanceResult.OK

    def test_unbalanced_braces(self):
        file_content = """
            {abc (xyz}
            {#if (test)}
            {#endif}
        """
        assert (
            check_file_balance(file_content)
            == CheckFileBalanceResult.MISMATCHED_PARENTHESIS
        )

        # Broken brace
        file_content_broken_braces = "Something {test"
        assert (
            check_file_balance(file_content_broken_braces)
            == CheckFileBalanceResult.MISMATCHED_BRACES
        )

    def test_control_flow_error(self):
        file_content = """
            {xyz (abc)}
            {#if (condition)}
        """
        assert (
            check_file_balance(file_content)
            == CheckFileBalanceResult.INVALID_FLOW_CONTROL
        )


class TestFileContentFixes:
    def test_naive_fixes(self):
        # One braced expression with missing parenthesis
        file_content = "Start {abc (xyz} End"
        fixed = fix_message_content(file_content)
        # Should have appended a ) inside the braces
        assert fixed == "Start {abc (xyz)} End"

        # Two braced expressions with missing parenthesis
        file_content_more_complex = "Start {(xyz} {((foo)} End"
        fixed2 = fix_message_content(file_content_more_complex)
        assert fixed2 == "Start {(xyz)} {((foo))} End"

    @pytest.mark.parametrize(
        "file_content, expected_result",
        [
            # Already valid => fix is a no-op
            ("{#if (x)}stuff{#endif}", CheckFileBalanceResult.OK),
            # Unbalanced => fix helps if it's just one missing parenthesis in a braced expr
            ("{#if (x)}stuff{#endif} Text {abc (xyz} ", CheckFileBalanceResult.OK),
            # Unbalanced => fix won't help if control flow is also broken
            ("{#if (x)}stuff", CheckFileBalanceResult.INVALID_FLOW_CONTROL),
        ],
    )
    def test_overall_fix_file_content_scenario(
        self, file_content: str, expected_result: bool
    ):
        # The naive fix addresses missing parenthesis in braces, not control-flow
        fixed = fix_message_content(file_content)
        result = check_file_balance(fixed)
        assert result == expected_result
