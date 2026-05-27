import asyncio
import os
import sys
import tempfile

import pytest
import pytest_asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture
def temp_state_file():
    path = tempfile.mktemp(suffix=".json")
    yield path
    try:
        os.remove(path)
        os.remove(f"{path}.tmp")
    except FileNotFoundError:
        pass


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
