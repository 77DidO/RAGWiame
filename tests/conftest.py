"""Configuration Pytest."""
import sys
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Mock mariadb module if not present
try:
    import mariadb
except ImportError:
    mock_mariadb = MagicMock()
    sys.modules["mariadb"] = mock_mariadb
