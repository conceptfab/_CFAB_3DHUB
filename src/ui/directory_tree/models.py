# ... istniejący kod ...
# Tu zostaną przeniesione klasy StatsProxyModel oraz FolderStatsDelegate z pliku directory_tree_manager.py
# ... istniejący kod ... 

from PyQt6.QtCore import QModelIndex, QSortFilterProxyModel, Qt
from PyQt6.QtWidgets import QStyledItemDelegate
from .data_classes import FolderStatistics


class FolderStatsDelegate(QStyledItemDelegate):
    """Delegate do wyświetlania statystyk folderów w drzewie."""

    def __init__(self, directory_tree_manager, parent=None):
        super().__init__(parent)
        self.directory_tree_manager = directory_tree_manager

    def displayText(self, value, locale):
        """Dostosowuje tekst wyświetlany w drzewie folderów."""
        if isinstance(value, str):
            return value
        return super().displayText(value, locale)


class StatsProxyModel(QSortFilterProxyModel):
    """Proxy model dla drzewa folderów z filtrowaniem i cache statystyk."""

    def __init__(self, directory_tree_manager, parent=None):
        super().__init__(parent)
        self.directory_tree_manager = directory_tree_manager
        self._filter_function = None

    def setSourceModel(self, sourceModel):
        """Ustawia model źródłowy."""
        super().setSourceModel(sourceModel)
        if sourceModel:
            sourceModel.directoryLoaded.connect(self.invalidateFilter)

    def set_filter_function(self, filter_func):
        """Ustawia funkcję filtrującą dla folderów."""
        self._filter_function = filter_func
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        """Sprawdza czy wiersz powinien być wyświetlany."""
        if self._filter_function:
            return self._filter_function(source_row, source_parent)
        return super().filterAcceptsRow(source_row, source_parent)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        """Pobiera dane z modelu z dodanymi statystykami."""
        if not index.isValid():
            return super().data(index, role)

        # Standardowe dane
        base_data = super().data(index, role)

        # Dodaj statystyki do wyświetlania
        if role == Qt.ItemDataRole.DisplayRole and index.column() == 0:
            source_index = self.mapToSource(index)
            if source_index.isValid():
                source_model = self.sourceModel()
                if hasattr(source_model, 'filePath'):
                    folder_path = source_model.filePath(source_index)
                    
                    # Pobierz statystyki z cache
                    stats = self.directory_tree_manager.get_cached_folder_statistics(folder_path)
                    if stats:
                        folder_name = str(base_data) if base_data else ""
                        stats_text = f" ({stats.total_pairs} par, {stats.total_size_gb:.1f} GB)"
                        return folder_name + stats_text

        return base_data 