"""
Core async download engine with segmented downloads
"""

import asyncio
import aiohttp
import aiofiles
from pathlib import Path
from typing import Optional, Callable
import os
import tempfile

from macdl.core.models import DownloadJob, DownloadInfo, Segment, DownloadStatus
from macdl.core.progress import ProgressTracker, ProgressStats, format_size
from macdl.exceptions import (
    DownloadError,
    ResumeNotSupportedError,
    FileSizeError,
    NetworkError,
)
from macdl.config import Config


class Downloader:
    """
    Async download engine with multi-threaded/segmented downloads.
    
    Features:
    - Segmented downloads (split file into chunks)
    - Parallel connections per file
    - Resume support via Range headers
    - Progress callbacks
    """
    
    def __init__(
        self,
        config: Optional[Config] = None,
        progress_callback: Optional[Callable[[DownloadJob, ProgressStats], None]] = None,
    ):
        self.config = config or Config.load()
        self.progress_callback = progress_callback
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        await self._create_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._close_session()
    
    async def _create_session(self) -> None:
        """Create aiohttp session"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers={"User-Agent": self.config.user_agent},
            )
    
    async def _close_session(self) -> None:
        """Close aiohttp session"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def get_file_info(self, url: str, headers: Optional[dict] = None) -> DownloadInfo:
        """
        Get file information from URL using HEAD request.
        
        Returns:
            DownloadInfo with size, filename, and resume support info
        """
        await self._create_session()
        
        request_headers = headers or {}
        
        async with self._session.head(url, allow_redirects=True, headers=request_headers) as response:
            response.raise_for_status()
            
            # Get file size
            content_length = response.headers.get("Content-Length")
            size = int(content_length) if content_length else None
            
            # Check resume support
            accept_ranges = response.headers.get("Accept-Ranges", "").lower()
            resume_supported = accept_ranges == "bytes"
            
            # Get filename from Content-Disposition or URL
            filename = self._extract_filename(response, url)
            
            return DownloadInfo(
                url=str(response.url),  # Final URL after redirects
                filename=filename,
                size=size,
                resume_supported=resume_supported,
                source_url=url,
            )
    
    def _extract_filename(self, response: aiohttp.ClientResponse, url: str) -> str:
        """Extract filename from response headers or URL"""
        # Try Content-Disposition header
        content_disposition = response.headers.get("Content-Disposition", "")
        if "filename=" in content_disposition:
            # Extract filename from header
            parts = content_disposition.split("filename=")
            if len(parts) > 1:
                filename = parts[1].strip().strip('"').strip("'")
                if filename:
                    return filename
        
        # Fall back to URL path
        from urllib.parse import urlparse, unquote
        parsed = urlparse(url)
        path = unquote(parsed.path)
        filename = Path(path).name
        
        return filename if filename else "download"
    
    async def download(
        self,
        url: str,
        output_path: Optional[Path] = None,
        filename: Optional[str] = None,
        num_threads: Optional[int] = None,
        headers: Optional[dict] = None,
    ) -> DownloadJob:
        """
        Download a file with segmented/multi-threaded downloading.
        
        Args:
            url: URL to download
            output_path: Directory or full path for output file
            filename: Override filename (optional)
            num_threads: Number of parallel segments (default from config)
            headers: Additional headers for the request
            
        Returns:
            DownloadJob with download status and info
        """
        await self._create_session()
        
        num_threads = num_threads or self.config.threads_per_download
        
        # Get file info
        info = await self.get_file_info(url, headers)
        
        # Determine output path
        final_filename = filename or info.filename
        if output_path is None:
            output_path = Path(self.config.download_dir) / final_filename
        elif output_path.is_dir():
            output_path = output_path / final_filename
        
        # Create download job
        job = DownloadJob(
            url=info.url,
            filename=final_filename,
            output_path=output_path,
            total_size=info.size,
            num_threads=num_threads,
        )
        
        try:
            # Decide download strategy
            if info.size and info.resume_supported and info.size > self.config.chunk_size:
                # Use segmented download for large files with resume support
                await self._download_segmented(job, info, headers)
            else:
                # Use simple streaming download
                await self._download_simple(job, info, headers)
            
            job.status = DownloadStatus.COMPLETED
            
        except Exception as e:
            job.status = DownloadStatus.FAILED
            job.error_message = str(e)
            raise
        
        return job
    
    async def _download_simple(
        self,
        job: DownloadJob,
        info: DownloadInfo,
        headers: Optional[dict] = None,
    ) -> None:
        """Simple streaming download without segmentation"""
        job.status = DownloadStatus.DOWNLOADING
        
        # Progress tracker
        tracker = ProgressTracker(
            total_size=info.size,
            callback=lambda stats: self._on_progress(job, stats),
        )
        tracker.start()
        
        request_headers = headers or {}
        
        async with self._session.get(info.url, headers=request_headers) as response:
            response.raise_for_status()
            
            # Ensure parent directory exists
            job.output_path.parent.mkdir(parents=True, exist_ok=True)
            
            async with aiofiles.open(job.output_path, "wb") as f:
                async for chunk in response.content.iter_chunked(self.config.chunk_size):
                    await f.write(chunk)
                    job.downloaded_size += len(chunk)
                    tracker.update(job.downloaded_size)
        
        tracker.finish()
    
    async def _download_segmented(
        self,
        job: DownloadJob,
        info: DownloadInfo,
        headers: Optional[dict] = None,
    ) -> None:
        """Download using multiple parallel segments"""
        job.status = DownloadStatus.DOWNLOADING
        
        if info.size is None:
            raise FileSizeError("Cannot segment download: file size unknown")
        
        # Create segments
        job.segments = self._create_segments(info.size, job.num_threads)
        
        # Create temp directory for segments
        temp_dir = Path(tempfile.mkdtemp(prefix="macdl_"))
        
        try:
            # Progress tracker
            tracker = ProgressTracker(
                total_size=info.size,
                callback=lambda stats: self._on_progress(job, stats),
            )
            tracker.start()
            
            # Download all segments in parallel
            tasks = [
                self._download_segment(
                    job, segment, info.url, temp_dir, headers, tracker
                )
                for segment in job.segments
            ]
            
            await asyncio.gather(*tasks)
            
            # Merge segments into final file
            await self._merge_segments(job, temp_dir)
            
            tracker.finish()
            
        finally:
            # Clean up temp files
            for segment in job.segments:
                if segment.temp_file and segment.temp_file.exists():
                    segment.temp_file.unlink()
            if temp_dir.exists():
                temp_dir.rmdir()
    
    def _create_segments(self, total_size: int, num_segments: int) -> list[Segment]:
        """Create download segments"""
        segment_size = total_size // num_segments
        segments = []
        
        for i in range(num_segments):
            start = i * segment_size
            # Last segment gets the remainder
            end = (total_size - 1) if i == num_segments - 1 else (start + segment_size - 1)
            
            segments.append(Segment(
                id=i,
                start=start,
                end=end,
            ))
        
        return segments
    
    async def _download_segment(
        self,
        job: DownloadJob,
        segment: Segment,
        url: str,
        temp_dir: Path,
        headers: Optional[dict],
        tracker: ProgressTracker,
    ) -> None:
        """Download a single segment"""
        segment.temp_file = temp_dir / f"segment_{segment.id}.tmp"
        
        request_headers = dict(headers) if headers else {}
        request_headers["Range"] = f"bytes={segment.start}-{segment.end}"
        
        async with self._session.get(url, headers=request_headers) as response:
            if response.status not in (200, 206):
                raise DownloadError(f"Segment download failed: HTTP {response.status}")
            
            async with aiofiles.open(segment.temp_file, "wb") as f:
                async for chunk in response.content.iter_chunked(self.config.chunk_size):
                    await f.write(chunk)
                    segment.downloaded += len(chunk)
                    job.update_progress()
                    tracker.update(job.downloaded_size)
        
        segment.completed = True
    
    async def _merge_segments(self, job: DownloadJob, temp_dir: Path) -> None:
        """Merge all segments into the final file"""
        # Ensure parent directory exists
        job.output_path.parent.mkdir(parents=True, exist_ok=True)
        
        async with aiofiles.open(job.output_path, "wb") as output_file:
            for segment in sorted(job.segments, key=lambda s: s.id):
                if segment.temp_file and segment.temp_file.exists():
                    async with aiofiles.open(segment.temp_file, "rb") as seg_file:
                        while chunk := await seg_file.read(self.config.chunk_size):
                            await output_file.write(chunk)
    
    def _on_progress(self, job: DownloadJob, stats: ProgressStats) -> None:
        """Handle progress update"""
        job.speed = stats.speed
        if self.progress_callback:
            self.progress_callback(job, stats)


async def download_file(
    url: str,
    output: Optional[str] = None,
    threads: int = 8,
    progress_callback: Optional[Callable[[DownloadJob, ProgressStats], None]] = None,
) -> DownloadJob:
    """
    Convenience function to download a file.
    
    Args:
        url: URL to download
        output: Output path or directory
        threads: Number of parallel segments
        progress_callback: Optional callback for progress updates
        
    Returns:
        DownloadJob with result
    """
    config = Config.load()
    config.threads_per_download = threads
    
    output_path = Path(output) if output else None
    
    async with Downloader(config=config, progress_callback=progress_callback) as dl:
        return await dl.download(url, output_path=output_path)
