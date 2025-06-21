"""
DialogManager - centralne zarządzanie oknami dialogowymi.
🚀 ETAP 5 REFAKTORYZACJI: Wydzielenie logiki dialogów z main_window.py
"""

import logging
import os

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QMessageBox, QTextEdit, QVBoxLayout

from src.models.file_pair import FilePair
from src.ui.widgets.preview_dialog import PreviewDialog


class DialogManager:
    """
    Manager odpowiedzialny za centralne zarządzanie oknami dialogowymi.
    Standaryzuje wygląd, zachowanie i obsługę wszystkich dialogów.
    """

    def __init__(self, main_window):
        """
        Inicjalizuje DialogManager.

        Args:
            main_window: Referencja do głównego okna aplikacji
        """
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)

    def show_preview_dialog(self, file_pair: FilePair):
        """
        Wyświetla okno dialogowe z podglądem obrazu.

        Args:
            file_pair: Para plików do wyświetlenia podglądu
        """
        preview_path = file_pair.get_preview_path()
        if not preview_path or not os.path.exists(preview_path):
            QMessageBox.warning(
                self.main_window,
                "Brak Podglądu",
                "Plik podglądu dla tego elementu nie istnieje.",
            )
            return

        try:
            pixmap = QPixmap(preview_path)
            if pixmap.isNull():
                raise ValueError("Nie udało się załadować obrazu do QPixmap.")

            dialog = PreviewDialog(pixmap, self.main_window)
            dialog.exec()

        except Exception as e:
            error_message = f"Wystąpił błąd podczas ładowania podglądu: {e}"
            self.logger.error(error_message)
            QMessageBox.critical(self.main_window, "Błąd Podglądu", error_message)

    def show_detailed_move_report(
        self, moved_pairs, detailed_errors, skipped_files, summary
    ):
        """
        Wyświetla szczegółowy raport z operacji przenoszenia plików.

        Args:
            moved_pairs: Lista pomyślnie przeniesionych par
            detailed_errors: Szczegółowe błędy operacji
            skipped_files: Lista pominiętych plików
            summary: Podsumowanie operacji
        """
        # Tworzenie dialogu z raportem
        dialog = QMessageBox(self.main_window)
        dialog.setWindowTitle("Raport Przenoszenia Plików")
        dialog.setIcon(QMessageBox.Icon.Information)

        # Tworzenie szczegółowego tekstu raportu
        report_text = self._create_move_report_text(
            moved_pairs, detailed_errors, skipped_files, summary
        )

        # Ustawienie głównej wiadomości
        main_message = (
            f"Operacja przenoszenia zakończona.\n"
            f"Przeniesiono: {len(moved_pairs)} par plików\n"
            f"Błędy: {len(detailed_errors)}\n"
            f"Pominięto: {len(skipped_files)}"
        )
        dialog.setText(main_message)

        # Dodanie szczegółów jeśli są błędy lub pominięte pliki
        if detailed_errors or skipped_files:
            dialog.setDetailedText(report_text)

        # Wyświetlenie dialogu
        dialog.exec()

    def _create_move_report_text(
        self, moved_pairs, detailed_errors, skipped_files, summary
    ):
        """
        Tworzy szczegółowy tekst raportu z przenoszenia plików.

        Args:
            moved_pairs: Lista pomyślnie przeniesionych par
            detailed_errors: Szczegółowe błędy operacji
            skipped_files: Lista pominiętych plików
            summary: Podsumowanie operacji

        Returns:
            Sformatowany tekst raportu
        """
        report_lines = []

        # Podsumowanie
        if summary:
            report_lines.append("=== PODSUMOWANIE ===")
            for key, value in summary.items():
                report_lines.append(f"{key}: {value}")
            report_lines.append("")

        # Przeniesione pliki
        if moved_pairs:
            report_lines.append("=== POMYŚLNIE PRZENIESIONE ===")
            for pair in moved_pairs[:10]:  # Pokaż tylko pierwsze 10
                report_lines.append(f"✅ {pair.get_base_name()}")
            if len(moved_pairs) > 10:
                report_lines.append(f"... i {len(moved_pairs) - 10} więcej")
            report_lines.append("")

        # Błędy
        if detailed_errors:
            report_lines.append("=== BŁĘDY ===")
            for error in detailed_errors[:20]:  # Pokaż tylko pierwsze 20
                report_lines.append(f"❌ {error}")
            if len(detailed_errors) > 20:
                report_lines.append(f"... i {len(detailed_errors) - 20} więcej")
            report_lines.append("")

        # Pominięte pliki
        if skipped_files:
            report_lines.append("=== POMINIĘTE PLIKI ===")
            for file_path in skipped_files[:20]:  # Pokaż tylko pierwsze 20
                report_lines.append(f"⏭️ {file_path}")
            if len(skipped_files) > 20:
                report_lines.append(f"... i {len(skipped_files) - 20} więcej")

        return "\n".join(report_lines)

    def show_error_message(self, title: str, message: str):
        """
        Pokazuje błąd użytkownikowi w standaryzowany sposób.

        Args:
            title: Tytuł okna błędu
            message: Treść komunikatu błędu
        """
        QMessageBox.critical(self.main_window, title, message)

    def show_warning_message(self, title: str, message: str):
        """
        Pokazuje ostrzeżenie użytkownikowi w standaryzowany sposób.

        Args:
            title: Tytuł okna ostrzeżenia
            message: Treść komunikatu ostrzeżenia
        """
        QMessageBox.warning(self.main_window, title, message)

    def show_info_message(self, title: str, message: str):
        """
        Pokazuje informację użytkownikowi w standaryzowany sposób.

        Args:
            title: Tytuł okna informacji
            message: Treść komunikatu informacyjnego
        """
        QMessageBox.information(self.main_window, title, message)

    def confirm_action(self, title: str, message: str) -> bool:
        """
        Wyświetla dialog potwierdzenia akcji.

        Args:
            title: Tytuł okna potwierdzenia
            message: Treść pytania do użytkownika

        Returns:
            True jeśli użytkownik potwierdził, False w przeciwnym przypadku
        """
        reply = QMessageBox.question(
            self.main_window,
            title,
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes

    def show_progress_info(self, title: str, message: str, auto_close_ms: int = None):
        """
        Wyświetla informację o postępie operacji.

        Args:
            title: Tytuł okna informacji
            message: Treść komunikatu o postępie
            auto_close_ms: Automatyczne zamknięcie po X milisekundach (opcjonalne)
        """
        info_box = QMessageBox(QMessageBox.Icon.Information, title, message)
        info_box.setParent(self.main_window)

        if auto_close_ms:
            # Automatyczne zamknięcie po określonym czasie
            QTimer.singleShot(auto_close_ms, info_box.close)

        info_box.exec()

    def show_custom_dialog(self, title: str, content_widget, modal: bool = True):
        """
        Wyświetla niestandardowy dialog z dowolnym widgetem.

        Args:
            title: Tytuł okna dialogu
            content_widget: Widget do wyświetlenia w dialogu
            modal: Czy dialog ma być modalny

        Returns:
            Utworzony dialog
        """
        from PyQt6.QtWidgets import QDialog

        dialog = QDialog(self.main_window)
        dialog.setWindowTitle(title)
        dialog.setModal(modal)

        layout = QVBoxLayout(dialog)
        layout.addWidget(content_widget)

        return dialog
