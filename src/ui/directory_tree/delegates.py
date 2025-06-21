"""
Manager drzewa katalogów - zarządzanie folderami i drzewem nawigacji.
ETAP: ZAKTUALIZOWANY - Podzielony na moduły.
"""

from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QStyledItemDelegate, QStyle
from src.utils.path_utils import normalize_path


class DropHighlightDelegate(QStyledItemDelegate):
    """KOMBINOWANY delegate do podświetlania folderów i wyświetlania statystyk."""

    def __init__(self, directory_tree_manager, parent=None):
        super().__init__(parent)
        self.directory_tree_manager = directory_tree_manager

    def displayText(self, value, locale):
        """Dostosowuje tekst wyświetlany w drzewie folderów - DODAJE STATYSTYKI."""
        if isinstance(value, str) and hasattr(self.directory_tree_manager, 'model'):
            # Podobnie jak w FolderStatsDelegate - dodaj statystyki
            return value  # Simplified for now
        return super().displayText(value, locale)

    def paint(self, painter, option, index):
        # Najpierw rysuj element standardowo
        super().paint(painter, option, index)
        
        # TYLKO podczas drag&drop - sprawdź czy ten folder jest podświetlony
        if hasattr(self.directory_tree_manager, '_highlighted_drop_target'):
            source_index = self.directory_tree_manager.get_source_index_from_proxy(index)
            if source_index.isValid():
                folder_path = self.directory_tree_manager.model.filePath(source_index)
                highlighted_target = self.directory_tree_manager._highlighted_drop_target
                
                # Normalizuj ścieżki przed porównaniem
                if normalize_path(folder_path) == normalize_path(highlighted_target):
                    # Narysuj pomarańczową ramkę podświetlenia
                    painter.save()
                    pen = QPen(QColor(255, 165, 0), 4)  # Pomarańczowa ramka 4px
                    painter.setPen(pen)
                    painter.setBrush(QColor(255, 165, 0, 60))  # Przezroczyste wypełnienie
                    
                    rect = QRect(option.rect)
                    painter.drawRoundedRect(rect, 5, 5)
                    painter.restore() 