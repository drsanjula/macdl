"""
MacDL GUI - Main Window
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional
import threading

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QScrollArea,
    QFrame, QFileDialog, QMessageBox, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QObject, QTimer
from PySide6.QtGui import QFont, QIcon

from macdl import __version__
from macdl.config import Config
from macdl.core import Downloader, DownloadJob, ProgressStats, format_size
from macdl.plugins import get_registry
from macdl.storage import get_db


class DownloadSignals(QObject):
    """Signals for async download communication"""
    started = Signal(str, str)  # job_id, filename
    progress = Signal(str, float, float, str)  # job_id, progress, speed, eta
    completed = Signal(str)  # job_id
    failed = Signal(str, str)  # job_id, error


class DownloadItemWidget(QFrame):
    """Widget representing a single download in the list"""
    
    def __init__(self, job_id: str, filename: str, parent=None):
        super().__init__(parent)
        self.job_id = job_id
        self.filename = filename
        self.setup_ui()
    
    def setup_ui(self):
        self.setObjectName("downloadItem")
        self.setStyleSheet("""
            QFrame#downloadItem {
                background-color: #2d2d2d;
                border-radius: 12px;
                padding: 15px;
                margin: 5px 0;
            }
            QFrame#downloadItem:hover {
                background-color: #353535;
            }
        """)
        self.setMinimumHeight(80)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        
        # Top row: filename and status
        top_row = QHBoxLayout()
        
        self.filename_label = QLabel(self.filename)
        self.filename_label.setFont(QFont("SF Pro Display", 14, QFont.Weight.Medium))
        self.filename_label.setStyleSheet("color: #ffffff;")
        top_row.addWidget(self.filename_label)
        
        top_row.addStretch()
        
        self.status_label = QLabel("Starting...")
        self.status_label.setStyleSheet("color: #808080;")
        top_row.addWidget(self.status_label)
        
        layout.addLayout(top_row)
        
        # Progress bar
        from PySide6.QtWidgets import QProgressBar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMinimumHeight(6)
        self.progress_bar.setMaximumHeight(6)
        layout.addWidget(self.progress_bar)
        
        # Bottom row: details
        bottom_row = QHBoxLayout()
        
        self.size_label = QLabel("")
        self.size_label.setStyleSheet("color: #808080; font-size: 12px;")
        bottom_row.addWidget(self.size_label)
        
        bottom_row.addStretch()
        
        self.speed_label = QLabel("")
        self.speed_label.setStyleSheet("color: #808080; font-size: 12px;")
        bottom_row.addWidget(self.speed_label)
        
        layout.addLayout(bottom_row)
    
    def update_progress(self, progress: float, speed: float, eta: str):
        """Update the progress display"""
        self.progress_bar.setValue(int(progress))
        self.speed_label.setText(f"{format_size(speed)}/s • ETA: {eta}")
        self.status_label.setText(f"{progress:.1f}%")
        self.status_label.setStyleSheet("color: #0078d4;")
    
    def set_completed(self):
        """Mark as completed"""
        self.progress_bar.setValue(100)
        self.status_label.setText("✓ Completed")
        self.status_label.setStyleSheet("color: #4CAF50;")
        self.speed_label.setText("")
    
    def set_failed(self, error: str):
        """Mark as failed"""
        self.status_label.setText("✗ Failed")
        self.status_label.setStyleSheet("color: #f44336;")
        self.speed_label.setText(error[:50])


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.config = Config.load()
        self.signals = DownloadSignals()
        self.download_widgets: dict[str, DownloadItemWidget] = {}
        
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        self.setWindowTitle(f"MacDL v{__version__}")
        self.setMinimumSize(700, 500)
        self.resize(800, 600)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header
        header = self.create_header()
        layout.addLayout(header)
        
        # URL input area
        input_area = self.create_input_area()
        layout.addLayout(input_area)
        
        # Downloads list
        downloads_area = self.create_downloads_area()
        layout.addWidget(downloads_area, 1)
        
        # Footer
        footer = self.create_footer()
        layout.addLayout(footer)
    
    def create_header(self) -> QHBoxLayout:
        """Create the header with logo and title"""
        header = QHBoxLayout()
        
        # Logo/Title
        title = QLabel("🚀 MacDL")
        title.setFont(QFont("SF Pro Display", 24, QFont.Weight.Bold))
        title.setStyleSheet("color: #ffffff;")
        header.addWidget(title)
        
        header.addStretch()
        
        # Status indicator
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #4CAF50;")
        header.addWidget(self.status_label)
        
        return header
    
    def create_input_area(self) -> QHBoxLayout:
        """Create the URL input area"""
        input_layout = QHBoxLayout()
        
        # URL input
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste URL here (supports GoFile, Bunkr, direct links...)")
        self.url_input.setMinimumHeight(45)
        self.url_input.returnPressed.connect(self.start_download)
        input_layout.addWidget(self.url_input, 1)
        
        # Download button
        self.download_btn = QPushButton("Download")
        self.download_btn.setMinimumHeight(45)
        self.download_btn.setMinimumWidth(120)
        self.download_btn.clicked.connect(self.start_download)
        input_layout.addWidget(self.download_btn)
        
        return input_layout
    
    def create_downloads_area(self) -> QScrollArea:
        """Create the scrollable downloads list"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Container for download items
        self.downloads_container = QWidget()
        self.downloads_layout = QVBoxLayout(self.downloads_container)
        self.downloads_layout.setSpacing(10)
        self.downloads_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Empty state
        self.empty_label = QLabel("No downloads yet\nPaste a URL above to get started!")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: #808080; font-size: 16px;")
        self.downloads_layout.addWidget(self.empty_label)
        
        scroll.setWidget(self.downloads_container)
        return scroll
    
    def create_footer(self) -> QHBoxLayout:
        """Create the footer with actions and info"""
        footer = QHBoxLayout()
        
        # Settings button
        settings_btn = QPushButton("⚙️ Settings")
        settings_btn.setObjectName("secondaryButton")
        settings_btn.setMinimumHeight(35)
        settings_btn.clicked.connect(self.show_settings)
        footer.addWidget(settings_btn)
        
        # Clear history button
        clear_btn = QPushButton("🗑️ Clear")
        clear_btn.setObjectName("secondaryButton")
        clear_btn.setMinimumHeight(35)
        clear_btn.clicked.connect(self.clear_downloads)
        footer.addWidget(clear_btn)
        
        footer.addStretch()
        
        # Download directory
        self.dir_label = QLabel(f"📁 {self.config.download_dir}")
        self.dir_label.setStyleSheet("color: #808080;")
        footer.addWidget(self.dir_label)
        
        return footer
    
    def connect_signals(self):
        """Connect async signals to UI updates"""
        self.signals.started.connect(self.on_download_started)
        self.signals.progress.connect(self.on_download_progress)
        self.signals.completed.connect(self.on_download_completed)
        self.signals.failed.connect(self.on_download_failed)
    
    def start_download(self):
        """Start downloading from URL input"""
        url = self.url_input.text().strip()
        if not url:
            return
        
        # Clear input
        self.url_input.clear()
        
        # Hide empty state
        self.empty_label.hide()
        
        # Start download in background thread
        thread = threading.Thread(target=self._run_download, args=(url,), daemon=True)
        thread.start()
        
        self.status_label.setText("Downloading...")
        self.status_label.setStyleSheet("color: #0078d4;")
    
    def _run_download(self, url: str):
        """Run download in background thread"""
        asyncio.run(self._download_async(url))
    
    async def _download_async(self, url: str):
        """Async download implementation"""
        job_id = None
        
        try:
            # Check for plugin
            registry = get_registry()
            plugin = registry.get_plugin_for_url(url)
            
            download_infos = []
            if plugin and plugin.name != "http":
                async with plugin:
                    download_infos = await plugin.extract(url)
            
            if not download_infos:
                # Direct download
                from macdl.core.models import DownloadInfo
                download_infos = [DownloadInfo(url=url, filename="download")]
            
            for info in download_infos:
                async with Downloader(config=self.config) as dl:
                    # Get file info
                    file_info = await dl.get_file_info(info.url, info.headers if hasattr(info, 'headers') else None)
                    
                    job_id = str(id(file_info))[:8]
                    filename = info.filename or file_info.filename
                    
                    # Signal UI
                    self.signals.started.emit(job_id, filename)
                    
                    # Download with progress
                    def on_progress(job: DownloadJob, stats: ProgressStats):
                        eta = f"{int(stats.eta // 60)}:{int(stats.eta % 60):02d}" if stats.eta else "..."
                        self.signals.progress.emit(job_id, stats.progress, stats.speed, eta)
                    
                    dl.progress_callback = on_progress
                    
                    job = await dl.download(
                        info.url, 
                        filename=filename,
                        headers=info.headers if hasattr(info, 'headers') else None,
                    )
                    
                    if job.status.value == "completed":
                        self.signals.completed.emit(job_id)
                    else:
                        self.signals.failed.emit(job_id, job.error_message or "Unknown error")
                        
        except Exception as e:
            if job_id:
                self.signals.failed.emit(job_id, str(e))
            else:
                # Create error widget
                self.signals.started.emit("error", "Download")
                self.signals.failed.emit("error", str(e))
    
    def on_download_started(self, job_id: str, filename: str):
        """Handle download started"""
        widget = DownloadItemWidget(job_id, filename)
        self.download_widgets[job_id] = widget
        self.downloads_layout.insertWidget(0, widget)
    
    def on_download_progress(self, job_id: str, progress: float, speed: float, eta: str):
        """Handle progress update"""
        if job_id in self.download_widgets:
            self.download_widgets[job_id].update_progress(progress, speed, eta)
    
    def on_download_completed(self, job_id: str):
        """Handle download completed"""
        if job_id in self.download_widgets:
            self.download_widgets[job_id].set_completed()
        
        self.status_label.setText("Ready")
        self.status_label.setStyleSheet("color: #4CAF50;")
    
    def on_download_failed(self, job_id: str, error: str):
        """Handle download failed"""
        if job_id in self.download_widgets:
            self.download_widgets[job_id].set_failed(error)
        
        self.status_label.setText("Ready")
        self.status_label.setStyleSheet("color: #4CAF50;")
    
    def show_settings(self):
        """Show settings dialog"""
        QMessageBox.information(
            self,
            "Settings",
            f"Download Directory: {self.config.download_dir}\n"
            f"Threads: {self.config.threads_per_download}\n"
            f"Timeout: {self.config.timeout}s"
        )
    
    def clear_downloads(self):
        """Clear all download widgets"""
        for widget in self.download_widgets.values():
            widget.deleteLater()
        self.download_widgets.clear()
        self.empty_label.show()
