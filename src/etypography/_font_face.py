from __future__ import annotations

__all__ = [
    "FontFace",
    "FontFaceSize",
    "PrimaryAxisTextAlign",
    "RenderedGlyph",
    "RenderedGlyphFormat",
    "SecondaryAxisTextAlign",
    "TextLayout",
    "TextLine",
    "TextGlyph",
]


# etypography
from ._break_text import BreakText
from ._break_text import BreakTextChunk
from ._break_text import break_text_never
from ._unicode import character_is_normally_rendered

# egeometry
from egeometry import FRectangle

# emath
from emath import FVector2
from emath import UVector2

# freetype-py
from freetype import FT_ENCODING_UNICODE
from freetype import FT_Exception
from freetype import FT_RENDER_MODE_LCD
from freetype import FT_RENDER_MODE_LCD_V
from freetype import FT_RENDER_MODE_LIGHT
from freetype import FT_RENDER_MODE_SDF
from freetype import Face as FtFace

# python
from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum
from enum import StrEnum
from typing import BinaryIO
from typing import Callable
from typing import Generator
from typing import NamedTuple
from typing import Sequence

# uharfbuzz
from uharfbuzz import Buffer as HbBuffer
from uharfbuzz import Face as HbFace
from uharfbuzz import Font as HbFont
from uharfbuzz import shape as hb_shape


class RenderedGlyphFormat(Enum):
    ALPHA = FT_RENDER_MODE_LIGHT
    SDF = FT_RENDER_MODE_SDF
    LCD = FT_RENDER_MODE_LCD
    LCD_V = FT_RENDER_MODE_LCD_V


class FontFace:
    def __init__(self, file: BinaryIO):
        self._ft_face = FtFace(file)
        file.seek(0)
        self._hb_face = HbFace(file.read())
        self._hb_font = HbFont(self._hb_face)

        self._name = repr(file)
        if self._ft_face.family_name:
            self._name = self._ft_face.family_name.decode("ascii")
        if self._ft_face.postscript_name:
            self._name = self._ft_face.postscript_name.decode("ascii")

        self._ft_face.select_charmap(FT_ENCODING_UNICODE)

    def __repr__(self) -> str:
        return f"<FontFace {self._name!r}>"

    def get_glyph_index(self, character: str) -> int:
        if len(character) != 1:
            raise ValueError("only a single character may be entered")

        index = self._ft_face.get_char_index(character)
        assert isinstance(index, int)
        return index

    def request_point_size(
        self,
        *,
        width: float | None = None,
        height: float | None = None,
        dpi: UVector2 = UVector2(72, 72),
    ) -> FontFaceSize:
        if width is None and height is None:
            raise TypeError("width or height must be specified")
        return _PointFontFaceSize(
            self, 0 if width is None else (width * 64), 0 if height is None else (height * 64), dpi
        )

    def request_pixel_size(
        self,
        *,
        width: int | None = None,
        height: int | None = None,
    ) -> FontFaceSize:
        if width is None and height is None:
            raise TypeError("width or height must be specified")
        return _PixelFontFaceSize(
            self, 0 if width is None else width, 0 if height is None else height
        )

    def _get_glyph_size(self, character: int, size: FontFaceSize) -> FVector2:
        size._use()
        self._ft_face.load_glyph(character, 0)
        ft_glyph = self._ft_face.glyph
        return FVector2(
            ft_glyph.metrics.width / 64.0,
            ft_glyph.metrics.height / 64.0,
        )

    def render_glyph(
        self,
        character: str | int,
        size: FontFaceSize,
        *,
        format: RenderedGlyphFormat | None = None,
    ) -> RenderedGlyph:
        if format is None:
            format = RenderedGlyphFormat.ALPHA
        if isinstance(character, str) and len(character) != 1:
            raise ValueError("only a single character may be rendered")
        if size.face is not self:
            raise ValueError("size is not compatible with this face")

        size._use()
        if isinstance(character, str):
            self._ft_face.load_char(character, 0)
        else:
            try:
                self._ft_face.load_glyph(character, 0)
            except FT_Exception as ex:
                raise ValueError("face does not contain the specified glyph")

        ft_glyph = self._ft_face.glyph
        try:
            ft_glyph.render(format.value)
        except FT_Exception as ex:
            pass
        width = ft_glyph.bitmap.width
        height = ft_glyph.bitmap.rows
        data = bytes(ft_glyph.bitmap.buffer)
        if format == RenderedGlyphFormat.LCD:
            width = width // 3
            data = b"".join(
                (
                    bytes(
                        (
                            data[x * 3 + (y * ft_glyph.bitmap.pitch)],
                            data[x * 3 + 1 + (y * ft_glyph.bitmap.pitch)],
                            data[x * 3 + 2 + (y * ft_glyph.bitmap.pitch)],
                        )
                    )
                    for y in range(height)
                    for x in range(width)
                )
            )
        elif format == RenderedGlyphFormat.LCD_V:
            height = height // 3
            data = b"".join(
                (
                    bytes(
                        (
                            data[x + (y * 3 * ft_glyph.bitmap.pitch)],
                            data[x + ((y * 3 + 1) * ft_glyph.bitmap.pitch)],
                            data[x + ((y * 3 + 2) * ft_glyph.bitmap.pitch)],
                        )
                    )
                    for y in range(height)
                    for x in range(width)
                )
            )

        return RenderedGlyph(
            data,
            UVector2(width, height),
            FVector2(ft_glyph.bitmap_left, -ft_glyph.bitmap_top),
            format,
        )

    def layout_text(
        self,
        text: str,
        size: FontFaceSize,
        *,
        break_text: BreakText | None = None,
        max_line_size: int | None = None,
        is_character_rendered: Callable[[str], bool] | None = None,
        line_height: int | None = None,
        primary_axis_alignment: PrimaryAxisTextAlign | None = None,
        secondary_axis_alignment: SecondaryAxisTextAlign | None = None,
        origin: FVector2 | None = None,
    ) -> TextLayout | None:
        if break_text is None:
            break_text = break_text_never
        if is_character_rendered is None:
            is_character_rendered = character_is_normally_rendered
        if size.face is not self:
            raise ValueError("size is not compatible with this face")
        if primary_axis_alignment is None:
            primary_axis_alignment = PrimaryAxisTextAlign.BEGIN
        if secondary_axis_alignment is None:
            secondary_axis_alignment = SecondaryAxisTextAlign.BEGIN
        if origin is None:
            origin = FVector2(0)

        return _TextLayout(
            text,
            size,
            break_text,
            max_line_size,
            is_character_rendered,
            line_height,
            primary_axis_alignment,
            secondary_axis_alignment,
        ).to_text_layout(origin)

    @property
    def fixed_sizes(self) -> Sequence[FontFaceSize]:
        return tuple(
            _FixedFontFaceSize(self, i) for i, _ in enumerate(self._ft_face.available_sizes)
        )

    @property
    def name(self) -> str:
        return self._name


class PrimaryAxisTextAlign(StrEnum):
    BEGIN = "begin"
    END = "end"
    CENTER = "center"


class SecondaryAxisTextAlign(StrEnum):
    BEGIN = "begin"
    END = "end"
    CENTER = "center"
    BASELINE = "baseline"


@dataclass(slots=True)
class _PositionedGlyph:
    character: str
    glyph_index: int
    position: FVector2
    size: FVector2
    is_rendered: bool

    @property
    def extent(self) -> FVector2:
        return self.position + self.size


class _TextLineLayout:
    def __init__(self, position: FVector2):
        self.position = position
        self.size = FVector2(0)
        self.baseline_offset = FVector2(0)
        self.glyphs: list[_PositionedGlyph] = []

    def add_glyphs(
        self,
        glyphs: Sequence[_PositionedGlyph],
        advance: FVector2,
        baseline_offset: FVector2,
        size: float,
        max_size: int | None,
    ) -> bool:
        if max_size is not None and self.extent.x + advance.x > max_size:
            if self.glyphs:
                return False
        for glyph in glyphs:
            glyph.position += self.size.xo

        line_size = self.size.y
        if round(size) > line_size:
            line_size = round(size)
            self.baseline_offset = baseline_offset
        self.size = FVector2(self.size.x + advance.x, line_size)

        self.glyphs.extend(glyphs)
        return True

    @property
    def baseline(self) -> FVector2:
        baseline = self.position + self.size.oy + self.baseline_offset
        return FVector2(int(baseline.x), int(baseline.y))

    @property
    def extent(self) -> FVector2:
        return self.position + self.size

    @property
    def rendered_size(self) -> FVector2:
        for glyph in reversed(self.glyphs):
            if glyph.is_rendered:
                return FVector2(glyph.extent.x, self.size.y)
        return FVector2(0)


class _TextLayout:
    def __init__(
        self,
        text: str,
        size: FontFaceSize,
        break_text: BreakText,
        max_line_size: int | None,
        is_character_rendered: Callable[[str], bool],
        line_height: int | None,
        primary_axis_alignment: PrimaryAxisTextAlign,
        secondary_axis_alignment: SecondaryAxisTextAlign,
    ):
        self._font_face_size = size

        self.is_character_rendered = is_character_rendered

        self.line_height = round(size._line_size.y) if line_height is None else line_height
        self.max_line_size = max_line_size
        self.lines: list[_TextLineLayout] = [_TextLineLayout(FVector2(0))]

        self._hb_font = size._face._hb_font
        self._hb_font.scale = size._scale
        for chunk in break_text(text):
            self._add_chunk(chunk)

        self._h_align(primary_axis_alignment)
        self._v_align(secondary_axis_alignment)

        self.position = FVector2(
            min(line.position.x for line in self.lines), self.lines[0].position.y
        )
        self.size = FVector2(
            max(line.rendered_size.x for line in self.lines),
            self.lines[-1].extent.y - self.position.y,
        )

    def _add_chunk(self, chunk: BreakTextChunk) -> None:
        chunk_glyphs: list[_PositionedGlyph] = []
        pen_position = FVector2(0)

        hb_buffer = HbBuffer()
        hb_buffer.direction = "LTR"
        hb_buffer.add_str(chunk.text)
        hb_shape(self._hb_font, hb_buffer, {})

        for info, pos in zip(hb_buffer.glyph_infos, hb_buffer.glyph_positions):
            c = chunk.text[info.cluster]
            chunk_glyphs.append(
                _PositionedGlyph(
                    c,
                    info.codepoint,
                    pen_position + FVector2(pos.x_offset / 64.0, pos.y_offset / 64.0),
                    self._font_face_size._face._get_glyph_size(
                        info.codepoint, self._font_face_size
                    ),
                    self.is_character_rendered(c),
                )
            )
            pen_position += FVector2(pos.x_advance / 64.0, pos.y_advance / 64.0)

        self._add_chunk_glyphs(chunk, chunk_glyphs, pen_position)

    def _add_chunk_glyphs(
        self, chunk: BreakTextChunk, chunk_glyphs: Sequence[_PositionedGlyph], advance: FVector2
    ) -> None:
        glyphs_added = self.lines[-1].add_glyphs(
            chunk_glyphs,
            advance,
            self._font_face_size._baseline_offset,
            self._font_face_size._line_size.y,
            self.max_line_size,
        )

        if not glyphs_added or chunk.force_break:
            line = _TextLineLayout(FVector2(0, sum((l.size.y for l in self.lines))))
            self.lines.append(line)

            if not glyphs_added:
                line.add_glyphs(
                    chunk_glyphs,
                    advance,
                    self._font_face_size._baseline_offset,
                    self._font_face_size._line_size.y,
                    self.max_line_size,
                )

    def _h_align(self, align: PrimaryAxisTextAlign) -> None:
        getattr(self, f"_h_align_{align.value}")()

    def _h_align_begin(self) -> None:
        pass

    def _h_align_center(self) -> None:
        for line in self.lines:
            line.position -= line.rendered_size.xo * 0.5

    def _h_align_end(self) -> None:
        for line in self.lines:
            line.position -= line.rendered_size.xo

    def _v_align(self, align: SecondaryAxisTextAlign) -> None:
        getattr(self, f"_v_align_{align.value}")()

    def _v_align_begin(self) -> None:
        pass

    def _v_align_center(self) -> None:
        center = FVector2(0, self.line_height * len(self.lines) * 0.5)
        for line in self.lines:
            line.position -= center

    def _v_align_end(self) -> None:
        end = FVector2(0, self.line_height * len(self.lines))
        for line in self.lines:
            line.position -= end

    def _v_align_baseline(self) -> None:
        baseline = FVector2(0, self.line_height)
        for line in self.lines:
            line.position -= baseline

    def to_text_layout(self, origin: FVector2) -> TextLayout | None:
        if not self.size:
            return None
        return TextLayout(
            FRectangle(origin + self.position, self.size),
            tuple(
                TextLine(
                    FRectangle(origin + line.position, line.rendered_size),
                    tuple(
                        TextGlyph(
                            FRectangle(origin + line.baseline + glyph.position, glyph.size),
                            glyph.character,
                            glyph.glyph_index,
                        )
                        for glyph in line.glyphs
                        if glyph.is_rendered and glyph.size
                    ),
                )
                for line in self.lines
                if line.rendered_size
            ),
        )


class TextGlyph(NamedTuple):
    bounding_box: FRectangle
    character: str
    glyph_index: int


class TextLine(NamedTuple):
    bounding_box: FRectangle
    glyphs: tuple[TextGlyph, ...]


class TextLayout(NamedTuple):
    bounding_box: FRectangle
    lines: tuple[TextLine, ...]

    @property
    def glyphs(self) -> Generator[TextGlyph, None, None]:
        for line in self.lines:
            yield from line.glyphs


class RenderedGlyph(NamedTuple):
    data: bytes
    size: UVector2
    bearing: FVector2
    format: RenderedGlyphFormat


class FontFaceSize(ABC):
    def __init__(self, face: FontFace):
        self._face = face
        self._use()
        self._nominal_size = UVector2(
            self._face._ft_face.size.x_ppem,
            self._face._ft_face.size.y_ppem,
        )
        self._scale = (
            self._face._ft_face.size.x_scale * self._face._ft_face.units_per_EM + (1 << 15) >> 16,
            self._face._ft_face.size.y_scale * self._face._ft_face.units_per_EM + (1 << 15) >> 16,
        )
        self._line_size = FVector2(
            0.0,  # how
            self._face._ft_face.size.height / 64.0,
        )
        self._baseline_offset = FVector2(0, self._face._ft_face.size.descender / 64.0)  # how

    def __repr__(self) -> str:
        return f"<FontFaceSize for {self._face.name!r} of {self.nominal_size}>"

    @abstractmethod
    def _use(self) -> None:
        ...

    @property
    def face(self) -> FontFace:
        return self._face

    @property
    def nominal_size(self) -> UVector2:
        return self._nominal_size


class _PointFontFaceSize(FontFaceSize):
    def __init__(self, face: FontFace, width: float | None, height: float | None, dpi: UVector2):
        self._args = (width, height, dpi.x, dpi.y)
        super().__init__(face)

    def _use(self) -> None:
        self.face._ft_face.set_char_size(*self._args)


class _PixelFontFaceSize(FontFaceSize):
    def __init__(self, face: FontFace, width: int | None, height: int | None):
        self._args = (width, height)
        super().__init__(face)

    def _use(self) -> None:
        self.face._ft_face.set_pixel_sizes(*self._args)


class _FixedFontFaceSize(FontFaceSize):
    def __init__(self, face: FontFace, index: int):
        self._index = index
        super().__init__(face)

    def _use(self) -> None:
        self.face._ft_face.select_size(self._index)
