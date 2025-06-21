"""
Centralny moduł importów PyQt6 dla całej aplikacji.
Wszystkie moduły UI powinny importować z tego pliku.
"""

# Core Qt
from PyQt6.QtCore import (
    Qt, QObject, QThread, QTimer, QSize, 
    QDir, QUrl, QMimeData, QEvent,
    pyqtSignal, QThreadPool
)

# Widgets
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QFrame,
    QTreeView, QScrollArea, QTabWidget,
    QFileDialog, QMessageBox, QProgressBar,
    QSplitter, QStatusBar, QMenu, QSizePolicy,
    QProgressDialog, QInputDialog, QListWidget
)

# GUI
from PyQt6.QtGui import (
    QAction, QPixmap, QColor, QDrag,
    QDesktopServices
)

# Często używane kombinacje
QT_LAYOUTS = (QVBoxLayout, QHBoxLayout, QGridLayout)
QT_WIDGETS = (QPushButton, QLabel, QFrame)
QT_DIALOGS = (QFileDialog, QMessageBox)