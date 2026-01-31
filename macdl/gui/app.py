"""
MacDL GUI Application - Main Entry Point
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from macdl.gui.main_window import MainWindow


def run():
    """Run the MacDL GUI application"""
    # Enable High DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    
    # Set application metadata
    app.setApplicationName("MacDL")
    app.setApplicationDisplayName("MacDL")
    app.setOrganizationName("MacDL")
    app.setOrganizationDomain("macdl.local")
    
    # Set default font
    font = QFont("SF Pro Display", 13)
    app.setFont(font)
    
    # Apply dark theme
    app.setStyleSheet(get_dark_stylesheet())
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


def get_dark_stylesheet() -> str:
    """Get dark theme stylesheet"""
    return """
        QMainWindow {
            background-color: #1e1e1e;
        }
        
        QWidget {
            background-color: #1e1e1e;
            color: #ffffff;
            font-family: "SF Pro Display", -apple-system, BlinkMacSystemFont, sans-serif;
        }
        
        QLabel {
            color: #ffffff;
        }
        
        QLineEdit {
            background-color: #2d2d2d;
            border: 1px solid #3d3d3d;
            border-radius: 8px;
            padding: 10px 15px;
            color: #ffffff;
            selection-background-color: #0078d4;
        }
        
        QLineEdit:focus {
            border-color: #0078d4;
        }
        
        QPushButton {
            background-color: #0078d4;
            color: #ffffff;
            border: none;
            border-radius: 8px;
            padding: 10px 20px;
            font-weight: 600;
        }
        
        QPushButton:hover {
            background-color: #1084d8;
        }
        
        QPushButton:pressed {
            background-color: #006cbd;
        }
        
        QPushButton:disabled {
            background-color: #3d3d3d;
            color: #808080;
        }
        
        QPushButton#secondaryButton {
            background-color: #3d3d3d;
        }
        
        QPushButton#secondaryButton:hover {
            background-color: #4d4d4d;
        }
        
        QProgressBar {
            background-color: #2d2d2d;
            border: none;
            border-radius: 4px;
            height: 8px;
            text-align: center;
        }
        
        QProgressBar::chunk {
            background-color: #0078d4;
            border-radius: 4px;
        }
        
        QScrollArea {
            border: none;
            background-color: transparent;
        }
        
        QScrollBar:vertical {
            background-color: #2d2d2d;
            width: 10px;
            border-radius: 5px;
        }
        
        QScrollBar::handle:vertical {
            background-color: #4d4d4d;
            border-radius: 5px;
            min-height: 30px;
        }
        
        QScrollBar::handle:vertical:hover {
            background-color: #5d5d5d;
        }
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        
        QMenuBar {
            background-color: #1e1e1e;
            color: #ffffff;
        }
        
        QMenuBar::item:selected {
            background-color: #3d3d3d;
        }
        
        QMenu {
            background-color: #2d2d2d;
            color: #ffffff;
            border: 1px solid #3d3d3d;
            border-radius: 8px;
            padding: 5px;
        }
        
        QMenu::item {
            padding: 8px 30px;
            border-radius: 4px;
        }
        
        QMenu::item:selected {
            background-color: #0078d4;
        }
        
        QToolTip {
            background-color: #2d2d2d;
            color: #ffffff;
            border: 1px solid #3d3d3d;
            border-radius: 4px;
            padding: 5px;
        }
    """


if __name__ == "__main__":
    run()
