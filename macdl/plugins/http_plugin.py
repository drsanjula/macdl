"""
Generic HTTP/HTTPS plugin for direct download links
"""

from typing import Optional
from urllib.parse import urlparse, unquote
from pathlib import Path

from macdl.plugins.base import BasePlugin
from macdl.core.models import DownloadInfo


class HTTPPlugin(BasePlugin):
    """
    Generic plugin for direct HTTP/HTTPS downloads.
    
    This is the fallback plugin for URLs that don't match
    any specific hosting site. It handles direct links to files.
    """
    
    name = "http"
    description = "Direct HTTP/HTTPS downloads"
    version = "0.1.0"
    
    # This plugin handles all HTTP/HTTPS URLs as a fallback
    domains = []  # Empty - we use custom can_handle logic
    url_patterns = [r"^https?://"]
    
    def can_handle(self, url: str) -> bool:
        """
        This plugin can handle any HTTP/HTTPS URL.
        It should be checked last as a fallback.
        """
        return url.startswith("http://") or url.startswith("https://")
    
    async def extract(self, url: str) -> list[DownloadInfo]:
        """
        Extract download info from a direct HTTP/HTTPS URL.
        
        Makes a HEAD request to get file info.
        """
        await self._ensure_session()
        
        async with self._session.head(url, allow_redirects=True) as response:
            response.raise_for_status()
            
            # Get file size
            content_length = response.headers.get("Content-Length")
            size = int(content_length) if content_length else None
            
            # Check resume support
            accept_ranges = response.headers.get("Accept-Ranges", "").lower()
            resume_supported = accept_ranges == "bytes"
            
            # Get filename
            filename = self._extract_filename(response, url)
            
            # Final URL after redirects
            final_url = str(response.url)
            
            return [DownloadInfo(
                url=final_url,
                filename=filename,
                size=size,
                resume_supported=resume_supported,
                source_url=url,
            )]
    
    def _extract_filename(self, response, url: str) -> str:
        """Extract filename from response headers or URL"""
        # Try Content-Disposition header
        content_disposition = response.headers.get("Content-Disposition", "")
        if "filename=" in content_disposition:
            parts = content_disposition.split("filename=")
            if len(parts) > 1:
                filename = parts[1].strip().strip('"').strip("'")
                # Handle filename* (RFC 5987)
                if not filename and "filename*=" in content_disposition:
                    parts = content_disposition.split("filename*=")
                    if len(parts) > 1:
                        # Format: encoding'language'filename
                        encoded = parts[1].strip().strip('"').strip("'")
                        if "'" in encoded:
                            filename = encoded.split("'")[-1]
                            filename = unquote(filename)
                if filename:
                    return filename
        
        # Try to extract from URL path
        parsed = urlparse(url)
        path = unquote(parsed.path)
        filename = Path(path).name
        
        # Remove query string if accidentally included
        if "?" in filename:
            filename = filename.split("?")[0]
        
        return filename if filename else "download"
