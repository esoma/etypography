from __future__ import annotations

__all__ = ["Font"]

# etypography
from ._break_text import BreakText
from ._font_face import FontFace
from ._font_face import FontFaceSize
from ._font_face import PrimaryAxisTextAlign
from ._font_face import RenderedGlyph
from ._font_face import RenderedGlyphFormat
from ._font_face import SecondaryAxisTextAlign
from ._font_face import TextLayout

# emath
from emath import FVector2

# python
from typing import Callable


class Font:
    def __init__(self, size: FontFaceSize):
        self._size = size

    def __repr__(self) -> str:
        return f"<Font {self._size.face.name!r} of {tuple(self._size.nominal_size)}>"

    def get_glyph_index(self, character: str) -> int:
        return self._size.face.get_glyph_index(character)

    def render_glyph(
        self, character: str | int, *, format: RenderedGlyphFormat | None = None
    ) -> RenderedGlyph:
        return self._size.face.render_glyph(character, self._size, format=format)

    def layout_text(
        self,
        text: str,
        *,
        break_text: BreakText | None = None,
        max_line_size: int | None = None,
        is_character_rendered: Callable[[str], bool] | None = None,
        line_height: int | None = None,
        primary_axis_alignment: PrimaryAxisTextAlign | None = None,
        secondary_axis_alignment: SecondaryAxisTextAlign | None = None,
        origin: FVector2 | None = None,
    ) -> TextLayout | None:
        return self._size.layout_text(
            text,
            break_text=break_text,
            max_line_size=max_line_size,
            is_character_rendered=is_character_rendered,
            line_height=line_height,
            primary_axis_alignment=primary_axis_alignment,
            secondary_axis_alignment=secondary_axis_alignment,
            origin=origin,
        )

    @property
    def size(self) -> FontFaceSize:
        return self._size

    @property
    def face(self) -> FontFace:
        return self._size.face
