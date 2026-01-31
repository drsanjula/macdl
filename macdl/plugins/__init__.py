"""
Plugin system for MacDL
"""

from macdl.plugins.base import BasePlugin
from macdl.plugins.registry import PluginRegistry, get_registry
from macdl.plugins.http_plugin import HTTPPlugin
from macdl.plugins.gofile import GoFilePlugin
from macdl.plugins.bunkr import BunkrPlugin

__all__ = [
    "BasePlugin",
    "PluginRegistry",
    "get_registry",
    "HTTPPlugin",
    "GoFilePlugin",
    "BunkrPlugin",
]
