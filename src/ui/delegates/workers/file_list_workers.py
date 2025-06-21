"""
Workery do operacji na listach plików (np. usuwanie).
"""

import logging
import os

from src.ui.delegates.workers.base_workers import UnifiedBaseWorker

logger = logging.getLogger(__name__)


class BulkDeleteFilesWorker(UnifiedBaseWorker):
    """
    Worker do masowego usuwania listy pojedynczych plików z dysku.
    """

    def __init__(self, files_to_delete: list[str], *args, **kwargs):
        """
        Inicjalizuje workera.

        Args:
            files_to_delete: Lista absolutnych ścieżek do plików do usunięcia.
        """
        super().__init__(*args, **kwargs)
        self.files_to_delete = files_to_delete
        self.total_files = len(self.files_to_delete)

    def _run_implementation(self):
        """
        Główna logika workera - usuwanie plików.
        """
        deleted_files = []
        errors = []

        if not self.files_to_delete:
            self.emit_progress(100, "Brak plików do usunięcia.")
            self.emit_finished({"deleted_files": [], "errors": []})
            return

        for i, file_path in enumerate(self.files_to_delete):
            if self.check_interruption():
                logger.warning("Przerwano usuwanie plików.")
                break

            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    deleted_files.append(file_path)
                    logger.info(f"Usunięto plik: {file_path}")
                else:
                    logger.warning(f"Plik nie istnieje, pomijam: {file_path}")
            except Exception as e:
                error_msg = f"Błąd podczas usuwania pliku {file_path}: {e}"
                logger.error(error_msg, exc_info=True)
                errors.append({"path": file_path, "error": str(e)})

            progress = int(((i + 1) / self.total_files) * 100)
            message = f"Usuwanie pliku {i + 1}/{self.total_files}..."
            self.emit_progress(progress, message)

        result = {"deleted_files": deleted_files, "errors": errors}
        self.emit_progress(100, "Zakończono usuwanie.")
        self.emit_finished(result)
