# etypography
from etypography import character_is_normally_rendered

# pytest
import pytest


@pytest.mark.parametrize(
    "character, result",
    [
        (" ", True),
        ("\n", False),
        ("\t", False),
        ("\r", False),
        ("\u2028", True),
        ("\u2029", True),
        ("a", True),
        ("A", True),
        ("食", True),
    ],
)
def test_character_is_normally_rendered(character, result):
    assert character_is_normally_rendered(character) == result


def test_character_normally_rendered_too_many():
    with pytest.raises(TypeError) as excinfo:
        character_is_normally_rendered("ab")
