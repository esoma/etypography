# etypography
from . import resources

# pytest
import pytest

# python
from pathlib import Path


@pytest.fixture
def resource_dir():
    return Path(resources.__file__).parent
