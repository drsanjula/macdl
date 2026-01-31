"""
MediaFire plugin for extracting download links
"""

import re
from typing import Optional
from bs4 import BeautifulSoup

from macdl.plugins.base import BasePlugin
from macdl.core.models import DownloadInfo
from macdl.exceptions import ExtractionError


class MediaFirePlugin(BasePlugin):
    """
    Plugin for downloading files from MediaFire.
    
    Parses the landing page to find the direct download button.
    """
    
    name = "mediafire"
    description = "MediaFire file hosting"
    version = "0.1.0"
    
    domains = ["mediafire.com"]
    url_patterns = [r"mediafire\.com/file/([a-zA-Z0-9]+)/?"]
    
    async def extract(self, url: str) -> list[DownloadInfo]:
        """
        Extract download links from a MediaFire URL.
        """
        await self._ensure_session()
        
        try:
            async with self._session.get(url) as resp:
                if resp.status != 200:
                    raise ExtractionError(f"Failed to fetch MediaFire page: HTTP {resp.status}")
                
                html = await resp.text()
                soup = BeautifulSoup(html, "html.parser")
                
                # Find download button (usually an 'a' tag with class 'input' and id 'downloadButton')
                # Or look for any 'a' tag that has 'href' containing 'download'
                download_btn = soup.find("a", {"id": "downloadButton"})
                
                if not download_btn:
                    # Fallback: find by Aria-label or searching through all links
                    download_btn = soup.find("a", string=re.compile(r"Download", re.I))
                
                if not download_btn or not download_btn.get("href"):
                    raise ExtractionError("Could not find download button on MediaFire page")
                
                download_url = download_btn["href"]
                
                # Extract filename from the page if possible
                filename_header = soup.find("div", {"class": "filename"})
                if filename_header:
                    filename = filename_header.get_text(strip=True)
                else:
                    # Extract from URL or use a default
                    filename = url.split("/")[-2] if url.endswith("/") else url.split("/")[-1]
                
                return [
                    DownloadInfo(
                        url=download_url,
                        filename=filename,
                        source_url=url,
                        resume_supported=True
                    )
                ]
                
        except ExtractionError:
            raise
        except Exception as e:
            raise ExtractionError(f"Failed to extract MediaFire link: {e}")
