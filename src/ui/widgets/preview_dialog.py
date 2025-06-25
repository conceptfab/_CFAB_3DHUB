from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QScreen
from PyQt6.QtWidgets import QDialog, QLabel, QSizePolicy, QVBoxLayout, QWidget
from typing import Optional


class PreviewDialog(QDialog):
    """
    Okno dialogowe do wyświetlania większego podglądu obrazu.
    """

    def __init__(self, pixmap: QPixmap, parent: Optional[QWidget] = None):
        """
        Inicjalizuje PreviewDialog.

        Args:
            pixmap (QPixmap): Obraz QPixmap do wyświetlenia.
            parent (QWidget, optional): Widget nadrzędny. Defaults to None.
        """
        super().__init__(parent)
        if parent is None:
            import logging
            logging.error(f"TWORZENIE PreviewDialog BEZ PARENTA! To spowoduje puste okno!")

        self.setWindowTitle("Podgląd Obrazu")

        self.original_pixmap = pixmap

        self.image_label = QLabel()
        self.image_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.image_label)
        self.setLayout(layout)

        if self.original_pixmap and not self.original_pixmap.isNull():
            pixmap_w = self.original_pixmap.width()
            pixmap_h = self.original_pixmap.height()

            if pixmap_h == 0 or pixmap_w == 0:
                self.image_label.setText("Błąd: Wymiary obrazu są zerowe.")
                self.resize(300, 200)
                return

            image_aspect_ratio = pixmap_w / pixmap_h

            screen = self.screen() or QScreen.primaryScreen()
            screen_geometry = screen.availableGeometry()
            margin = 50
            max_screen_w = screen_geometry.width() - margin
            max_screen_h = screen_geometry.height() - margin

            dialog_w = float(pixmap_w)
            dialog_h = float(pixmap_h)

            if dialog_w > max_screen_w:
                dialog_w = float(max_screen_w)
                dialog_h = dialog_w / image_aspect_ratio

            if dialog_h > max_screen_h:
                dialog_h = float(max_screen_h)
                dialog_w = dialog_h * image_aspect_ratio

            if dialog_w > max_screen_w:
                dialog_w = float(max_screen_w)
                dialog_h = dialog_w / image_aspect_ratio

            min_dialog_w = 200.0
            min_dialog_h = 150.0

            scale_w_for_min = 1.0
            if dialog_w < min_dialog_w:
                scale_w_for_min = min_dialog_w / dialog_w

            scale_h_for_min = 1.0
            if dialog_h < min_dialog_h:
                scale_h_for_min = min_dialog_h / dialog_h

            upscale_factor = max(scale_w_for_min, scale_h_for_min)

            if upscale_factor > 1.0:
                dialog_w *= upscale_factor
                dialog_h *= upscale_factor

                if dialog_w > max_screen_w:
                    dialog_w = float(max_screen_w)
                    dialog_h = dialog_w / image_aspect_ratio

                if dialog_h > max_screen_h:
                    dialog_h = float(max_screen_h)
                    dialog_w = dialog_h * image_aspect_ratio

                if dialog_w > max_screen_w:
                    dialog_w = float(max_screen_w)
                    dialog_h = dialog_w / image_aspect_ratio

            final_width = int(
                max(
                    dialog_w,
                    (
                        min_dialog_w
                        if image_aspect_ratio >= 1
                        else min_dialog_h * image_aspect_ratio
                    ),
                )
            )
            final_height = int(
                max(
                    dialog_h,
                    (
                        min_dialog_h
                        if image_aspect_ratio < 1
                        else min_dialog_w / image_aspect_ratio
                    ),
                )
            )

            final_width = int(dialog_w)
            final_height = int(dialog_h)

            final_width = max(final_width, int(min_dialog_w))
            final_height = max(final_height, int(min_dialog_h))

            self.resize(int(dialog_w), int(dialog_h))
            self._update_pixmap_scaled()
        else:
            self.image_label.setText("Brak obrazu do wyświetlenia.")
            self.resize(300, 200)

    def _update_pixmap_scaled(self):
        """
        Skaluje oryginalny QPixmap do rozmiaru image_label, zachowując
        proporcje.
        """
        if self.original_pixmap and not self.original_pixmap.isNull():
            scaled_pixmap = self.original_pixmap.scaled(
                self.image_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.image_label.setPixmap(scaled_pixmap)

    def resizeEvent(self, event):
        """
        Obsługuje zdarzenie zmiany rozmiaru okna dialogowego.
        """
        super().resizeEvent(event)
        self._update_pixmap_scaled()
