"""
Detailed Reporting dla operacji na plikach.
ETAP 7 refaktoryzacji file_operations_ui.py
"""

import logging
from typing import Dict, List, Any

from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout, 
    QLabel,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget
)

logger = logging.getLogger(__name__)


class DetailedReporting:
    """
    Manager odpowiedzialny za tworzenie szczegółowych raportów z operacji na plikach.
    
    Separuje logikę raportowania błędów z głównej klasy FileOperationsUI
    i zapewnia ujednolicone formatowanie raportów.
    """
    
    def __init__(self, parent_window: QWidget):
        """
        Initialize the manager.
        
        Args:
            parent_window: Okno nadrzędne dla dialogów raportów
        """
        self.parent_window = parent_window
    
    def show_detailed_move_report(
        self, 
        moved_pairs: List,
        detailed_errors: List[Dict[str, Any]],
        skipped_files: List[Dict[str, Any]],
        summary: Dict[str, int]
    ) -> None:
        """
        Wyświetla szczegółowy raport z operacji przenoszenia plików.
        
        Args:
            moved_pairs: Lista pomyślnie przeniesionych par
            detailed_errors: Lista szczegółowych błędów
            skipped_files: Lista pominiętych plików
            summary: Podsumowanie operacji
        """
        logger.debug("Tworzenie szczegółowego raportu przenoszenia")
        
        dialog = self._create_report_dialog()
        layout = QVBoxLayout(dialog)

        # Dodaj podsumowanie
        summary_label = self._create_summary_section(summary)
        layout.addWidget(summary_label)

        # Dodaj zakładki z szczegółami
        tab_widget = self._create_details_tabs(
            moved_pairs, detailed_errors, skipped_files
        )
        layout.addWidget(tab_widget)

        # Dodaj przyciski
        button_layout = self._create_button_layout(dialog)
        layout.addLayout(button_layout)

        # Pokaż dialog
        dialog.exec()
        logger.debug("Raport wyświetlony")
    
    def _create_report_dialog(self) -> QDialog:
        """
        Tworzy bazowy dialog dla raportu.
        
        Returns:
            Skonfigurowany dialog
        """
        dialog = QDialog(self.parent_window)
        dialog.setWindowTitle("Raport przenoszenia plików")
        dialog.setMinimumSize(800, 600)
        dialog.setModal(True)
        
        logger.debug("Utworzono dialog raportu")
        return dialog
    
    def _create_summary_section(self, summary: Dict[str, int]) -> QLabel:
        """
        Tworzy sekcję podsumowania raportu.
        
        Args:
            summary: Dane podsumowania
            
        Returns:
            Label z podsumowaniem
        """
        summary_text = f"""
<h3>Podsumowanie operacji przenoszenia</h3>
<p><b>Żądano przeniesienia:</b> {summary.get('total_requested', 0)} par plików</p>
<p><b>Pomyślnie przeniesiono:</b> {summary.get('successfully_moved', 0)} par plików</p>
<p><b>Błędy:</b> {summary.get('errors', 0)} plików</p>
<p><b>Pominięto:</b> {summary.get('skipped', 0)} plików</p>
        """

        summary_label = QLabel(summary_text)
        summary_label.setWordWrap(True)
        
        logger.debug("Utworzono sekcję podsumowania")
        return summary_label
    
    def _create_details_tabs(
        self, 
        moved_pairs: List,
        detailed_errors: List[Dict[str, Any]],
        skipped_files: List[Dict[str, Any]]
    ) -> QTabWidget:
        """
        Tworzy zakładki ze szczegółami operacji.
        
        Args:
            moved_pairs: Lista przeniesionych par
            detailed_errors: Lista błędów
            skipped_files: Lista pominiętych plików
            
        Returns:
            Zakładki z danymi
        """
        tab_widget = QTabWidget()

        # Zakładka z błędami
        if detailed_errors:
            errors_widget = self._create_errors_tab(detailed_errors)
            tab_widget.addTab(errors_widget, f"Błędy ({len(detailed_errors)})")

        # Zakładka z pominięciami
        if skipped_files:
            skipped_widget = self._create_skipped_tab(skipped_files)
            tab_widget.addTab(skipped_widget, f"Pominięte ({len(skipped_files)})")

        # Zakładka z sukcesami
        if moved_pairs:
            success_widget = self._create_success_tab(moved_pairs)
            tab_widget.addTab(success_widget, f"Sukces ({len(moved_pairs)})")
        
        logger.debug(f"Utworzono {tab_widget.count()} zakładek szczegółów")
        return tab_widget
    
    def _create_errors_tab(self, detailed_errors: List[Dict[str, Any]]) -> QWidget:
        """
        Tworzy zakładkę z błędami.
        
        Args:
            detailed_errors: Lista błędów
            
        Returns:
            Widget z błędami
        """
        errors_widget = QWidget()
        errors_layout = QVBoxLayout(errors_widget)

        errors_text = QTextEdit()
        errors_text.setReadOnly(True)

        error_content = "<h4>Szczegółowe błędy:</h4>\n"

        # Grupuj błędy według typu
        error_groups = self._group_errors_by_type(detailed_errors)

        for error_type, errors in error_groups.items():
            error_content += f"<h5>{error_type} ({len(errors)} plików):</h5>\n<ul>\n"
            for error in errors:
                error_content += self._format_error_entry(error)
            error_content += "</ul>\n"

        errors_text.setHtml(error_content)
        errors_layout.addWidget(errors_text)
        
        logger.debug(f"Utworzono zakładkę błędów z {len(detailed_errors)} elementami")
        return errors_widget
    
    def _create_skipped_tab(self, skipped_files: List[Dict[str, Any]]) -> QWidget:
        """
        Tworzy zakładkę z pominięciami.
        
        Args:
            skipped_files: Lista pominiętych plików
            
        Returns:
            Widget z pominięciami
        """
        skipped_widget = QWidget()
        skipped_layout = QVBoxLayout(skipped_widget)

        skipped_text = QTextEdit()
        skipped_text.setReadOnly(True)

        skipped_content = "<h4>Pominięte pliki:</h4>\n<ul>\n"
        for skipped in skipped_files:
            skipped_content += self._format_skipped_entry(skipped)
        skipped_content += "</ul>\n"

        skipped_text.setHtml(skipped_content)
        skipped_layout.addWidget(skipped_text)
        
        logger.debug(f"Utworzono zakładkę pominiętych z {len(skipped_files)} elementami")
        return skipped_widget
    
    def _create_success_tab(self, moved_pairs: List) -> QWidget:
        """
        Tworzy zakładkę z sukcesami.
        
        Args:
            moved_pairs: Lista przeniesionych par
            
        Returns:
            Widget z sukcesami
        """
        success_widget = QWidget()
        success_layout = QVBoxLayout(success_widget)

        success_text = QTextEdit()
        success_text.setReadOnly(True)

        success_content = "<h4>Pomyślnie przeniesione pary:</h4>\n<ul>\n"
        for pair in moved_pairs:
            success_content += self._format_success_entry(pair)
        success_content += "</ul>\n"

        success_text.setHtml(success_content)
        success_layout.addWidget(success_text)
        
        logger.debug(f"Utworzono zakładkę sukcesów z {len(moved_pairs)} elementami")
        return success_widget
    
    def _create_button_layout(self, dialog: QDialog) -> QHBoxLayout:
        """
        Tworzy layout z przyciskami.
        
        Args:
            dialog: Dialog do przypisania akcji
            
        Returns:
            Layout z przyciskami
        """
        button_layout = QHBoxLayout()

        close_button = QPushButton("Zamknij")
        close_button.clicked.connect(dialog.accept)
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        
        logger.debug("Utworzono layout przycisków")
        return button_layout
    
    def _group_errors_by_type(
        self, 
        detailed_errors: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Grupuje błędy według typu.
        
        Args:
            detailed_errors: Lista błędów
            
        Returns:
            Słownik błędów pogrupowanych według typu
        """
        error_groups = {}
        for error in detailed_errors:
            error_type = error.get("error_type", "NIEZNANY")
            if error_type not in error_groups:
                error_groups[error_type] = []
            error_groups[error_type].append(error)
        
        logger.debug(f"Pogrupowano błędy na {len(error_groups)} typów")
        return error_groups
    
    def _format_error_entry(self, error: Dict[str, Any]) -> str:
        """
        Formatuje pojedynczy wpis błędu.
        
        Args:
            error: Dane błędu
            
        Returns:
            Sformatowany HTML wpisu
        """
        file_pair = error.get("file_pair", "Nieznany")
        file_type = error.get("file_type", "nieznany")
        file_path = error.get("file_path", "nieznana ścieżka")
        error_msg = error.get("error", "nieznany błąd")

        return (
            f"<li><b>Para:</b> {file_pair} ({file_type})<br/>"
            f"<b>Plik:</b> {file_path}<br/>"
            f"<b>Błąd:</b> {error_msg}</li>\n"
        )
    
    def _format_skipped_entry(self, skipped: Dict[str, Any]) -> str:
        """
        Formatuje pojedynczy wpis pominięcia.
        
        Args:
            skipped: Dane pominięcia
            
        Returns:
            Sformatowany HTML wpisu
        """
        file_pair = skipped.get("file_pair", "Nieznany")
        file_type = skipped.get("file_type", "nieznany")
        file_path = skipped.get("file_path", "nieznana ścieżka")
        target_path = skipped.get("target_path", "nieznana ścieżka docelowa")
        reason = skipped.get("reason", "nieznany powód")

        return (
            f"<li><b>Para:</b> {file_pair} ({file_type})<br/>"
            f"<b>Plik źródłowy:</b> {file_path}<br/>"
            f"<b>Plik docelowy:</b> {target_path}<br/>"
            f"<b>Powód:</b> {reason}</li>\n"
        )
    
    def _format_success_entry(self, pair) -> str:
        """
        Formatuje pojedynczy wpis sukcesu.
        
        Args:
            pair: Para plików
            
        Returns:
            Sformatowany HTML wpisu
        """
        pair_name = (
            pair.get_base_name()
            if hasattr(pair, "get_base_name")
            else "Nieznana para"
        )
        archive_path = getattr(pair, "archive_path", "brak")
        preview_path = getattr(pair, "preview_path", "brak")

        return (
            f"<li><b>Para:</b> {pair_name}<br/>"
            f"<b>Archiwum:</b> {archive_path}<br/>"
            f"<b>Podgląd:</b> {preview_path}</li>\n"
        ) 