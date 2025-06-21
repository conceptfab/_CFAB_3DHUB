"""
Zrefaktoryzowany moduł file_operations - operacje na plikach podzielone na specjalistyczne klasy.
Zgodnie z ETAP 2: correction_KRYTYCZNY_file_operations.md
"""

from .file_opener import FileOpener
from .file_pair_operations import FilePairOperations
from .file_system_operations import FileSystemOperations
from .worker_factory import (
    CentralizedWorkerFactory,
    WorkerFactoryInterface,
    configure_worker_factory,
    get_worker_factory,
)

__all__ = [
    "FileOpener",
    "FilePairOperations",
    "FileSystemOperations",
    "CentralizedWorkerFactory",
    "WorkerFactoryInterface",
    "configure_worker_factory",
    "get_worker_factory",
]
