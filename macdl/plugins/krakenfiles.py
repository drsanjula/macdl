"""
KrakenFiles plugin for extracting download links
"""

import re
import json
from typing import Optional
from bs4 import BeautifulSoup

from macdl.plugins.base import BasePlugin
from macdl.core.models import DownloadInfo
from macdl.exceptions import ExtractionError


class KrakenFilesPlugin(BasePlugin):
    """
    Plugin for downloading files from KrakenFiles.
    
    Needs to fetch the landing page and trigger the download hash.
    """
    
    name = "krakenfiles"
    description = "KrakenFiles file hosting"
    version = "0.1.0"
    
    domains = ["krakenfiles.com"]
    url_patterns = [r"krakenfiles\.com/view/([a-zA-Z0-9]+)/file\.html"]
    
    async def extract(self, url: str) -> list[DownloadInfo]:
        """
        Extract download links from a KrakenFiles URL.
        """
        await self._ensure_session()
        
        try:
            # 1. Get the landing page
            async with self._session.get(url) as resp:
                if resp.status != 200:
                    raise ExtractionError(f"Failed to fetch KrakenFiles page: HTTP {resp.status}")
                
                html = await resp.text()
                soup = BeautifulSoup(html, "html.parser")
                
                # 2. Find the download form and hash
                # Usually there's a button <button type="button" id="download-button" ...>
                # Kraken often uses a POST request to get the real link
                form = soup.find("form", {"id": "dl-form"})
                if not form:
                    # Alternative behavior for some files: direct link
                    direct_link = soup.find("a", {"class": "download-link"})
                    if direct_link:
                        return [DownloadInfo(url=direct_link["href"], filename="binary", source_url=url)]
                    raise ExtractionError("Could not find download form on KrakenFiles")
                
                action_url = form.get("action")
                if action_url and action_url.startswith("//"):
                    action_url = "https:" + action_url
                elif not action_url:
                    action_url = url # Request to same page
                
                # Find the token or hash (CSRF protection)
                token = soup.find("input", {"name": "token"})
                if not token:
                    # Sometimes it's just a button click that triggers AJAX
                    # Let's try to find the data-hash or download-token
                    btn = soup.find("button", {"id": "download-button"})
                    token_val = btn.get("data-token") if btn else None
                else:
                    token_val = token.get("value")
                
                if not token_val:
                    # If we can't find a token, the file might be gone or protected
                    raise ExtractionError("Download token not found. File might be deleted or private.")

                # 3. Request the direct link via POST
                # Kraken expects a POST to the download action to get the direct URL
                post_data = {"token": token_val}
                async with self._session.post(action_url, data=post_data) as post_resp:
                    if post_resp.status != 200:
                        raise ExtractionError(f"KrakenFiles POST failed: HTTP {post_resp.status}")
                    
                    # Kraken returns JSON with the direct link
                    result = await post_resp.json()
                    direct_url = result.get("url")
                    
                    if not direct_url:
                        raise ExtractionError(f"KrakenFiles API did not return a URL: {result}")
                    
                    # Get filename from the page header if possible
                    filename = "kraken_file"
                    name_tag = soup.find("h5", {"class": "file-name"})
                    if name_tag:
                        filename = name_tag.get_text(strip=True)
                    
                    return [
                        DownloadInfo(
                            url=direct_url,
                            filename=filename,
                            source_url=url,
                            resume_supported=True
                        )
                    ]
                    
        except ExtractionError:
            raise
        except Exception as e:
            raise ExtractionError(f"Failed to extract KrakenFiles link: {e}")
