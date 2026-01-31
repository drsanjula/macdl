"""
Qiwi.gg plugin for extracting download links
"""

import re
from typing import Optional
from bs4 import BeautifulSoup

from macdl.plugins.base import BasePlugin
from macdl.core.models import DownloadInfo
from macdl.exceptions import ExtractionError


class QiwiPlugin(BasePlugin):
    """
    Plugin for downloading files from Qiwi.gg
    """
    
    name = "qiwi"
    description = "Qiwi.gg file hosting"
    version = "0.1.0"
    
    domains = ["qiwi.gg"]
    url_patterns = [r"qiwi\.gg/file/([a-zA-Z0-9\-]+)"]
    
    async def extract(self, url: str) -> list[DownloadInfo]:
        """
        Extract download links from a Qiwi URL.
        """
        await self._ensure_session()
        
        try:
            async with self._session.get(url) as resp:
                if resp.status != 200:
                    raise ExtractionError(f"Failed to fetch Qiwi page: HTTP {resp.status}")
                
                html = await resp.text()
                soup = BeautifulSoup(html, "html.parser")
                
                # Qiwi often has a the link in a button with class "btn-download" or a link
                download_btn = soup.find("a", {"class": "btn-download"})
                if not download_btn:
                    # Fallback
                    download_btn = soup.find("a", href=re.compile(r"/u/"))
                
                if not download_btn or not download_btn.get("href"):
                    # Check for "Wait for download" logic
                    # Sometimes Qiwi just has a direct button
                    raise ExtractionError("Qiwi download link not found")
                
                download_url = download_btn["href"]
                if download_url.startswith("/"):
                    download_url = f"https://qiwi.gg{download_url}"
                
                # Extract filename
                filename = "qiwi_file"
                name_tag = soup.find("h1") or soup.find("h3")
                if name_tag:
                    filename = name_tag.get_text(strip=True)
                
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
            raise ExtractionError(f"Failed to extract Qiwi link: {e}")
