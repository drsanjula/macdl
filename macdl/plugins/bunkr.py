"""
Bunkr plugin for extracting download links

Bunkr.su is a file hosting site that uses heavy JavaScript.
This plugin uses BeautifulSoup for HTML parsing.
"""

import re
from typing import Optional
from urllib.parse import urljoin

from macdl.plugins.base import BasePlugin
from macdl.core.models import DownloadInfo
from macdl.exceptions import ExtractionError


class BunkrPlugin(BasePlugin):
    """
    Plugin for downloading files from Bunkr
    
    Bunkr can host files at various domains:
    - bunkr.su, bunkr.si, bunkr.is, etc.
    
    This plugin parses the HTML to find download links.
    """
    
    name = "bunkr"
    description = "Bunkr.su file hosting"
    version = "0.1.0"
    
    domains = [
        "bunkr.su",
        "bunkr.si", 
        "bunkr.is",
        "bunkrr.su",
        "bunkr.la",
        "bunkr.ru",
        "bunkr.ac",
        "bunkr.ws",
    ]
    
    # CDN domains where actual files are hosted
    CDN_DOMAINS = [
        "cdn.bunkr.ru",
        "media-files.bunkr.ru",
        "cdn-files.bunkr.is",
        "i.bunkr.ru",
        "burger.bunkr.ru",
        "pizza.bunkr.ru",
        "cdn.bunkr.su",
    ]
    
    url_patterns = [
        r"bunkr\.[a-z]+/a/([a-zA-Z0-9]+)",  # Album
        r"bunkr\.[a-z]+/v/([a-zA-Z0-9]+)",  # Video
        r"bunkr\.[a-z]+/i/([a-zA-Z0-9]+)",  # Image
        r"bunkr\.[a-z]+/f/([a-zA-Z0-9]+)",  # File
    ]
    
    async def extract(self, url: str) -> list[DownloadInfo]:
        """
        Extract download links from a Bunkr URL.
        
        Handles:
        - Album pages (/a/) with multiple files
        - Individual file pages (/v/, /i/, /f/)
        """
        await self._ensure_session()
        
        # Determine URL type
        if "/a/" in url:
            return await self._extract_album(url)
        else:
            info = await self._extract_single(url)
            return [info] if info else []
    
    async def _extract_album(self, url: str) -> list[DownloadInfo]:
        """Extract all files from a Bunkr album"""
        try:
            html = await self._fetch(url)
        except Exception as e:
            raise ExtractionError(f"Failed to fetch Bunkr album: {e}")
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        
        downloads = []
        
        # Find all file links in the album
        # Bunkr uses various selectors, try common ones
        selectors = [
            "a.grid-images_box-link",
            "a[href*='/v/']",
            "a[href*='/i/']",
            "a[href*='/f/']",
            ".grid-images a",
            "figure a",
        ]
        
        links = set()
        for selector in selectors:
            for link in soup.select(selector):
                href = link.get("href")
                if href:
                    # Make absolute URL
                    full_url = urljoin(url, href)
                    # Only add if it's a valid bunkr file link
                    if any(f"/{t}/" in full_url for t in ["v", "i", "f"]):
                        links.add(full_url)
        
        # Extract each file
        for link_url in links:
            try:
                info = await self._extract_single(link_url)
                if info:
                    downloads.append(info)
            except Exception:
                # Skip failed extractions in album
                continue
        
        if not downloads:
            # Fallback: try to find direct CDN links
            downloads = self._extract_cdn_links(soup, url)
        
        return downloads
    
    async def _extract_single(self, url: str) -> Optional[DownloadInfo]:
        """Extract a single file from a Bunkr page"""
        try:
            html = await self._fetch(url)
        except Exception as e:
            raise ExtractionError(f"Failed to fetch Bunkr page: {e}")
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        
        # Try to find the download link
        download_url = None
        filename = None
        
        # Method 1: Look for download button/link
        download_selectors = [
            "a.btn-download",
            "a[download]",
            "a[href*='cdn']",
            "a.download-btn",
            ".download a",
        ]
        
        for selector in download_selectors:
            link = soup.select_one(selector)
            if link and link.get("href"):
                download_url = link["href"]
                filename = link.get("download") or self._extract_filename_from_url(download_url)
                break
        
        # Method 2: Look for video source
        if not download_url:
            video = soup.select_one("video source, video")
            if video:
                download_url = video.get("src")
                filename = self._extract_filename_from_url(download_url) if download_url else None
        
        # Method 3: Look for image source
        if not download_url:
            img = soup.select_one("img.max-h-full, img.lightgallery-image, .lightgallery img")
            if img:
                download_url = img.get("src")
                filename = self._extract_filename_from_url(download_url) if download_url else None
        
        # Method 4: Parse JavaScript for CDN URL
        if not download_url:
            scripts = soup.find_all("script")
            for script in scripts:
                if script.string:
                    # Look for CDN URLs in JS
                    matches = re.findall(r'https?://[^"\']+(?:cdn|media)[^"\']+', script.string)
                    for match in matches:
                        if any(cdn in match for cdn in self.CDN_DOMAINS):
                            download_url = match
                            filename = self._extract_filename_from_url(download_url)
                            break
        
        if not download_url:
            return None
        
        # Make absolute URL
        download_url = urljoin(url, download_url)
        
        # Get filename from URL if not found
        if not filename:
            filename = self._extract_filename_from_url(download_url)
        
        return DownloadInfo(
            url=download_url,
            filename=filename or "bunkr_file",
            source_url=url,
            resume_supported=True,
        )
    
    def _extract_cdn_links(self, soup, base_url: str) -> list[DownloadInfo]:
        """Fallback: extract any CDN links found in the page"""
        downloads = []
        
        # Find all links and images pointing to CDN
        for tag in soup.find_all(["a", "img", "video", "source"]):
            url = tag.get("href") or tag.get("src")
            if url and any(cdn in url for cdn in self.CDN_DOMAINS):
                full_url = urljoin(base_url, url)
                filename = self._extract_filename_from_url(full_url)
                downloads.append(DownloadInfo(
                    url=full_url,
                    filename=filename or "bunkr_file",
                    source_url=base_url,
                    resume_supported=True,
                ))
        
        return downloads
    
    def _extract_filename_from_url(self, url: str) -> str:
        """Extract filename from URL"""
        from urllib.parse import urlparse, unquote
        
        parsed = urlparse(url)
        path = unquote(parsed.path)
        filename = path.split("/")[-1]
        
        # Remove query string
        if "?" in filename:
            filename = filename.split("?")[0]
        
        return filename if filename else "bunkr_file"
