"""
GoFile.io plugin for extracting download links

NOTE: GoFile API requires authentication. Guest access is limited.
This plugin attempts to use the API but may fail for protected content.
"""

import hashlib
import time
import re
from typing import Optional

from macdl.plugins.base import BasePlugin
from macdl.core.models import DownloadInfo
from macdl.exceptions import ExtractionError


class GoFilePlugin(BasePlugin):
    """
    Plugin for downloading files from GoFile.io
    
    GoFile provides an API for accessing files. This plugin:
    1. Creates a guest account via POST to /accounts
    2. Fetches content metadata via API
    3. Extracts direct download links
    
    Note: GoFile may require premium for some content.
    """
    
    name = "gofile"
    description = "GoFile.io file hosting"
    version = "0.2.0"
    
    domains = ["gofile.io"]
    url_patterns = [r"gofile\.io/d/([a-zA-Z0-9]+)"]
    
    # GoFile API endpoints
    API_BASE = "https://api.gofile.io"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._token: Optional[str] = None
        self._wt: Optional[str] = None
    
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
            
        # Get website token (wt)
        if not self._wt:
            await self._fetch_website_token()
        
        # Fetch content metadata
        content = await self._get_content(content_id)
        
        # Extract file info
        downloads = []
        
        # Data structure: data['children'] contains the files
        children = content.get("children", {})
        if isinstance(children, dict):
            for file_id, file_info in children.items():
                if file_info.get("type") == "file":
                    downloads.append(self._create_download_info(file_info, url))
        elif isinstance(children, list):
            for file_info in children:
                if file_info.get("type") == "file":
                    downloads.append(self._create_download_info(file_info, url))
        elif content.get("type") == "file":
            # Direct file link (rare via /d/ but possible)
            downloads.append(self._create_download_info(content, url))
        
        if not downloads:
            raise ExtractionError(
                f"No downloadable files found. GoFile may require premium access or the link is invalid."
            )
        
        return downloads
    
    def _extract_content_id(self, url: str) -> Optional[str]:
        """Extract content ID from GoFile URL"""
        # Match patterns like gofile.io/d/abc123
        match = re.search(r"gofile\.io/d/([a-zA-Z0-9]+)", url)
        if match:
            return match.group(1)
        
        return None
    
    async def _fetch_website_token(self) -> None:
        """Fetch the current website token (wt) from GoFile config"""
        try:
            async with self._session.get("https://gofile.io/dist/js/config.js") as resp:
                if resp.status == 200:
                    text = await resp.text()
                    match = re.search(r'appdata\.wt\s*=\s*["\']([^"\']+)["\']', text)
                    if match:
                        self._wt = match.group(1)
            
            if not self._wt:
                # Fallback to current known token if extraction fails
                self._wt = "4fd6sg89d7s6"
        except Exception:
            self._wt = "4fd6sg89d7s6"

    async def _create_account(self) -> None:
        """Create a guest account to get an access token"""
        try:
            # GoFile uses POST for account creation
            async with self._session.post(f"{self.API_BASE}/accounts") as response:
                if response.status != 200:
                    raise ExtractionError(
                        f"Failed to create GoFile account: HTTP {response.status}"
                    )
                
                data = await response.json()
                if data.get("status") == "ok":
                    self._token = data.get("data", {}).get("token")
                else:
                    raise ExtractionError(f"Failed to create GoFile account: {data}")
                    
        except Exception as e:
            if "ExtractionError" in str(type(e)):
                raise
            raise ExtractionError(f"Failed to create GoFile account: {e}")
    
    async def _get_content(self, content_id: str) -> dict:
        """Fetch content metadata from GoFile API"""
        headers = {
            "Authorization": f"Bearer {self._token}",
            "X-Website-Token": self._wt
        }
        
        # Browser uses these parameters
        params = {
            "contentFilter": "",
            "page": "1",
            "pageSize": "1000",
            "sortField": "name",
            "sortDirection": "1"
        }
        
        url = f"{self.API_BASE}/contents/{content_id}"
        
        try:
            async with self._session.get(url, headers=headers, params=params) as response:
                data = await response.json()
                
                if data.get("status") == "ok":
                    return data.get("data", {})
                elif data.get("status") == "error-notPremium":
                    raise ExtractionError(
                        "GoFile reports that premium is required for this content. "
                        "This usually happens when the website token (wt) is invalid or the file is restricted."
                    )
                elif data.get("status") == "error-notFound":
                    raise ExtractionError(
                        f"Content not found: {content_id}. The file may have been deleted."
                    )
                elif data.get("status") == "error-passwordRequired":
                    raise ExtractionError(
                        "This content is password protected. Password support not yet implemented."
                    )
                else:
                    raise ExtractionError(f"GoFile API error: {data.get('status', 'unknown')}")
                    
        except ExtractionError:
            raise
        except Exception as e:
            raise ExtractionError(f"Failed to fetch GoFile content: {e}")
    
    def _create_download_info(self, file_info: dict, source_url: str) -> DownloadInfo:
        """Create DownloadInfo from GoFile file metadata"""
        download_link = file_info.get("link", "")
        
        # GoFile direct links require the token cookie
        return DownloadInfo(
            url=download_link,
            filename=file_info.get("name", "unknown"),
            size=file_info.get("size"),
            source_url=source_url,
            resume_supported=True,
            headers={
                "Cookie": f"accountToken={self._token}",
            },
        )
