"""
Base plugin class for site extractors
"""

from abc import ABC, abstractmethod
from typing import Optional
import re
import aiohttp

from macdl.core.models import DownloadInfo


class BasePlugin(ABC):
    """
    Abstract base class for all MacDL plugins.
    
    Plugins are responsible for extracting actual download URLs
    from various hosting sites (GoFile, Bunkr, etc.)
    
    To create a new plugin:
    1. Subclass BasePlugin
    2. Set `name` and `domains`
    3. Implement `extract()` method
    4. Register in the plugin registry
    """
    
    # Plugin metadata
    name: str = "base"
    description: str = "Base plugin"
    version: str = "0.1.0"
    
    # List of domains this plugin handles
    # e.g., ["gofile.io", "gofile.me"]
    domains: list[str] = []
    
    # URL patterns (regex) this plugin handles
    # More specific than domains, optional
    url_patterns: list[str] = []
    
    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        self._session = session
        self._owns_session = False
    
    async def __aenter__(self):
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._close_session()
    
    async def _ensure_session(self) -> None:
        """Create a session if one doesn't exist"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
            self._owns_session = True
    
    async def _close_session(self) -> None:
        """Close the session if we own it"""
        if self._owns_session and self._session and not self._session.closed:
            await self._session.close()
    
    def can_handle(self, url: str) -> bool:
        """
        Check if this plugin can handle the given URL.
        
        Override for custom matching logic.
        Default: checks domains and url_patterns.
        """
        # Check domains
        if self.domains:
            if any(domain in url for domain in self.domains):
                return True
        
        # Check URL patterns
        if self.url_patterns:
            for pattern in self.url_patterns:
                if re.search(pattern, url):
                    return True
        
        return False
    
    @abstractmethod
    async def extract(self, url: str) -> list[DownloadInfo]:
        """
        Extract download information from the URL.
        
        Args:
            url: The URL to extract from
            
        Returns:
            List of DownloadInfo objects with direct download URLs
            
        Raises:
            ExtractionError: If extraction fails
        """
        pass
    
    async def _fetch(self, url: str, **kwargs) -> str:
        """Fetch a URL and return the text content"""
        await self._ensure_session()
        async with self._session.get(url, **kwargs) as response:
            response.raise_for_status()
            return await response.text()
    
    async def _fetch_json(self, url: str, **kwargs) -> dict:
        """Fetch a URL and return JSON content"""
        await self._ensure_session()
        async with self._session.get(url, **kwargs) as response:
            response.raise_for_status()
            return await response.json()
    
    async def _head(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Make a HEAD request"""
        await self._ensure_session()
        return await self._session.head(url, allow_redirects=True, **kwargs)
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.name}>"
