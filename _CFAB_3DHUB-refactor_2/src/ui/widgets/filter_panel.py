"""
Widget panelu filtrów.
"""

from PyQt6.QtWidgets import QCheckBox, QComboBox, QGroupBox, QHBoxLayout, QLabel

from src import app_config


class FilterPanel(QGroupBox):
    """
    Panel filtrów do filtrowania galerii.
    """

    def __init__(self, parent=None):
        super().__init__("Filtry", parent)
        self._init_ui()
        self.setFixedHeight(60)  # Wysokość panelu

    def _init_ui(self):
        """
        Inicjalizuje interfejs użytkownika panelu filtrów.
        """
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        # Filtr gwiazdek
        self.filter_stars_label = QLabel("Min. gwiazdki:")
        layout.addWidget(self.filter_stars_label)

        self.filter_stars_combo = QComboBox()
        for i in range(6):  # 0 do 5 gwiazdek
            self.filter_stars_combo.addItem(f"{i} gwiazdek", userData=i)
        layout.addWidget(self.filter_stars_combo)

        # Filtr koloru
        self.filter_color_label = QLabel("Tag koloru:")
        layout.addWidget(self.filter_color_label)

        self.filter_color_combo = QComboBox()
        # Użycie PREDEFINED_COLORS_FILTER z app_config
        for name, value in app_config.PREDEFINED_COLORS_FILTER.items():
            self.filter_color_combo.addItem(name, userData=value)
        layout.addWidget(self.filter_color_combo)

        layout.addStretch(1)

    def get_filter_criteria(self) -> dict:
        """
        Zwraca aktualnie ustawione kryteria filtrowania.
        """
        min_stars = self.filter_stars_combo.currentData()
        if min_stars is None:
            min_stars = 0  # Fallback

        req_color = self.filter_color_combo.currentData()
        if req_color is None:
            req_color = "ALL"  # Fallback

        return {
            "min_stars": min_stars,
            "required_color_tag": req_color,
        }

    def connect_signals(self, callback):
        """
        Podłącza sygnały zmiany filtrów do podanego callback.
        """
        self.filter_stars_combo.currentIndexChanged.connect(callback)
        self.filter_color_combo.currentIndexChanged.connect(callback)
