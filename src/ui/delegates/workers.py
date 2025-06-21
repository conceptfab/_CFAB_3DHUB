"""
Moduł workerów do obsługi zadań w tle - plik przejściowy używający nowej modularnej architektury.
UWAGA: Ten plik jest utrzymywany dla wstecznej kompatybilności.
Nowe moduły są dostępne w ./workers/*.py
"""

import warnings

# Importuj wszystkie klasy z podmodułów dla wstecznej kompatybilności
from src.ui.delegates.workers.base_workers import (
    UnifiedWorkerSignals,
    UnifiedBaseWorker,
    TransactionalWorker,
    WorkerPriority,
)
from src.ui.delegates.workers.folder_workers import (
    CreateFolderWorker, 
    RenameFolderWorker, 
    DeleteFolderWorker,
)
from src.ui.delegates.workers.file_workers import (
    ManuallyPairFilesWorker,
    RenameFilePairWorker,
    DeleteFilePairWorker,
    MoveFilePairWorker,
)
from src.ui.delegates.workers.bulk_workers import (
    BulkDeleteWorker,
    BulkMoveWorker,
)
from src.ui.delegates.workers.processing_workers import (
    ThumbnailGenerationWorker,
    BatchThumbnailWorker,
    DataProcessingWorker,
    SaveMetadataWorker,
)
from src.ui.delegates.workers.scan_workers import (
    ScanFolderWorker,
)
from src.ui.delegates.workers.worker_factory import WorkerFactory

# Wyświetl ostrzeżenie o deprecation
warnings.warn(
    "Moduł src.ui.delegates.workers jest przestarzały. "
    "Używaj bezpośrednio modułów z pakietu src.ui.delegates.workers.*",
    DeprecationWarning,
    stacklevel=2
)
