"""
Custom exceptions for MacDL
"""


class MacDLError(Exception):
    """Base exception for all MacDL errors"""
    pass


class DownloadError(MacDLError):
    """Error during file download"""
    pass


class ResumeNotSupportedError(DownloadError):
    """Server doesn't support resume (no Range header support)"""
    pass


class FileSizeError(DownloadError):
    """Unable to determine file size"""
    pass


class ChecksumError(DownloadError):
    """File checksum verification failed"""
    pass


class PluginError(MacDLError):
    """Error in plugin execution"""
    pass


class ExtractionError(PluginError):
    """Failed to extract download info from URL"""
    pass


class UnsupportedURLError(PluginError):
    """No plugin available for this URL"""
    pass


class NetworkError(MacDLError):
    """Network-related error"""
    pass


class TimeoutError(NetworkError):
    """Request timed out"""
    pass


class RateLimitError(NetworkError):
    """Rate limited by server"""
    pass


class ConfigError(MacDLError):
    """Configuration error"""
    pass
