"""
Manager drzewa katalogów - zarządzanie folderami i drzewem nawigacji.
ETAP: ZAKTUALIZOWANY - Podzielony na moduły.
"""

from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QStyledItemDelegate, QStyle
from src.utils.path_utils import normalize_path


class DropHighlightDelegate(QStyledItemDelegate):
    """Delegate do podświetlania folderów podczas drag&drop."""

    def __init__(self, directory_tree_manager, parent=None):
        super().__init__(parent)
        self.directory_tree_manager = directory_tree_manager

    def paint(self, painter, option, index):
        # Najpierw rysuj element standardowo
        super().paint(painter, option, index)

        # DEBUG: Sprawdź czy paint() w ogóle się wywołuje
        import logging
        logger = logging.getLogger(__name__)
        
        # Sprawdź czy ten folder jest podświetlony podczas drag&drop
        if hasattr(self.directory_tree_manager, '_highlighted_drop_target'):
            source_index = self.directory_tree_manager.get_source_index_from_proxy(index)
            if source_index.isValid():
                folder_path = self.directory_tree_manager.model.filePath(source_index)
                
                # NAPRAWKA: Normalizuj ścieżki przed porównaniem
                highlighted_target = self.directory_tree_manager._highlighted_drop_target
                normalized_folder_path = normalize_path(folder_path)
                normalized_highlighted = normalize_path(highlighted_target)
                
                logger.info(f"DELEGATE DEBUG: folder='{normalized_folder_path}' vs target='{normalized_highlighted}'")
                
                if normalized_folder_path == normalized_highlighted:
                    logger.info(f"DRAG&DROP HIGHLIGHT: ✅ PODŚWIETLAM FOLDER {folder_path}")
                    
                    # Narysuj ramkę podświetlenia - MOCNIEJSZA I BARDZIEJ WIDOCZNA
                    painter.save()
                    pen = QPen(QColor(255, 165, 0), 5)  # Grubsza linia - 5px
                    painter.setPen(pen)
                    painter.setBrush(QColor(255, 165, 0, 100))  # Mocniejsze wypełnienie
                    
                    # Narysuj prostokąt z zaokrąglonymi rogami - większy
                    rect = QRect(option.rect)
                    rect.adjust(0, 0, 0, 0)  # Pełny rozmiar
                    painter.drawRoundedRect(rect, 6, 6)
                    painter.restore()
                    
                    logger.info(f"DELEGATE: ✅ NARYSOWANO PODŚWIETLENIE!")
                else:
                    logger.debug(f"DELEGATE DEBUG: ❌ NIE PASUJE - folder: '{folder_path}', target: '{highlighted_target}'") 