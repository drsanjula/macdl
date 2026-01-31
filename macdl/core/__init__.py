"""
Core download engine for MacDL
"""

from macdl.core.downloader import Downloader, download_file
from macdl.core.models import DownloadJob, DownloadInfo, Segment, DownloadStatus
from macdl.core.progress import ProgressTracker, ProgressStats, format_size, format_time

__all__ = [
    "Downloader",
    "download_file",
    "DownloadJob",
    "DownloadInfo",
    "Segment",
    "DownloadStatus",
    "ProgressTracker",
    "ProgressStats",
    "format_size",
    "format_time",
]
