"""
Konfiguracja dla testów jednostkowych
"""

import os
from unittest.mock import MagicMock, patch

import pytest


# Rejestrujemy patchery automatyczne dla filelock,
# aby uniknąć problemów z PyFakeFS próbującym przechwycić
# operacje systemowe filelock
@pytest.fixture(autouse=True)
def mock_filelock():
    """
    Mock dla klasy FileLock, aby uniknąć faktycznego tworzenia plików blokad.
    """
    mock_lock = MagicMock()
    mock_lock_instance = MagicMock()
    mock_lock.return_value = mock_lock_instance

    # Skonfiguruj __enter__ i __exit__ dla menedżera kontekstu
    mock_lock_instance.__enter__.return_value = None
    mock_lock_instance.__exit__.return_value = None

    # Zapewnij, że acquire i release nie robią nic
    mock_lock_instance.acquire.return_value = None
    mock_lock_instance.release.return_value = None

    with patch("filelock.FileLock", mock_lock):
        yield mock_lock
