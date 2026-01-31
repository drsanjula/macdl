"""
GoFile.io plugin for extracting download links
"""

import hashlib
import time
from typing import Optional

from macdl.plugins.base import BasePlugin
from macdl.core.models import DownloadInfo
from macdl.exceptions import ExtractionError


class GoFilePlugin(BasePlugin):
    """
    Plugin for downloading files from GoFile.io
    
    GoFile provides an API for accessing files. This plugin:
    1. Creates a guest account (or uses existing token)
    2. Fetches content metadata via API
    3. Extracts direct download links
    """
    
    name = "gofile"
    description = "GoFile.io file hosting"
    version = "0.1.0"
    
    domains = ["gofile.io"]
    url_patterns = [r"gofile\.io/d/([a-zA-Z0-9]+)"]
    
    # GoFile API endpoints
    API_BASE = "https://api.gofile.io"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._token: Optional[str] = None
        self._website_token: Optional[str] = None
    
    async def extract(self, url: str) -> list[DownloadInfo]:
        """
        Extract download links from a GoFile URL.
        
        Args:
            url: GoFile URL like https://gofile.io/d/abc123
            
        Returns:
            List of DownloadInfo for all files in the folder
        """
        await self._ensure_session()
        
        # Extract content ID from URL
        content_id = self._extract_content_id(url)
        if not content_id:
            raise ExtractionError(f"Could not extract content ID from URL: {url}")
        
        # Get or create account token
        if not self._token:
            await self._create_account()
        
        # Get website token for API auth
        if not self._website_token:
            await self._get_website_token()
        
        # Fetch content metadata
        content = await self._get_content(content_id)
        
        # Extract file info
        downloads = []
        
        if content.get("type") == "folder":
            # Folder with multiple files
            children = content.get("children", {})
            for file_id, file_info in children.items():
                if file_info.get("type") == "file":
                    downloads.append(self._create_download_info(file_info, url))
        else:
            # Single file
            downloads.append(self._create_download_info(content, url))
        
        return downloads
    
    def _extract_content_id(self, url: str) -> Optional[str]:
        """Extract content ID from GoFile URL"""
        import re
        
        # Match patterns like gofile.io/d/abc123
        match = re.search(r"gofile\.io/d/([a-zA-Z0-9]+)", url)
        if match:
            return match.group(1)
        
        return None
    
    async def _create_account(self) -> None:
        """Create a guest account to get an access token"""
        try:
            data = await self._fetch_json(f"{self.API_BASE}/accounts")
            if data.get("status") == "ok":
                self._token = data.get("data", {}).get("token")
            else:
                raise ExtractionError(f"Failed to create GoFile account: {data}")
        except Exception as e:
            raise ExtractionError(f"Failed to create GoFile account: {e}")
    
    async def _get_website_token(self) -> None:
        """Get website token from GoFile JS"""
        # The website token is typically embedded in the page
        # For now, we'll use a static approach that works for most cases
        try:
            # Try to fetch from the website
            text = await self._fetch("https://gofile.io/dist/js/alljs.js")
            
            # Look for websiteToken in the JS
            import re
            match = re.search(r'wt:\s*["\']([^"\']+)["\']', text)
            if match:
                self._website_token = match.group(1)
            else:
                # Fallback: generate a hash-based token
                self._website_token = hashlib.sha256(
                    str(time.time()).encode()
                ).hexdigest()[:32]
        except Exception:
            # Fallback token generation
            self._website_token = hashlib.sha256(
                str(time.time()).encode()
            ).hexdigest()[:32]
    
    async def _get_content(self, content_id: str) -> dict:
        """Fetch content metadata from GoFile API"""
        headers = {
            "Authorization": f"Bearer {self._token}",
        }
        
        params = {
            "wt": self._website_token,
        }
        
        url = f"{self.API_BASE}/contents/{content_id}"
        
        try:
            async with self._session.get(url, headers=headers, params=params) as response:
                response.raise_for_status()
                data = await response.json()
                
                if data.get("status") != "ok":
                    raise ExtractionError(f"GoFile API error: {data}")
                
                return data.get("data", {})
        except Exception as e:
            raise ExtractionError(f"Failed to fetch GoFile content: {e}")
    
    def _create_download_info(self, file_info: dict, source_url: str) -> DownloadInfo:
        """Create DownloadInfo from GoFile file metadata"""
        return DownloadInfo(
            url=file_info.get("link", ""),
            filename=file_info.get("name", "unknown"),
            size=file_info.get("size"),
            source_url=source_url,
            resume_supported=True,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Cookie": f"accountToken={self._token}",
            },
        )
