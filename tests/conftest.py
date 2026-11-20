import os
from pathlib import Path
os.environ["DATA_DIR"]="/tmp/serial-holdings-pytest"
import pytest
from app.pipeline import run,sample_text
@pytest.fixture
def sample(): return sample_text()
@pytest.fixture
def result(sample): return run(sample)
