"""
Pakiet workerów dla operacji asynchronicznych w aplikacji.

Ten pakiet zawiera wszystkie workery używane w aplikacji do wykonywania
zadań w tle, takich jak operacje na plikach, folderach, generowanie miniatur itp.
"""

# Base workery
from .base_workers import (
    UnifiedWorkerSignals,
    UnifiedBaseWorker,
    TransactionalWorker,
    WorkerPriority,
)

# Folder workery
from .folder_workers import (
    CreateFolderWorker,
    RenameFolderWorker, 
    DeleteFolderWorker,
)

# File workery
from .file_workers import (
    ManuallyPairFilesWorker,
    RenameFilePairWorker,
    DeleteFilePairWorker,
    MoveFilePairWorker,
)

# Bulk workery
from .bulk_workers import (
    BulkDeleteWorker,
    BulkMoveWorker,
    BulkMoveFilesWorker,
)

# Processing workery
from .processing_workers import (
    ThumbnailGenerationWorker,
    BatchThumbnailWorker,
    DataProcessingWorker,
    SaveMetadataWorker,
)

# Scan workery
from .scan_workers import (
    ScanFolderWorker,
)

# Factory
from .worker_factory import WorkerFactory

# Dla wstecznej kompatybilności - eksportuj wszystkie klasy do głównej przestrzeni nazw
__all__ = [
    # Base workery
    'UnifiedWorkerSignals', 'UnifiedBaseWorker', 'TransactionalWorker', 'WorkerPriority',
    
    # Folder workery
    'CreateFolderWorker', 'RenameFolderWorker', 'DeleteFolderWorker',
    
    # File workery
    'ManuallyPairFilesWorker', 'RenameFilePairWorker', 'DeleteFilePairWorker', 'MoveFilePairWorker',
    
    # Bulk workery
    'BulkDeleteWorker', 'BulkMoveWorker', 'BulkMoveFilesWorker',
    
    # Processing workery
    'ThumbnailGenerationWorker', 'BatchThumbnailWorker', 'DataProcessingWorker', 'SaveMetadataWorker',
    
    # Scan workery
    'ScanFolderWorker',
    
    # Factory
    'WorkerFactory',
] 