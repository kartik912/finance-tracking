"""Unit tests for apply_text_format and parse_markdown_spans — the pure
text-transformation helpers used by the B / I / U buttons in the note editor.

These tests do NOT need a running Flet page or database — both functions are
module-level functions with no UI dependencies (parse_markdown_spans does
import flet for TextSpan/TextStyle, but those are pure data objects with no
page context required).
"""
from __future__ import annotations

import flet as ft
import pytest

from screens.note_editor import apply_text_format, parse_markdown_spans


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bold(text: str, start: int = -1, end: int = -1) -> str:
    return apply_text_format(text, start, end, "**", "**", "bold")


def _italic(text: str, start: int = -1, end: int = -1) -> str:
    return apply_text_format(text, start, end, "_", "_", "italic")


def _underline(text: str, start: int = -1, end: int = -1) -> str:
    return apply_text_format(text, start, end, "<u>", "</u>", "underline")


# ---------------------------------------------------------------------------
# Selection-based wrapping
# ---------------------------------------------------------------------------

class TestSelectionWrapping:
    def test_bold_wraps_whole_word(self) -> None:
        assert _bold("hello world", 6, 11) == "hello **world**"

    def test_italic_wraps_whole_word(self) -> None:
        assert _italic("hello world", 0, 5) == "_hello_ world"

    def test_underline_wraps_mid_word(self) -> None:
        assert _underline("text", 1, 3) == "t<u>ex</u>t"

    def test_bold_wraps_entire_text(self) -> None:
        assert _bold("full", 0, 4) == "**full**"

    def test_italic_wraps_single_char(self) -> None:
        assert _italic("abc", 1, 2) == "a_b_c"

    def test_underline_wraps_with_leading_trailing_space(self) -> None:
        # Only the content inside the selection is wrapped, spaces outside stay
        assert _underline("  hi  ", 2, 4) == "  <u>hi</u>  "

    def test_tags_are_adjacent_when_selection_at_start(self) -> None:
        assert _bold("abc", 0, 1) == "**a**bc"

    def test_tags_are_adjacent_when_selection_at_end(self) -> None:
        assert _bold("abc", 2, 3) == "ab**c**"


# ---------------------------------------------------------------------------
# No-selection: placeholder insertion
# ---------------------------------------------------------------------------

class TestPlaceholderInsertion:
    def test_bold_appends_placeholder_on_empty_field(self) -> None:
        assert _bold("") == "**bold**"

    def test_italic_appends_placeholder_on_empty_field(self) -> None:
        assert _italic("") == "_italic_"

    def test_underline_appends_placeholder_on_empty_field(self) -> None:
        assert _underline("") == "<u>underline</u>"

    def test_bold_appends_when_start_negative(self) -> None:
        # start=-1 means no selection info — append at end
        assert _bold("hello", -1, -1) == "hello**bold**"

    def test_bold_inserts_at_cursor_position(self) -> None:
        # start==end==5 means cursor at index 5 (between 'o' and ' ')
        assert _bold("hello world", 5, 5) == "hello**bold** world"

    def test_italic_inserts_at_cursor_position_zero(self) -> None:
        assert _italic("text", 0, 0) == "_italic_text"

    def test_italic_inserts_at_end_cursor(self) -> None:
        assert _italic("text", 4, 4) == "text_italic_"

    def test_placeholder_content_is_correct_for_each_format(self) -> None:
        assert "bold" in _bold("")
        assert "italic" in _italic("")
        assert "underline" in _underline("")


# ---------------------------------------------------------------------------
# Edge / boundary cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_start_equals_end_uses_placeholder(self) -> None:
        """start == end is a cursor (no selection) so placeholder must be inserted."""
        result = _bold("abc", 2, 2)
        assert result == "ab**bold**c"

    def test_end_less_than_start_treated_as_no_selection(self) -> None:
        """apply_text_format receives raw start/end — it does NOT normalise them.
        The caller (_apply_format) does min/max normalisation before calling.
        So passing (3, 1) → condition 0<=3<1 is False → placeholder at pos=3."""
        result = apply_text_format("abc", 3, 1, "**", "**", "bold")
        assert result == "abc**bold**"

    def test_start_beyond_text_length_appends(self) -> None:
        """If cursor is past end of text, insertion is at end."""
        result = _bold("hi", 10, 10)
        assert result == "hi**bold**"

    def test_empty_open_and_close_tags_returns_text_unchanged(self) -> None:
        result = apply_text_format("hello", 0, 5, "", "", "placeholder")
        assert result == "hello"  # wrap: "" + "hello" + "" == "hello"

    def test_multiline_text_wraps_selection_correctly(self) -> None:
        text = "line1\nline2\nline3"
        # Select "line2" (chars 6–11)
        assert _italic(text, 6, 11) == "line1\n_line2_\nline3"

    def test_unicode_text_wraps_correctly(self) -> None:
        text = "नमस्ते"
        assert _bold(text, 0, len(text)) == f"**{text}**"


# ---------------------------------------------------------------------------
# Format-bar lambda arity regression guard
# ---------------------------------------------------------------------------

class TestFormatBarLambdaArity:
    """Regression guard: format-bar lambdas must call _apply_format with 3 args.

    The QA contract requires every format-bar lambda to pass
    _apply_format(open_tag, close_tag, placeholder).  A 2-arg call means the
    inner helper omits the placeholder, so clicking Bold/Italic/Underline with
    no text selected inserts empty markers (e.g. ****) rather than readable
    placeholder text (e.g. **bold**).
    """

    def test_format_bar_bold_uses_3_args(self) -> None:
        """Grep note_editor.py for 2-arg _apply_format calls — any match is a BLOCK."""
        import re
        import pathlib

        src = pathlib.Path("screens/note_editor.py").read_text(encoding="utf-8")
        # Matches: _apply_format("...", "...") with NO third argument before the closing paren
        two_arg_pattern = re.compile(r'_apply_format\("[^"]*",\s*"[^"]*"\)')
        matches = two_arg_pattern.findall(src)
        assert matches == [], (
            f"Found {len(matches)} 2-arg _apply_format call(s) — lambdas must use "
            f"3 args: _apply_format(open, close, placeholder). "
            f"Offending calls: {matches}"
        )


# ---------------------------------------------------------------------------
# parse_markdown_spans — rich-text conversion
# ---------------------------------------------------------------------------

class TestParseMarkdownSpans:
    """parse_markdown_spans is a module-level pure function: no Flet page needed.

    Covers plain text, each individual format tag, mixed content, and the
    empty-string boundary case — all required by the QA workflow Step 6.
    """

    # --- helpers -----------------------------------------------------------

    @staticmethod
    def _texts(spans: list[ft.TextSpan]) -> list[str | None]:
        """Return the .text value of every span for easy equality checks."""
        return [s.text for s in spans]

    @staticmethod
    def _styles(spans: list[ft.TextSpan]) -> list[ft.TextStyle | None]:
        return [s.style for s in spans]

    # --- plain text --------------------------------------------------------

    def test_plain_text_returns_single_span(self) -> None:
        spans = parse_markdown_spans("hello world")
        assert len(spans) == 1
        assert spans[0].text == "hello world"
        assert spans[0].style is None

    def test_plain_text_with_no_markers_has_no_style(self) -> None:
        spans = parse_markdown_spans("just some text")
        assert all(s.style is None for s in spans)

    # --- empty string ------------------------------------------------------

    def test_empty_string_returns_one_span(self) -> None:
        """Empty input must not crash and must return exactly one TextSpan."""
        spans = parse_markdown_spans("")
        assert len(spans) == 1
        assert spans[0].text == ""

    # --- bold (**...**) ----------------------------------------------------

    def test_bold_only_returns_bold_span(self) -> None:
        spans = parse_markdown_spans("**bold**")
        assert len(spans) == 1
        assert spans[0].text == "bold"
        assert spans[0].style is not None
        assert spans[0].style.weight == ft.FontWeight.BOLD

    def test_bold_surrounded_by_plain_text(self) -> None:
        spans = parse_markdown_spans("Hello **world** foo")
        assert self._texts(spans) == ["Hello ", "world", " foo"]
        assert spans[0].style is None
        assert spans[1].style.weight == ft.FontWeight.BOLD
        assert spans[2].style is None

    # --- italic (_..._) ---------------------------------------------------

    def test_italic_only_returns_italic_span(self) -> None:
        spans = parse_markdown_spans("_italic_")
        assert len(spans) == 1
        assert spans[0].text == "italic"
        assert spans[0].style is not None
        assert spans[0].style.italic is True

    def test_italic_surrounded_by_plain_text(self) -> None:
        spans = parse_markdown_spans("one _two_ three")
        assert self._texts(spans) == ["one ", "two", " three"]
        assert spans[1].style.italic is True

    # --- underline (<u>...</u>) -------------------------------------------

    def test_underline_only_returns_underline_span(self) -> None:
        spans = parse_markdown_spans("<u>underline</u>")
        assert len(spans) == 1
        assert spans[0].text == "underline"
        assert spans[0].style is not None
        assert spans[0].style.decoration == ft.TextDecoration.UNDERLINE

    def test_underline_surrounded_by_plain_text(self) -> None:
        spans = parse_markdown_spans("a <u>b</u> c")
        assert self._texts(spans) == ["a ", "b", " c"]
        assert spans[1].style.decoration == ft.TextDecoration.UNDERLINE

    # --- mixed content ----------------------------------------------------

    def test_bold_then_italic(self) -> None:
        spans = parse_markdown_spans("**bold** and _italic_")
        assert self._texts(spans) == ["bold", " and ", "italic"]
        assert spans[0].style.weight == ft.FontWeight.BOLD
        assert spans[1].style is None
        assert spans[2].style.italic is True

    def test_all_three_formats_in_sequence(self) -> None:
        spans = parse_markdown_spans("**b** _i_ <u>u</u>")
        assert self._texts(spans) == ["b", " ", "i", " ", "u"]
        assert spans[0].style.weight == ft.FontWeight.BOLD
        assert spans[2].style.italic is True
        assert spans[4].style.decoration == ft.TextDecoration.UNDERLINE

    def test_format_at_start_and_end_no_leading_trailing_plain(self) -> None:
        """No phantom empty plain-text spans at the boundaries."""
        spans = parse_markdown_spans("**bold**")
        assert len(spans) == 1  # no empty leading/trailing span

    def test_plain_text_between_two_bold_markers(self) -> None:
        spans = parse_markdown_spans("**a** middle **b**")
        assert self._texts(spans) == ["a", " middle ", "b"]
        assert spans[0].style.weight == ft.FontWeight.BOLD
        assert spans[1].style is None
        assert spans[2].style.weight == ft.FontWeight.BOLD

    # --- multiline --------------------------------------------------------

    def test_multiline_bold_span(self) -> None:
        text = "line1\n**bold line**\nline3"
        spans = parse_markdown_spans(text)
        texts = self._texts(spans)
        assert "bold line" in texts
        bold_span = next(s for s in spans if s.text == "bold line")
        assert bold_span.style.weight == ft.FontWeight.BOLD
