"""
ThreadCoordinator - Centralne zarządzanie wątkami dla MainWindow.
Rozwiązuje Problem #3: Nadmierna złożoność zarządzania wątkami.
"""

import logging
from typing import Any, Callable, Dict, Optional

from PyQt6.QtCore import QObject, QThread, QThreadPool, pyqtSignal


class ThreadCoordinator(QObject):
    """
    Centralizuje zarządzanie wątkami i workerami w aplikacji.
    Zapobiega wyciekom pamięci i upraszcza debugging.
    """

    # Sygnały
    operation_started = pyqtSignal(str)  # operation_id
    operation_finished = pyqtSignal(str)  # operation_id
    operation_error = pyqtSignal(str, str)  # operation_id, error_message

    def __init__(self):
        super().__init__()
        self.active_threads: Dict[str, QThread] = {}
        self.active_workers: Dict[str, Any] = {}
        self.thread_pool = QThreadPool.globalInstance()
        logging.debug("ThreadCoordinator zainicjalizowany")

    def execute_scan(self, operation_id: str, worker, callback: Callable):
        """
        Wykonuje operację skanowania w dedykowanym wątku.

        Args:
            operation_id: Unikalny identyfikator operacji
            worker: Worker do uruchomienia
            callback: Funkcja callback po zakończeniu
        """
        if operation_id in self.active_threads:
            logging.warning(f"Operacja {operation_id} już aktywna")
            return False

        # Utwórz nowy wątek
        thread = QThread()
        worker.moveToThread(thread)

        # Zapisz referencje
        self.active_threads[operation_id] = thread
        self.active_workers[operation_id] = worker

        # Podłącz sygnały
        thread.started.connect(worker.run)
        worker.finished.connect(
            lambda *args: self._handle_scan_finished(operation_id, callback, *args)
        )
        worker.finished.connect(thread.quit)
        worker.error.connect(lambda error: self._handle_scan_error(operation_id, error))
        worker.error.connect(thread.quit)
        thread.finished.connect(lambda: self._cleanup_thread(operation_id))

        # Uruchom
        thread.start()
        self.operation_started.emit(operation_id)
        logging.info(f"Uruchomiono operację skanowania: {operation_id}")
        return True

    def execute_bulk_operation(self, operation_id: str, worker, callback: Callable):
        """
        Wykonuje operację masową w thread pool.

        Args:
            operation_id: Unikalny identyfikator operacji
            worker: Worker do uruchomienia
            callback: Funkcja callback po zakończeniu
        """
        if operation_id in self.active_workers:
            logging.warning(f"Operacja {operation_id} już aktywna")
            return False

        # Zapisz workera
        self.active_workers[operation_id] = worker

        # Podłącz sygnały
        worker.signals.finished.connect(
            lambda *args: self._handle_bulk_finished(operation_id, callback, *args)
        )
        worker.signals.error.connect(
            lambda error: self._handle_bulk_error(operation_id, error)
        )

        # Uruchom w thread pool
        self.thread_pool.start(worker)
        self.operation_started.emit(operation_id)
        logging.info(f"Uruchomiono operację masową: {operation_id}")
        return True

    def stop_operation(self, operation_id: str):
        """Zatrzymuje operację o podanym ID."""
        if operation_id in self.active_workers:
            worker = self.active_workers[operation_id]
            if hasattr(worker, "stop"):
                worker.stop()

        if operation_id in self.active_threads:
            thread = self.active_threads[operation_id]
            thread.quit()
            thread.wait(1000)

    def cleanup_all_threads(self):
        """Czyści wszystkie aktywne wątki przy zamykaniu aplikacji."""
        logging.info("Czyszczenie wszystkich wątków...")

        # Zatrzymaj wszystkie operacje
        for operation_id in list(self.active_workers.keys()):
            self.stop_operation(operation_id)

        # Wymuś zakończenie wątków
        for operation_id, thread in list(self.active_threads.items()):
            if thread.isRunning():
                thread.quit()
                if not thread.wait(1000):
                    logging.warning(f"Wymuszam zakończenie wątku: {operation_id}")
                    thread.terminate()
                    thread.wait()

        self.active_threads.clear()
        self.active_workers.clear()
        logging.info("Wszystkie wątki wyczyszczone")

    def _handle_scan_finished(self, operation_id: str, callback: Callable, *args):
        """Obsługuje zakończenie operacji skanowania."""
        if callback:
            callback(*args)
        self.operation_finished.emit(operation_id)

    def _handle_scan_error(self, operation_id: str, error: str):
        """Obsługuje błąd operacji skanowania."""
        self.operation_error.emit(operation_id, error)
        self._cleanup_thread(operation_id)

    def _handle_bulk_finished(self, operation_id: str, callback: Callable, *args):
        """Obsługuje zakończenie operacji masowej."""
        if callback:
            callback(*args)
        self.operation_finished.emit(operation_id)
        if operation_id in self.active_workers:
            del self.active_workers[operation_id]

    def _handle_bulk_error(self, operation_id: str, error: str):
        """Obsługuje błąd operacji masowej."""
        self.operation_error.emit(operation_id, error)
        if operation_id in self.active_workers:
            del self.active_workers[operation_id]

    def _cleanup_thread(self, operation_id: str):
        """Czyści referencje do zakończonego wątku."""
        if operation_id in self.active_threads:
            thread = self.active_threads[operation_id]
            thread.deleteLater()
            del self.active_threads[operation_id]

        if operation_id in self.active_workers:
            worker = self.active_workers[operation_id]
            worker.deleteLater()
            del self.active_workers[operation_id]

    def get_active_operations(self) -> Dict[str, str]:
        """Zwraca listę aktywnych operacji."""
        operations = {}
        for op_id in self.active_workers.keys():
            operations[op_id] = "active"
        return operations
