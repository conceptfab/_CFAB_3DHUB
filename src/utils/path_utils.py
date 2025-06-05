"""Narzędzia pomocnicze związane ze ścieżkami."""

import os


def normalize_path(path: str) -> str:
    """
    Normalizuje ścieżkę, zamieniając separatory na uniwersalny '/'.
    Jest to kluczowe dla spójności między różnymi częściami aplikacji.
    """
    if not path:
        return ""
    # Używamy os.path.normpath, aby najpierw rozwiązać '..' itp., a potem
    # zamieniamy na forward slashes dla spójności.
    normalized = os.path.normpath(path).replace("\\", "/")
    return normalized
