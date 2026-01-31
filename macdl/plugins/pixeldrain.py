"""
Pixeldrain plugin for extracting download links
"""

import re
import json
from typing import Optional
from macdl.plugins.base import BasePlugin
from macdl.core.models import DownloadInfo
from macdl.exceptions import ExtractionError


class PixeldrainPlugin(BasePlugin):
    """
    Plugin for downloading files from Pixeldrain.
    
    API: https://pixeldrain.com/api/file/{id}
    """
    
    name = "pixeldrain"
    description = "Pixeldrain file hosting"
    version = "0.1.0"
    
    domains = ["pixeldrain.com"]
    url_patterns = [r"pixeldrain\.com/u/([a-zA-Z0-9]+)"]
    
    API_BASE = "https://pixeldrain.com/api"
    
    async def extract(self, url: str) -> list[DownloadInfo]:
        """
        Extract download links from a Pixeldrain URL.
        """
        await self._ensure_session()
        
        file_id = self._extract_id(url)
        if not file_id:
            raise ExtractionError(f"Could not extract file ID from URL: {url}")
            
        # Get metadata
        info_url = f"{self.API_BASE}/file/{file_id}/info"
        try:
            async with self._session.get(info_url) as resp:
                if resp.status == 404:
                    raise ExtractionError(f"File not found on Pixeldrain: {file_id}")
                if resp.status != 200:
                    raise ExtractionError(f"Pixeldrain API error: HTTP {resp.status}")
                
                data = await resp.json()
                if not data.get("success"):
                    raise ExtractionError(f"Pixeldrain API error: {data.get('message', 'Unknown error')}")
                
                filename = data.get("name", "pixeldrain_file")
                size = data.get("size")
                
                # Direct download link
                # We use /data endpoint as it's the actual file content
                download_url = f"{self.API_BASE}/file/{file_id}"
                
                return [
                    DownloadInfo(
                        url=download_url,
                        filename=filename,
                        size=size,
                        source_url=url,
                        resume_supported=True
                    )
                ]
                
        except ExtractionError:
            raise
        except Exception as e:
            raise ExtractionError(f"Failed to extract Pixeldrain link: {e}")
            
    def _extract_id(self, url: str) -> Optional[str]:
        """Extract file ID from Pixeldrain URL"""
        # https://pixeldrain.com/u/abc123
        match = re.search(r"pixeldrain\.com/u/([a-zA-Z0-9]+)", url)
        if match:
            return match.group(1)
        return None
