"""
Worker Coordinator dla operacji na plikach.
ETAP 2 refaktoryzacji file_operations_ui.py
"""

import logging
from typing import Callable, Optional

from PyQt6.QtCore import QThreadPool
from PyQt6.QtWidgets import QProgressDialog

from src.ui.delegates.workers.base_workers import UnifiedBaseWorker

logger = logging.getLogger(__name__)


class WorkerCoordinator:
    """
    Koordynator odpowiedzialny za centralne zarządzanie workerami i ich sygnałami.
    
    Eliminuje powtarzający się kod z file_operations_ui.py poprzez
    ujednolicenie obsługi sygnałów i uruchamiania workerów.
    """
    
    def __init__(self):
        """Initialize the coordinator."""
        self.thread_pool = QThreadPool.globalInstance()
    
    def setup_worker_connections(
        self,
        worker: UnifiedBaseWorker,
        progress_dialog: QProgressDialog,
        finished_handler: Callable,
        error_handler: Callable,
        progress_handler: Callable,
        interrupted_handler: Callable
    ) -> None:
        """
        Ujednolicone podłączenie sygnałów workera do handlerów.
        
        Args:
            worker: Worker do podłączenia
            progress_dialog: Dialog postępu
            finished_handler: Handler dla sygnału finished
            error_handler: Handler dla sygnału error
            progress_handler: Handler dla sygnału progress  
            interrupted_handler: Handler dla sygnału interrupted
        """
        logger.debug(f"Podłączanie sygnałów dla workera: {type(worker).__name__}")
        
        # Podłączenie sygnałów workera
        worker.signals.finished.connect(finished_handler)
        worker.signals.error.connect(error_handler)
        worker.signals.progress.connect(progress_handler)
        worker.signals.interrupted.connect(interrupted_handler)
        
        # Podłączenie cancel w progress dialog do interrupt workera
        progress_dialog.canceled.connect(worker.interrupt)
        
        logger.debug("Sygnały workera podłączone pomyślnie")
    
    def start_worker(
        self,
        worker: UnifiedBaseWorker,
        progress_dialog: QProgressDialog
    ) -> None:
        """
        Uruchamia workera w thread pool i wyświetla progress dialog.
        
        Args:
            worker: Worker do uruchomienia
            progress_dialog: Dialog postępu do wyświetlenia
        """
        logger.debug(f"Uruchamiam workera: {type(worker).__name__}")
        
        # Uruchom workera w thread pool
        self.thread_pool.start(worker)
        
        # Pokaż progress dialog
        progress_dialog.show()
        
        logger.debug("Worker uruchomiony pomyślnie")
    
    def setup_and_start_worker(
        self,
        worker: UnifiedBaseWorker,
        progress_dialog: QProgressDialog,
        finished_handler: Callable,
        error_handler: Callable,
        progress_handler: Callable,
        interrupted_handler: Callable
    ) -> None:
        """
        Kompletna konfiguracja i uruchomienie workera - metoda convenience.
        
        Args:
            worker: Worker do skonfigurowania i uruchomienia
            progress_dialog: Dialog postępu
            finished_handler: Handler dla sygnału finished
            error_handler: Handler dla sygnału error
            progress_handler: Handler dla sygnału progress
            interrupted_handler: Handler dla sygnału interrupted
        """
        logger.debug(f"Konfiguracja i uruchomienie workera: {type(worker).__name__}")
        
        # Podłącz sygnały
        self.setup_worker_connections(
            worker, progress_dialog,
            finished_handler, error_handler, 
            progress_handler, interrupted_handler
        )
        
        # Uruchom workera
        self.start_worker(worker, progress_dialog)
        
        logger.debug("Worker skonfigurowany i uruchomiony") 