"""
Plugin registry for discovering and managing plugins
"""

from typing import Optional, Type
import aiohttp

from macdl.plugins.base import BasePlugin
from macdl.core.models import DownloadInfo
from macdl.exceptions import UnsupportedURLError, PluginError


class PluginRegistry:
    """
    Registry for managing and discovering plugins.
    
    Usage:
        registry = PluginRegistry()
        registry.register(GoFilePlugin)
        registry.register(BunkrPlugin)
        
        plugin = registry.get_plugin_for_url(url)
        if plugin:
            info = await plugin.extract(url)
    """
    
    def __init__(self):
        self._plugins: dict[str, Type[BasePlugin]] = {}
        self._instances: dict[str, BasePlugin] = {}
    
    def register(self, plugin_class: Type[BasePlugin]) -> None:
        """Register a plugin class"""
        self._plugins[plugin_class.name] = plugin_class
    
    def unregister(self, name: str) -> None:
        """Unregister a plugin by name"""
        if name in self._plugins:
            del self._plugins[name]
        if name in self._instances:
            del self._instances[name]
    
    def get_plugin(
        self,
        name: str,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> Optional[BasePlugin]:
        """Get a plugin instance by name"""
        if name not in self._plugins:
            return None
        
        # Create instance if not cached
        if name not in self._instances:
            self._instances[name] = self._plugins[name](session=session)
        
        return self._instances[name]
    
    def get_plugin_for_url(
        self,
        url: str,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> Optional[BasePlugin]:
        """Find a plugin that can handle the given URL"""
        for name, plugin_class in self._plugins.items():
            # Create temporary instance to check
            plugin = self.get_plugin(name, session)
            if plugin and plugin.can_handle(url):
                return plugin
        
        return None
    
    async def extract(
        self,
        url: str,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> list[DownloadInfo]:
        """
        Extract download info from URL using appropriate plugin.
        
        Args:
            url: URL to extract from
            session: Optional aiohttp session to reuse
            
        Returns:
            List of DownloadInfo objects
            
        Raises:
            UnsupportedURLError: If no plugin can handle the URL
        """
        plugin = self.get_plugin_for_url(url, session)
        
        if plugin is None:
            raise UnsupportedURLError(f"No plugin available for URL: {url}")
        
        return await plugin.extract(url)
    
    def list_plugins(self) -> list[dict]:
        """List all registered plugins with metadata"""
        result = []
        for name, plugin_class in self._plugins.items():
            result.append({
                "name": name,
                "description": plugin_class.description,
                "version": plugin_class.version,
                "domains": plugin_class.domains,
            })
        return result
    
    @property
    def plugin_names(self) -> list[str]:
        """Get list of registered plugin names"""
        return list(self._plugins.keys())


# Global registry instance
_registry: Optional[PluginRegistry] = None


def get_registry() -> PluginRegistry:
    """Get the global plugin registry, creating it if needed"""
    global _registry
    if _registry is None:
        _registry = PluginRegistry()
        _load_builtin_plugins(_registry)
    return _registry


def _load_builtin_plugins(registry: PluginRegistry) -> None:
    """Load all built-in plugins"""
    from macdl.plugins.http_plugin import HTTPPlugin
    from macdl.plugins.gofile import GoFilePlugin
    from macdl.plugins.bunkr import BunkrPlugin
    
    registry.register(HTTPPlugin)
    registry.register(GoFilePlugin)
    registry.register(BunkrPlugin)
