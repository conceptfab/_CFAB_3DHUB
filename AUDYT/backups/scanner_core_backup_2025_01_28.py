"""
Moduł odpowiedzialny za skanowanie folderów.

Ten moduł zawiera funkcje do skanowania katalogów w poszukiwaniu plików
oraz koordynowania procesu skanowania.
"""

import logging
import os
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Set, Tuple

from src import app_config
from src.config import AppConfig
from src.logic.file_pairing import (
    ARCHIVE_EXTENSIONS,
    PREVIEW_EXTENSIONS,
    create_file_pairs,
    identify_unpaired_files,
)
from src.logic.metadata_manager import MetadataManager
from src.logic.scanner_cache import cache
from src.models.file_pair import FilePair
from src.models.special_folder import SpecialFolder
from src.utils.path_utils import normalize_path, path_exists

# Konfiguracja loggera
logger = logging.getLogger(__name__)

# Parametry cache z centralnego pliku konfiguracyjnego
MAX_CACHE_ENTRIES = app_config.SCANNER_MAX_CACHE_ENTRIES
MAX_CACHE_AGE_SECONDS = app_config.SCANNER_MAX_CACHE_AGE_SECONDS

# Foldery ignorowane podczas skanowania
IGNORED_FOLDERS = {
    ".app_metadata",
    "__pycache__",
    ".git",
    ".svn",
    ".hg",
    "node_modules",
    ".alg_meta",
}

# Pre-computed set for O(1) lookup optimization
IGNORED_FOLDERS_SET = frozenset(IGNORED_FOLDERS)


@dataclass
class ScanConfig:
    """Konfiguracja skanowania - zastępuje 8 parametrów funkcji."""

    directory: str
    max_depth: int = -1
    use_cache: bool = True
    pair_strategy: str = "first_match"
    interrupt_check: Optional[Callable[[], bool]] = None
    force_refresh_cache: bool = False
    progress_callback: Optional[Callable[[int, str], None]] = None

    def __post_init__(self):
        """Walidacja i normalizacja konfiguracji."""
        self.directory = normalize_path(self.directory)


class ScanCacheManager:
    """Zarządza operacjami cache podczas skanowania."""

    @staticmethod
    def get_cached_result(
        config: ScanConfig,
    ) -> Optional[Tuple[List[FilePair], List[str], List[str], List[SpecialFolder]]]:
        """Pobiera wynik z cache jeśli dostępny."""
        if config.use_cache and not config.force_refresh_cache:
            cached_result = cache.get_scan_result(
                config.directory, config.pair_strategy
            )
            if cached_result:
                logger.debug(
                    f"CACHE HIT: Zwracam pełny zbuforowany wynik dla {config.directory}"
                )
                if config.progress_callback:
                    config.progress_callback(
                        100, f"Używam cache dla {config.directory}"
                    )
                return cached_result
        return None

    @staticmethod
    def save_result(
        config: ScanConfig,
        result: Tuple[List[FilePair], List[str], List[str], List[SpecialFolder]],
    ):
        """Zapisuje wynik w cache."""
        if config.use_cache:
            cache.set_scan_result(config.directory, config.pair_strategy, result)


class ScanProgressManager:
    """Zarządza raportowaniem postępu skanowania."""

    def __init__(self, config: ScanConfig):
        self.config = config

    def report_progress(self, percent: int, message: str):
        """Raportuje postęp jeśli callback jest dostępny."""
        if self.config.progress_callback:
            self.config.progress_callback(percent, message)

    def create_scaled_progress_callback(
        self, scale_factor: float = 0.5
    ) -> Optional[Callable]:
        """Tworzy callback ze skalowaniem postępu."""
        if not self.config.progress_callback:
            return None

        def scaled_progress(percent, message):
            scaled_percent = int(percent * scale_factor)
            self.config.progress_callback(scaled_percent, message)

        return scaled_progress


class SpecialFoldersManager:
    """Zarządza wykrywaniem i tworzeniem folderów specjalnych."""

    @staticmethod
    def find_special_folders(directory: str) -> List[SpecialFolder]:
        """Znajduje foldery specjalne na dysku."""
        # USUNIĘTA FUNKCJA - Foldery specjalne są teraz pobierane z metadanych.
        logger.debug("find_special_folders: Funkcja zastąpiona przez metadane")
        return []

    @staticmethod
    def handle_virtual_folders(
        directory: str, special_folders: List[SpecialFolder]
    ) -> List[SpecialFolder]:
        """Obsługuje tworzenie wirtualnych folderów na podstawie metadanych."""
        metadata_manager = MetadataManager.get_instance(directory)
        metadata = metadata_manager.io.load_metadata_from_file()

        if metadata and metadata.get("has_special_folders") and not special_folders:
            logger.info(
                f"Metadane dla '{directory}' wskazują na istnienie folderów "
                f"specjalnych, ale nie znaleziono ich na dysku. "
                f"Tworzę folder wirtualny."
            )

            virtual_folder = SpecialFoldersManager._create_virtual_folder(
                directory, metadata
            )
            if virtual_folder:
                special_folders.append(virtual_folder)
                logger.info(
                    f"Utworzono wirtualny folder: {virtual_folder.get_folder_path()}"
                )

        return special_folders

    @staticmethod
    def _create_virtual_folder(
        directory: str, metadata: dict
    ) -> Optional[SpecialFolder]:
        """Tworzy wirtualny folder na podstawie metadanych."""
        # Użyj nazwy z metadanych, jeśli jest dostępna
        special_folders_from_meta = metadata.get("special_folders")
        if special_folders_from_meta:
            virtual_folder_name = special_folders_from_meta[0]
            logger.debug(
                f"Używam nazwy folderu wirtualnego z metadanych: '{virtual_folder_name}'"
            )
        else:
            # Fallback na starą logikę
            logger.warning(
                f"Brak zdefiniowanych nazw folderów specjalnych w metadanych "
                f"dla '{directory}'. Używam domyślnej nazwy z konfiguracji."
            )
            special_folders_config = AppConfig.get_instance().special_folders
            if special_folders_config:
                virtual_folder_name = special_folders_config[0]
            else:
                logger.error("Brak domyślnych folderów specjalnych w konfiguracji!")
                virtual_folder_name = "special_folder"  # Ostateczny fallback

        virtual_folder_path = os.path.join(directory, virtual_folder_name)
        return SpecialFolder(
            folder_name=virtual_folder_name,
            folder_path=virtual_folder_path,
            is_virtual=True,
        )


class ScanOrchestrator:
    """Koordynuje cały proces skanowania."""

    def __init__(self, config: ScanConfig):
        self.config = config
        self.progress_manager = ScanProgressManager(config)
        self.cache_manager = ScanCacheManager()
        self.special_folders_manager = SpecialFoldersManager()

    def execute_scan(
        self,
    ) -> Tuple[List[FilePair], List[str], List[str], List[SpecialFolder]]:
        """Wykonuje pełny proces skanowania."""
        # 1. Sprawdź cache
        cached_result = self.cache_manager.get_cached_result(self.config)
        if cached_result:
            return cached_result

        # 2. Waliduj katalog
        if not self._validate_directory():
            return [], [], [], []

        # 3. Zbierz pliki
        file_map = self._collect_files()

        # 4. Utwórz pary plików
        file_pairs, processed_files = self._create_file_pairs(file_map)

        # 5. Identyfikuj nieparowane pliki
        unpaired_archives, unpaired_previews = self._identify_unpaired_files(
            file_map, file_pairs
        )

        # 6. Znajdź foldery specjalne
        special_folders = self._handle_special_folders()

        # 7. Zapisz w cache i zwróć wynik
        result = (file_pairs, unpaired_archives, unpaired_previews, special_folders)
        self.cache_manager.save_result(self.config, result)

        logger.info(
            f"Skanowanie zakończone dla {self.config.directory}. Znaleziono {len(file_pairs)} par."
        )
        self.progress_manager.report_progress(
            100, f"Skanowanie zakończone: {len(file_pairs)} par"
        )

        return result

    def _validate_directory(self) -> bool:
        """Waliduje katalog do skanowania."""
        if not path_exists(self.config.directory) or not os.path.isdir(
            self.config.directory
        ):
            logger.warning(
                f"Katalog {self.config.directory} nie istnieje lub nie jest katalogiem. "
                f"Zwracam pusty wynik."
            )
            return False
        return True

    def _collect_files(self) -> Dict[str, List[str]]:
        """Zbiera pliki z katalogu."""
        scaled_progress = self.progress_manager.create_scaled_progress_callback(0.5)

        return collect_files_streaming(
            self.config.directory,
            self.config.max_depth,
            self.config.interrupt_check,
            self.config.force_refresh_cache,
            scaled_progress,
        )

    def _create_file_pairs(
        self, file_map: Dict[str, List[str]]
    ) -> Tuple[List[FilePair], Set[str]]:
        """Tworzy pary plików."""
        self.progress_manager.report_progress(55, "Tworzenie par plików...")

        return create_file_pairs(
            file_map,
            base_directory=self.config.directory,
            pair_strategy=self.config.pair_strategy,
        )

    def _identify_unpaired_files(
        self, file_map: Dict[str, List[str]], file_pairs: List[FilePair]
    ) -> Tuple[List[str], List[str]]:
        """Identyfikuje nieparowane pliki."""
        self.progress_manager.report_progress(
            80, "Identyfikacja nieparowanych plików..."
        )

        # Zbierz wszystkie przetworzone pliki z par
        processed_files = set()
        for pair in file_pairs:
            processed_files.add(pair.get_archive_path())
            if pair.get_preview_path():
                processed_files.add(pair.get_preview_path())

        return identify_unpaired_files(file_map, processed_files)

    def _handle_special_folders(self) -> List[SpecialFolder]:
        """Obsługuje foldery specjalne."""
        self.progress_manager.report_progress(95, "Szukanie folderów specjalnych...")

        special_folders = self.special_folders_manager.find_special_folders(
            self.config.directory
        )
        return self.special_folders_manager.handle_virtual_folders(
            self.config.directory, special_folders
        )


def should_ignore_folder(folder_name: str) -> bool:
    """
    Sprawdza czy folder powinien być ignorowany podczas skanowania.
    OPTYMALIZACJA: Używa frozenset dla O(1) lookup zamiast O(n).

    Args:
        folder_name: Nazwa folderu do sprawdzenia

    Returns:
        True jeśli folder powinien być ignorowany
    """
    return folder_name in IGNORED_FOLDERS_SET or folder_name.startswith(".")


class ScanningInterrupted(Exception):
    """Wyjątek rzucany gdy skanowanie zostało przerwane przez użytkownika."""

    pass


def collect_files_streaming(
    directory: str,
    max_depth: int = -1,
    interrupt_check: Optional[Callable[[], bool]] = None,
    force_refresh: bool = False,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> Dict[str, List[str]]:
    """
    Zbiera wszystkie pliki w katalogu z streaming progress.

    Args:
        directory: Ścieżka do katalogu do przeskanowania
        max_depth: Maksymalna głębokość rekursji, -1 oznacza brak limitu
        interrupt_check: Opcjonalna funkcja sprawdzająca czy przerwać skanowanie
        force_refresh: Czy wymusić odświeżenie cache (ignoruje cache)
        progress_callback: Opcjonalna funkcja do raportowania postępu (procent, wiadomość)

    Returns:
        Słownik zmapowanych plików, gdzie kluczem jest nazwa bazowa (bez rozszerzenia),
        a wartością lista pełnych ścieżek do plików.

    Raises:
        ScanningInterrupted: Jeśli skanowanie zostało przerwane
    """
    normalized_dir = normalize_path(directory)

    # Sprawdź cache
    if not force_refresh:
        cached_file_map = cache.get_file_map(normalized_dir)
        if cached_file_map is not None:
            logger.debug(f"CACHE HIT: używam buforowanych plików dla {normalized_dir}")
            if progress_callback:
                progress_callback(100, f"Używam cache dla {normalized_dir}")
            return cached_file_map

    # Jeśli katalog nie istnieje lub nie jest katalogiem, zwróć pusty słownik
    if not path_exists(normalized_dir) or not os.path.isdir(normalized_dir):
        logger.warning(f"Katalog {normalized_dir} nie istnieje lub nie jest katalogiem")
        if progress_callback:
            progress_callback(100, f"Katalog {normalized_dir} nie istnieje")
        return {}

    logger.info(f"Rozpoczęto streaming zbieranie plików z katalogu: {normalized_dir}")
    if progress_callback:
        progress_callback(0, f"Rozpoczynam streaming skanowanie: {normalized_dir}")

    file_map = defaultdict(list)
    total_folders_scanned = 0
    total_files_found = 0
    start_time = time.time()

    # Throttled progress reporting variables
    last_progress_time = time.time()
    PROGRESS_THROTTLE_INTERVAL = 0.1  # Minimum 100ms between progress updates

    # Zestaw odwiedzonych katalogów (do obsługi pętli symbolicznych)
    visited_dirs = set()

    def _walk_directory_streaming(current_dir: str, depth: int = 0):
        nonlocal total_folders_scanned, total_files_found, last_progress_time

        # Pre-compute normalized current directory (cache optimization)
        normalized_current_dir = normalize_path(current_dir)

        # Throttled progress reporting to prevent UI freeze
        current_time = time.time()
        if (
            progress_callback
            and (current_time - last_progress_time) >= PROGRESS_THROTTLE_INTERVAL
        ):
            progress = min(95, total_folders_scanned * 2)  # Aproksymacja progressu
            progress_callback(
                progress,
                f"Skanowanie: {os.path.basename(current_dir)} "
                f"({total_files_found} plików, {total_folders_scanned} folderów)",
            )
            last_progress_time = current_time

        # Sprawdzenie czy należy przerwać skanowanie
        if interrupt_check and interrupt_check():
            logger.warning("Skanowanie przerwane przez użytkownika")
            raise ScanningInterrupted("Skanowanie przerwane przez użytkownika")

        # Sprawdzanie co każde 50 plików dla responsywności
        if total_files_found % 50 == 0 and interrupt_check and interrupt_check():
            logger.warning(
                "Skanowanie przerwane przez użytkownika podczas " "przetwarzania plików"
            )
            raise ScanningInterrupted("Skanowanie przerwane przez użytkownika")

        # Obsługa limitu głębokości
        if max_depth >= 0 and depth > max_depth:
            return

        # Zabezpieczenie przed zapętleniem (symlinki)
        if normalized_current_dir in visited_dirs:
            logger.warning(f"Wykryto pętlę w katalogach: {normalized_current_dir}")
            return
        visited_dirs.add(normalized_current_dir)

        # Skanowanie folderu
        try:
            total_folders_scanned += 1
            entries = list(os.scandir(current_dir))

            # Sprawdzenie przerwania po liście folderów
            if interrupt_check and interrupt_check():
                logger.warning(
                    "Skanowanie przerwane podczas odczytu zawartości folderu"
                )
                raise ScanningInterrupted(
                    "Skanowanie przerwane podczas odczytu zawartości folderu"
                )

            # Najpierw przetwarzamy pliki
            files_processed_in_folder = 0
            for entry in entries:
                if entry.is_file():
                    total_files_found += 1
                    files_processed_in_folder += 1

                    # Sprawdzenie co 100 plików w folderze (batch processing)
                    if (
                        files_processed_in_folder % 100 == 0
                        and interrupt_check
                        and interrupt_check()
                    ):
                        msg = (
                            "Skanowanie przerwane podczas przetwarzania "
                            f"plików w {current_dir}"
                        )
                        logger.warning(msg)
                        raise ScanningInterrupted(msg)

                    name = entry.name
                    base_name, ext = os.path.splitext(name)
                    ext_lower = ext.lower()

                    if (
                        ext_lower in ARCHIVE_EXTENSIONS
                        or ext_lower in PREVIEW_EXTENSIONS
                    ):
                        # Optimized key generation - use pre-computed normalized path
                        map_key = os.path.join(
                            normalized_current_dir, base_name.lower()
                        )
                        full_file_path = os.path.join(normalized_current_dir, name)
                        file_map[map_key].append(full_file_path)

            should_scan_subfolders = files_processed_in_folder > 0

            logger.debug(
                f"Skanowanie: {current_dir} -> {files_processed_in_folder} plików"
            )

            if should_scan_subfolders:
                subfolders_processed = 0
                for entry in entries:
                    if entry.is_dir():
                        # Ignoruj ukryte foldery i foldery systemowe
                        if should_ignore_folder(entry.name):
                            logger.debug(f"Pomijam ignorowany folder: {entry.name}")
                            continue

                        subfolders_processed += 1

                        # Sprawdzenie co 20 podfolderów (batch processing)
                        if (
                            subfolders_processed % 20 == 0
                            and interrupt_check
                            and interrupt_check()
                        ):
                            msg = (
                                "Skanowanie przerwane podczas rekursywnego "
                                f"skanowania w {current_dir}"
                            )
                            logger.warning(msg)
                            raise ScanningInterrupted(msg)

                        # Normalny rekursywny skan (tylko gdy folder ma pliki)
                        _walk_directory_streaming(entry.path, depth + 1)
            else:
                logger.debug(f"Pomijam podfoldery: {current_dir} (brak plików)")

        except PermissionError as e:
            logger.warning(f"Brak uprawnień do katalogu {current_dir}: {e}")
            # Continue scanning other directories
        except FileNotFoundError as e:
            logger.warning(f"Katalog usunięty podczas skanowania {current_dir}: {e}")
            # Directory was deleted during scanning - continue
        except OSError as e:
            logger.error(f"Błąd I/O podczas dostępu do {current_dir}: {e}")
            # Try to continue with other directories
        except MemoryError as e:
            logger.critical(f"Brak pamięci podczas skanowania {current_dir}: {e}")
            # Critical error - should probably stop scanning
            raise
        except ScanningInterrupted:
            # Przepuszczamy wyjątek przerwania wyżej
            raise
        except Exception as e:
            logger.error(f"Nieoczekiwany błąd w katalogu {current_dir}: {e}")
            # Log unexpected errors but continue scanning

    try:
        _walk_directory_streaming(normalized_dir)
    except ScanningInterrupted:
        raise
    finally:
        # Cleanup to prevent memory leaks on repeated scans
        visited_dirs.clear()
        logger.debug(f"Cleaned up visited_dirs cache ({len(visited_dirs)} entries)")

    elapsed_time = time.time() - start_time

    # Business metrics logging
    files_per_second = total_files_found / elapsed_time if elapsed_time > 0 else 0
    folders_per_second = total_folders_scanned / elapsed_time if elapsed_time > 0 else 0

    logger.info(
        f"SCAN_COMPLETED: {normalized_dir} | "
        f"files={total_files_found} | folders={total_folders_scanned} | "
        f"time={elapsed_time:.2f}s | "
        f"rate={files_per_second:.1f}files/s, {folders_per_second:.1f}folders/s"
    )

    # Performance warning for slow scans
    if files_per_second < 100 and total_files_found > 500:
        logger.warning(
            f"SLOW_SCAN_DETECTED: {normalized_dir} | "
            f"rate={files_per_second:.1f}files/s (expected >100files/s for large folders)"
        )

    # Zapisz mapę plików w cache
    if not force_refresh:
        cache.set_file_map(normalized_dir, file_map)

    if progress_callback:
        progress_callback(100, "Zakończono zbieranie plików")

    return file_map


def scan_folder_for_pairs(
    directory: str,
    max_depth: int = -1,
    use_cache: bool = True,
    pair_strategy: str = "first_match",
    interrupt_check: Optional[Callable[[], bool]] = None,
    force_refresh_cache: bool = False,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> Tuple[List[FilePair], List[str], List[str], List[SpecialFolder]]:
    """
    Skanuje folder, tworzy pary i identyfikuje nieparowane pliki.

    REFAKTORYZACJA: Funkcja została uproszczona poprzez wydzielenie ScanOrchestrator.

    Args:
        directory: Ścieżka do katalogu do przeskanowania
        max_depth: Maksymalna głębokość skanowania (-1 = bez limitu)
        use_cache: Czy używać cache
        pair_strategy: Strategia parowania plików
        interrupt_check: Funkcja sprawdzająca przerwanie
        force_refresh_cache: Czy wymusić odświeżenie cache
        progress_callback: Callback postępu

    Returns:
        Tuple zawierający pary, niesparowane archiwa, niesparowane podglądy, foldery specjalne
    """
    config = ScanConfig(
        directory=directory,
        max_depth=max_depth,
        use_cache=use_cache,
        pair_strategy=pair_strategy,
        interrupt_check=interrupt_check,
        force_refresh_cache=force_refresh_cache,
        progress_callback=progress_callback,
    )

    orchestrator = ScanOrchestrator(config)
    return orchestrator.execute_scan()


def get_scan_statistics() -> Dict[str, float]:
    """
    Zwraca statystyki dotyczące bieżącego stanu cache skanowania.

    Returns:
        Słownik zawierający statystyki
    """
    return cache.get_statistics()


def find_special_folders(folder_path: str) -> List[SpecialFolder]:
    """
    USUNIĘTA FUNKCJA - Foldery specjalne są teraz pobierane z metadanych.
    Ta funkcja pozostaje jako zaślepka dla kompatybilności wstecznej.

    Args:
        folder_path: Ścieżka do folderu

    Returns:
        Pusta lista specjalnych folderów
    """
    logger.debug("find_special_folders: Funkcja zastąpiona przez metadane")
    return []
