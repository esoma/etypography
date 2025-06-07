from pathlib import Path

import pytest

from . import resources


@pytest.fixture
def resource_dir():
    return Path(resources.__file__).parent
