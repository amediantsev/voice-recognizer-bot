import os
import sys
from pathlib import Path
from unittest.mock import patch

from pytest import fixture


package_root = Path(__file__).parent.parent.parent.resolve()
sys.path.append(os.path.join(package_root))


@fixture(autouse=True)
def mock_tg_bot():
    with patch("telegram.Bot") as mock_bot:
        yield mock_bot


@fixture(autouse=True)
def mock_env_vars():
    os.environ["AWS_DEFAULT_REGION"] = "eu-east-1"
