__all__ = ()

# etypography
from etypography import FontFace
from etypography import PrimaryAxisTextAlign
from etypography import SecondaryAxisTextAlign
from etypography import break_text_icu_line

# click
import click

# pillow
from PIL import Image

# python
from pathlib import Path
import re

EXAMPLES_DIRECTORY = Path(__file__).parent


def get_pixel_size(ctx, param, value):
    match = re.match(r"^(\d+)(px|pt)$", value)
    if not match:
        raise click.BadParameter(repr(value))
    return (int(match.group(1)), match.group(2))


@click.command()
@click.argument("text", type=click.STRING)
@click.option(
    "-f",
    "--font",
    type=click.Path(exists=True, dir_okay=False),
    default=EXAMPLES_DIRECTORY / "resources/OpenSans-Regular.ttf",
    show_default=True,
    help="The font file to render.",
)
@click.option(
    "-s",
    "--size",
    type=click.STRING,
    callback=get_pixel_size,
    default="16px",
    show_default=True,
    help="The font size.",
)
@click.option(
    "-w",
    "--width",
    type=click.INT,
    help="The width of the output image. Matches the size of the text by default.",
)
@click.option(
    "-h",
    "--height",
    type=click.INT,
    help="The height of the output image. Matches the size of the text by default.",
)
@click.option(
    "--max-line-size",
    type=click.INT,
    help="The maximum size of a line. Line may be of infinite length by default.",
)
@click.option(
    "--line-height",
    type=click.INT,
    help="The height of a line. Defaults to a value picked by the font.",
)
@click.option(
    "--primary-axis-alignment", type=click.Choice(PrimaryAxisTextAlign), show_default=True
)
@click.option(
    "--secondary-axis-alignment", type=click.Choice(SecondaryAxisTextAlign), show_default=True
)
def main(
    text,
    font,
    size,
    width,
    height,
    max_line_size,
    line_height,
    primary_axis_alignment,
    secondary_axis_alignment,
):
    with open(font, "rb") as font_file:
        font_face = FontFace(font_file)

    size_value, size_type = size
    if size_type == "px":
        font_face_size = font_face.request_pixel_size(height=size_value)
    elif size_type == "pt":
        font_face_size = font_face.request_point_size(height=size_value)

    text_layout = font_face.layout_text(
        text,
        font_face_size,
        break_text=break_text_icu_line,
        max_line_size=max_line_size,
        line_height=line_height,
        primary_axis_alignment=primary_axis_alignment,
        secondary_axis_alignment=secondary_axis_alignment,
    )

    image_size = (
        int(text_layout.bounding_box.size.x) if width is None else width,
        int(text_layout.bounding_box.size.y) if height is None else height,
    )
    image = Image.new(mode="RGB", size=image_size)

    for text_glyph in text_layout.glyphs:
        rendered_glyph = font_face.render_glyph(text_glyph.glyph_index, font_face_size)
        image_glyph = Image.frombytes("L", tuple(rendered_glyph.size), rendered_glyph.data)
        image.paste(
            image_glyph,
            tuple(int(d) for d in text_glyph.bounding_box.position + rendered_glyph.bearing),
        )
    image.show()


if __name__ == "__main__":
    main()
