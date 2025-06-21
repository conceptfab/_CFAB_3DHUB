from dataclasses import dataclass

@dataclass
class FolderStatistics:
    """Statystyki folderu - rozmiar i liczba par plików."""
    size_gb: float = 0.0
    pairs_count: int = 0
    subfolders_size_gb: float = 0.0
    subfolders_pairs: int = 0
    total_files: int = 0

    @property
    def total_size_gb(self) -> float:
        return self.size_gb + self.subfolders_size_gb

    @property
    def total_pairs(self) -> int:
        return self.pairs_count + self.subfolders_pairs

# ... istniejący kod ...
# Tu zostanie przeniesiona klasa FolderStatistics oraz sygnały z pliku directory_tree_manager.py
# ... istniejący kod ... 