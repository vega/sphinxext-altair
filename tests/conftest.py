import sys

import pytest

pytest_plugins = "sphinx.testing.fixtures"


# Exclude 'roots' dirs for pytest test collector
collect_ignore = ["roots"]

if sys.version_info >= (3, 9):
    from pathlib import Path

    @pytest.fixture(scope="session")
    def rootdir():
        return Path(__file__).parent / "roots"
else:
    from sphinx.testing.path import path

    @pytest.fixture(scope="session")
    def rootdir():
        return path(__file__).parent.abspath() / "roots"
