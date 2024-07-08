# etypography
from etypography import Font
from etypography import PrimaryAxisTextAlign
from etypography import RenderedGlyphFormat
from etypography import SecondaryAxisTextAlign

# emath
from emath import FVector2

# pytest
import pytest

# python
from unittest.mock import Mock


def test_properties():
    size = Mock()
    font = Font(size)

    assert font.size is size
    assert font.face is size.face


def test_repr():
    size = Mock()
    size.nominal_size = [1, 2, 3]
    font = Font(size)

    assert repr(font) == f"<Font {size.face.name} of {tuple(size.nominal_size)}>"


@pytest.mark.parametrize("character", ["a", "私"])
def test_get_glyph_index(character):
    size = Mock()
    font = Font(size)

    index = font.get_glyph_index(character)
    size.face.get_glyph_index.assert_called_once_with(character)
    assert index == size.face.get_glyph_index(character)


@pytest.mark.parametrize("character", ["a", "私", 1])
@pytest.mark.parametrize("format", [None] + list(RenderedGlyphFormat))
def test_render_glyph(character, format):
    size = Mock()
    font = Font(size)

    kwargs = {}
    if format is not None:
        kwargs["format"] = format

    rendered_glyph = font.render_glyph(character, **kwargs)
    size.face.render_glyph.assert_called_once_with(character, size, format=format)
    assert rendered_glyph == size.face.render_glyph(character, size, **kwargs)


@pytest.mark.parametrize("text", ["a", "bcdef"])
@pytest.mark.parametrize("break_text", [None, Mock()])
@pytest.mark.parametrize("max_line_size", [None, 100])
@pytest.mark.parametrize("is_character_rendered", [None, Mock()])
@pytest.mark.parametrize("line_height", [None, 101])
@pytest.mark.parametrize("primary_axis_alignment", [None, *PrimaryAxisTextAlign])
@pytest.mark.parametrize("secondary_axis_alignment", [None, *SecondaryAxisTextAlign])
@pytest.mark.parametrize("origin", [None, FVector2(-1, 1)])
def test_layout_text(
    text,
    break_text,
    max_line_size,
    is_character_rendered,
    line_height,
    primary_axis_alignment,
    secondary_axis_alignment,
    origin,
):
    size = Mock()
    font = Font(size)

    kwargs = {}

    if break_text is not None:
        kwargs["break_text"] = expected_break_text = break_text

    if max_line_size is not None:
        kwargs["max_line_size"] = max_line_size

    if is_character_rendered is not None:
        kwargs["is_character_rendered"] = is_character_rendered

    if line_height is not None:
        kwargs["line_height"] = line_height

    if primary_axis_alignment is not None:
        kwargs["primary_axis_alignment"] = primary_axis_alignment

    if secondary_axis_alignment is not None:
        kwargs["secondary_axis_alignment"] = secondary_axis_alignment

    if origin is not None:
        kwargs["origin"] = origin

    text_layout = font.layout_text(text, **kwargs)
    size.face.layout_text.assert_called_once_with(
        text,
        size,
        break_text=break_text,
        max_line_size=max_line_size,
        is_character_rendered=is_character_rendered,
        line_height=line_height,
        primary_axis_alignment=primary_axis_alignment,
        secondary_axis_alignment=secondary_axis_alignment,
        origin=origin,
    )
    assert text_layout == size.face.layout_text(text, size, **kwargs)
