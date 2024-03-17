# etext
from . import resources

# etext
import etext
from etext import FontFace
from etext import FontFaceSize
from etext import PrimaryAxisTextAlign
from etext import RenderedGlyphFormat
from etext import SecondaryAxisTextAlign
from etext import break_text_never
from etext import character_is_normally_rendered

# egeometry
from egeometry import FRectangle2d

# emath
from emath import FVector2
from emath import UVector2

# pytest
import pytest

# python
import json
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch


@pytest.fixture(params=["OpenSans-Regular.ttf"])
def face(request, resource_dir):
    with open(resource_dir / request.param, "rb") as file:
        face = FontFace(file)
    yield face


def test_name_open_sans_regular(resource_dir):
    with open(resource_dir / "OpenSans-Regular.ttf", "rb") as file:
        face = FontFace(file)
    assert face.name == "OpenSans-Regular"


def test_repr_open_sans_regular(resource_dir):
    with open(resource_dir / "OpenSans-Regular.ttf", "rb") as file:
        face = FontFace(file)
    assert repr(face) == f"<FontFace {face.name!r}>"


@pytest.mark.parametrize("character", ["a", "z", "A", "Z", "\n", "食", "\u2028"])
def test_get_glyph_index(face, character):
    glyph_index = face.get_glyph_index(character)
    assert isinstance(glyph_index, int)


@pytest.mark.parametrize(
    "character",
    ["", "aZ", "食食"],
)
def test_get_glyph_index_invalid_length(face, character):
    with pytest.raises(ValueError) as excinfo:
        face.get_glyph_index(character)
    assert str(excinfo.value) == "only a single character may be entered"


def test_request_point_size_no_dimensions(face) -> None:
    with pytest.raises(TypeError) as excinfo:
        face.request_point_size()
    assert str(excinfo.value) == "width or height must be specified"


@pytest.mark.parametrize(
    "width, height",
    [
        (10, None),
        (None, 10),
        (10, 10),
        (20, None),
        (None, 20),
        (20, 20),
        (20, 25),
        (25, 20),
    ],
)
@pytest.mark.parametrize(
    "dpi",
    [None, UVector2(72, 72), UVector2(144, 72), UVector2(72, 144), UVector2(144, 144)],
)
def test_request_point_size(face, width, height, dpi):
    kwargs = {}
    if width is not None:
        kwargs["width"] = width
    if height is not None:
        kwargs["height"] = height
    if dpi is not None:
        kwargs["dpi"] = dpi
    else:
        dpi = (72, 72)
    expected_nominal_size = UVector2(
        int((height if width is None else width) * (dpi[0] / 72.0)),
        int((width if height is None else height) * (dpi[1] / 72.0)),
    )

    size = face.request_point_size(**kwargs)
    assert isinstance(size, FontFaceSize)
    assert size.face is face

    nominal_size = size.nominal_size
    assert isinstance(nominal_size, UVector2)
    assert nominal_size == expected_nominal_size
    nominal_size += UVector2(1, 1)
    assert size.nominal_size is not nominal_size
    assert size.nominal_size != nominal_size


def test_request_pixel_size_no_dimensions(face):
    with pytest.raises(TypeError) as excinfo:
        face.request_pixel_size()
    assert str(excinfo.value) == "width or height must be specified"


@pytest.mark.parametrize(
    "width, height",
    [
        (10, None),
        (None, 10),
        (10, 10),
        (20, None),
        (None, 20),
        (20, 20),
        (20, 25),
        (25, 20),
    ],
)
def test_request_pixel_size(face, width, height) -> None:
    kwargs = {}
    if width is not None:
        kwargs["width"] = width
    if height is not None:
        kwargs["height"] = height
    expected_nominal_size = UVector2(
        height if width is None else width,
        width if height is None else height,
    )

    size = face.request_pixel_size(**kwargs)
    assert isinstance(size, FontFaceSize)
    assert size.face is face

    nominal_size = size.nominal_size
    assert isinstance(nominal_size, UVector2)
    assert nominal_size == expected_nominal_size
    nominal_size += UVector2(1, 1)
    assert size.nominal_size is not nominal_size
    assert size.nominal_size != nominal_size


def test_fixed_sizes(face) -> None:
    fixed_sizes = face.fixed_sizes
    assert isinstance(fixed_sizes, tuple)
    assert len(fixed_sizes) == 0


@pytest.mark.parametrize("character", ["", "ab"])
def test_render_glyph_invalid_character(face, character):
    size = face.request_pixel_size(height=10)
    with pytest.raises(ValueError) as excinfo:
        face.render_glyph(character, size)
    assert str(excinfo.value) == "only a single character may be rendered"


def test_render_glyph_invalid_size(resource_dir, face):
    with open(resource_dir / "OpenSans-Regular.ttf", "rb") as file:
        other_face = FontFace(file)
    size = other_face.request_pixel_size(height=10)
    with pytest.raises(ValueError) as excinfo:
        face.render_glyph("a", size)
    assert str(excinfo.value) == "size is not compatible with this face"


@pytest.mark.parametrize("glyph_index", [-1000, -1, 999999])
def test_render_glyph_invalid_index(face, glyph_index):
    size = face.request_pixel_size(height=10)
    with pytest.raises(ValueError) as excinfo:
        face.render_glyph(glyph_index, size)
    assert str(excinfo.value) == "face does not contain the specified glyph"


@pytest.mark.parametrize("character", ["a", "Z", "1"])
@pytest.mark.parametrize("use_glyph_index", [False, True])
@pytest.mark.parametrize("format", [None] + list(RenderedGlyphFormat))
def test_render_glyph(face, character, use_glyph_index, format):
    size = face.request_pixel_size(height=10)
    input: Union[str, int]
    if use_glyph_index:
        input = face.get_glyph_index(character)
    else:
        input = character
    kwargs: dict[str, Any] = {}
    if format is not None:
        kwargs["format"] = format
    else:
        format = RenderedGlyphFormat.ALPHA
    rendered_glyph = face.render_glyph(input, size, **kwargs)

    assert isinstance(rendered_glyph.data, bytes)
    assert rendered_glyph.data
    assert len(rendered_glyph.data) == (
        rendered_glyph.size.x
        * rendered_glyph.size.y
        * (3 if format in (RenderedGlyphFormat.LCD, RenderedGlyphFormat.LCD_V) else 1)
    )

    assert isinstance(rendered_glyph.size, UVector2)
    assert rendered_glyph.size.x > 0
    assert rendered_glyph.size.y > 0
    rendered_glyph_size = rendered_glyph.size
    rendered_glyph_size += UVector2(1, 1)
    assert rendered_glyph.size != rendered_glyph_size

    assert isinstance(rendered_glyph.bearing, FVector2)
    rendered_glyph_bearing = rendered_glyph.bearing
    rendered_glyph_bearing += FVector2(1, 1)
    assert rendered_glyph.bearing != rendered_glyph_bearing

    assert rendered_glyph.format is format


def test_layout_text_invalid_size(resource_dir, face):
    with open(resource_dir / "OpenSans-Regular.ttf", "rb") as file:
        other_face = FontFace(file)
    size = other_face.request_pixel_size(height=10)
    with pytest.raises(ValueError) as excinfo:
        face.layout_text("a", size)
    assert str(excinfo.value) == "size is not compatible with this face"


@pytest.mark.parametrize("text", ["a", "bcdef"])
@pytest.mark.parametrize("break_text", [None, MagicMock()])
@pytest.mark.parametrize("max_line_size", [None, 100])
@pytest.mark.parametrize("is_character_rendered", [None, MagicMock()])
@pytest.mark.parametrize("line_height", [None, 101])
@pytest.mark.parametrize("primary_axis_alignment", [None, *PrimaryAxisTextAlign])
@pytest.mark.parametrize("secondary_axis_alignment", [None, *SecondaryAxisTextAlign])
@pytest.mark.parametrize("origin", [None, FVector2(-1, 1)])
def test_layout_text(
    face,
    text,
    break_text,
    max_line_size,
    is_character_rendered,
    line_height,
    primary_axis_alignment,
    secondary_axis_alignment,
    origin,
):
    size = face.request_pixel_size(height=10)

    kwargs = {}

    if break_text is None:
        expected_break_text = break_text_never
    else:
        kwargs["break_text"] = expected_break_text = break_text

    if max_line_size is None:
        expected_max_line_size = None
    else:
        kwargs["max_line_size"] = expected_max_line_size = max_line_size

    if is_character_rendered is None:
        expected_is_character_rendered = character_is_normally_rendered
    else:
        kwargs["is_character_rendered"] = expected_is_character_rendered = is_character_rendered

    if line_height is None:
        expected_line_height = None
    else:
        kwargs["line_height"] = expected_line_height = line_height

    if primary_axis_alignment is None:
        expected_primary_axis_alignment = PrimaryAxisTextAlign.BEGIN
    else:
        kwargs["primary_axis_alignment"] = expected_primary_axis_alignment = primary_axis_alignment

    if secondary_axis_alignment is None:
        expected_secondary_axis_alignment = SecondaryAxisTextAlign.BEGIN
    else:
        kwargs[
            "secondary_axis_alignment"
        ] = expected_secondary_axis_alignment = secondary_axis_alignment

    if origin is None:
        expected_origin = FVector2(0)
    else:
        kwargs["origin"] = expected_origin = origin

    text_layout = MagicMock()
    with patch("etext._font_face._TextLayout", return_value=text_layout) as TextLayoutMock:
        result = face.layout_text(text, size, **kwargs)

    TextLayoutMock.assert_called_once_with(
        text,
        size,
        expected_break_text,
        expected_max_line_size,
        expected_is_character_rendered,
        expected_line_height,
        expected_primary_axis_alignment,
        expected_secondary_axis_alignment,
    )
    text_layout.to_text_layout.assert_called_once_with(expected_origin)
    assert result is text_layout.to_text_layout.return_value


TEXT_LAYOUT_DIRECTORY = Path(resources.__file__).parent / "text-layout"
TEXT_LAYOUT_FILES = [
    TEXT_LAYOUT_DIRECTORY / o for o in TEXT_LAYOUT_DIRECTORY.iterdir() if o.suffix == ".json"
]


@pytest.mark.parametrize(
    "fixture_file_path", TEXT_LAYOUT_FILES, ids=[f.stem for f in TEXT_LAYOUT_FILES]
)
def test_text_layout(resource_dir, fixture_file_path):
    with open(fixture_file_path, "r", encoding="utf8") as fixture_file:
        fixture = json.load(fixture_file)

    with open(resource_dir / fixture["font"], "rb") as font_file:
        face = FontFace(font_file)

    get_face_size = getattr(face, fixture["size"]["method"])
    face_size = get_face_size(**fixture["size"]["kwargs"])

    text_layout = face.layout_text(
        fixture["layout_text_kwargs"]["text"],
        face_size,
        primary_axis_alignment=PrimaryAxisTextAlign(
            fixture["layout_text_kwargs"]["primary_axis_alignment"]
        ),
        secondary_axis_alignment=SecondaryAxisTextAlign(
            fixture["layout_text_kwargs"]["secondary_axis_alignment"]
        ),
        break_text=getattr(etext, fixture["layout_text_kwargs"]["break_text"]),
        max_line_size=fixture["layout_text_kwargs"]["max_line_size"],
        origin=FVector2(256),
        line_height=fixture["layout_text_kwargs"]["line_height"],
    )

    if text_layout is None:
        assert fixture["text_layout"] is None
    else:
        assert text_layout == (
            FRectangle2d(
                FVector2(*fixture["text_layout"]["position"]),
                FVector2(*fixture["text_layout"]["size"]),
            ),
            tuple(
                (
                    FRectangle2d(FVector2(*line["position"]), FVector2(*line["size"])),
                    tuple(
                        (
                            FRectangle2d(FVector2(*glyph["position"]), FVector2(*glyph["size"])),
                            glyph["character"],
                            glyph["glyph_index"],
                        )
                        for glyph in line["glyphs"]
                    ),
                )
                for line in fixture["text_layout"]["lines"]
            ),
        )
