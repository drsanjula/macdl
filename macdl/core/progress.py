"""
Progress tracking and callbacks for downloads
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional
import time


@dataclass
class ProgressStats:
    """Statistics for a download in progress"""
    downloaded: int = 0
    total: int = 0
    speed: float = 0.0  # bytes per second
    eta: Optional[float] = None  # seconds remaining
    elapsed: float = 0.0  # seconds elapsed
    
    @property
    def progress(self) -> float:
        """Progress as percentage (0-100)"""
        if self.total == 0:
            return 0.0
        return (self.downloaded / self.total) * 100
    
    @property
    def speed_human(self) -> str:
        """Human-readable speed"""
        return format_size(self.speed) + "/s"
    
    @property
    def eta_human(self) -> str:
        """Human-readable ETA"""
        if self.eta is None:
            return "Unknown"
        return format_time(self.eta)


class ProgressTracker:
    """Tracks download progress and calculates speed/ETA"""
    
    def __init__(
        self,
        total_size: Optional[int] = None,
        callback: Optional[Callable[[ProgressStats], None]] = None,
        update_interval: float = 0.1,  # seconds
    ):
        self.total_size = total_size or 0
        self.callback = callback
        self.update_interval = update_interval
        
        self.downloaded = 0
        self.start_time: Optional[float] = None
        self.last_update_time: float = 0
        self.last_downloaded: int = 0
        
        # For moving average speed calculation
        self.speed_samples: list[float] = []
        self.max_samples = 10
    
    def start(self) -> None:
        """Start tracking"""
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.last_downloaded = 0
    
    def update(self, bytes_downloaded: int) -> None:
        """Update progress with new bytes downloaded"""
        self.downloaded = bytes_downloaded
        
        current_time = time.time()
        elapsed_since_update = current_time - self.last_update_time
        
        # Only update at specified intervals
        if elapsed_since_update >= self.update_interval:
            self._calculate_and_notify(current_time)
    
    def _calculate_and_notify(self, current_time: float) -> None:
        """Calculate stats and notify callback"""
        elapsed_since_update = current_time - self.last_update_time
        bytes_since_update = self.downloaded - self.last_downloaded
        
        # Calculate instantaneous speed
        if elapsed_since_update > 0:
            instant_speed = bytes_since_update / elapsed_since_update
            self.speed_samples.append(instant_speed)
            if len(self.speed_samples) > self.max_samples:
                self.speed_samples.pop(0)
        
        # Moving average speed
        speed = sum(self.speed_samples) / len(self.speed_samples) if self.speed_samples else 0
        
        # Calculate ETA
        eta = None
        if speed > 0 and self.total_size > 0:
            remaining = self.total_size - self.downloaded
            eta = remaining / speed
        
        # Total elapsed time
        elapsed = current_time - (self.start_time or current_time)
        
        stats = ProgressStats(
            downloaded=self.downloaded,
            total=self.total_size,
            speed=speed,
            eta=eta,
            elapsed=elapsed,
        )
        
        if self.callback:
            self.callback(stats)
        
        self.last_update_time = current_time
        self.last_downloaded = self.downloaded
    
    def finish(self) -> ProgressStats:
        """Finish tracking and return final stats"""
        current_time = time.time()
        elapsed = current_time - (self.start_time or current_time)
        
        return ProgressStats(
            downloaded=self.downloaded,
            total=self.total_size,
            speed=self.downloaded / elapsed if elapsed > 0 else 0,
            eta=0,
            elapsed=elapsed,
        )


def format_size(size_bytes: float) -> str:
    """Format bytes to human-readable string"""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def format_time(seconds: float) -> str:
    """Format seconds to human-readable string"""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.0f}m {seconds % 60:.0f}s"
    else:
        hours = seconds / 3600
        minutes = (seconds % 3600) / 60
        return f"{hours:.0f}h {minutes:.0f}m"
