import pytest

from etypography import BreakTextChunk
from etypography import break_text_icu_line
from etypography import break_text_never


@pytest.mark.parametrize("func", [break_text_never, break_text_icu_line])
def test_empty_string(func):
    assert list(func("")) == []


@pytest.mark.parametrize("text", ["hello world", "there is a\nnewline"])
def test_break_text_never(text):
    assert list(break_text_never(text)) == [BreakTextChunk(text, False)]


@pytest.mark.parametrize(
    "text, expected_result",
    [
        ("hello world", [BreakTextChunk("hello ", False), BreakTextChunk("world", False)]),
        (
            "there is a\nnewline",
            [
                BreakTextChunk("there ", False),
                BreakTextChunk("is ", False),
                BreakTextChunk("a\n", True),
                BreakTextChunk("newline", False),
            ],
        ),
        (
            "こんにちは、世界",
            [
                BreakTextChunk("こ", False),
                BreakTextChunk("ん", False),
                BreakTextChunk("に", False),
                BreakTextChunk("ち", False),
                BreakTextChunk("は、", False),
                BreakTextChunk("世", False),
                BreakTextChunk("界", False),
            ],
        ),
    ],
)
def test_break_text_icu_line(text, expected_result):
    assert list(break_text_icu_line(text)) == expected_result
