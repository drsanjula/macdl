"""
Data models for download jobs
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional
import uuid


class DownloadStatus(Enum):
    """Status of a download job"""
    PENDING = "pending"
    EXTRACTING = "extracting"  # Extracting real URL from hosting site
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class DownloadInfo:
    """Information extracted from a URL by a plugin"""
    url: str
    filename: str
    size: Optional[int] = None  # File size in bytes, None if unknown
    headers: dict[str, str] = field(default_factory=dict)
    cookies: dict[str, str] = field(default_factory=dict)
    resume_supported: bool = False
    checksum: Optional[str] = None  # MD5 or SHA256 hash if available
    source_url: Optional[str] = None  # Original URL before extraction


@dataclass
class Segment:
    """A segment/chunk of a download"""
    id: int
    start: int  # Start byte position
    end: int  # End byte position
    downloaded: int = 0  # Bytes downloaded so far
    temp_file: Optional[Path] = None
    completed: bool = False
    
    @property
    def size(self) -> int:
        """Total size of this segment"""
        return self.end - self.start + 1
    
    @property
    def progress(self) -> float:
        """Progress as a percentage"""
        if self.size == 0:
            return 100.0
        return (self.downloaded / self.size) * 100


@dataclass
class DownloadJob:
    """A download job with all its metadata"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    url: str = ""
    filename: str = ""
    output_path: Optional[Path] = None
    
    # Size info
    total_size: Optional[int] = None
    downloaded_size: int = 0
    
    # Status
    status: DownloadStatus = DownloadStatus.PENDING
    error_message: Optional[str] = None
    
    # Segments for multi-threaded download
    segments: list[Segment] = field(default_factory=list)
    num_threads: int = 8
    
    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Speed tracking
    speed: float = 0.0  # bytes per second
    
    # Source info
    source_plugin: Optional[str] = None
    original_url: Optional[str] = None  # URL before plugin extraction
    
    @property
    def progress(self) -> float:
        """Overall download progress as percentage"""
        if self.total_size is None or self.total_size == 0:
            return 0.0
        return (self.downloaded_size / self.total_size) * 100
    
    @property
    def eta_seconds(self) -> Optional[float]:
        """Estimated time remaining in seconds"""
        if self.speed <= 0 or self.total_size is None:
            return None
        remaining = self.total_size - self.downloaded_size
        return remaining / self.speed
    
    def update_progress(self) -> None:
        """Update downloaded_size from segments"""
        self.downloaded_size = sum(seg.downloaded for seg in self.segments)
