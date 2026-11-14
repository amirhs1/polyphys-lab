"""
Fixtures and markers shared by the lab's tests.

Markers
-------
private_data
    The test reads the maintainer's processed data in the folder that
    ``POLYPHYS_DATA_DIR`` names. It is skipped when the variable is unset
    or empty, and errors in setup when the variable names something that is
    not a directory, so a misconfigured machine is not mistaken for one
    without data.

Fixtures
--------
private_data_dir
    The folder ``POLYPHYS_DATA_DIR`` names, for a ``private_data`` test.
"""
import os
from pathlib import Path

import pytest

DATA_DIR_ENV = "POLYPHYS_DATA_DIR"


def pytest_configure(config: pytest.Config) -> None:
    """Register the ``private_data`` marker."""
    config.addinivalue_line(
        "markers",
        "private_data: reads the maintainer's local data under "
        f"{DATA_DIR_ENV}; skipped when the variable is unset",
    )


def pytest_runtest_setup(item: pytest.Item) -> None:
    """Skip a ``private_data`` test without data, or fail it when
    ``POLYPHYS_DATA_DIR`` is not a directory."""
    if item.get_closest_marker("private_data") is None:
        return
    data_dir = os.environ.get(DATA_DIR_ENV, "")
    if data_dir == "":
        pytest.skip(f"{DATA_DIR_ENV} is not set")
    if not Path(data_dir).is_dir():
        pytest.fail(f"{DATA_DIR_ENV}={data_dir!r} is not a directory",
                    pytrace=False)


@pytest.fixture
def private_data_dir() -> Path:
    """Return the folder that ``POLYPHYS_DATA_DIR`` names.

    Use it only in a test marked ``@pytest.mark.private_data``; the marker
    skips the test before this fixture runs when the variable is unset.
    """
    return Path(os.environ[DATA_DIR_ENV])
