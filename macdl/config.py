"""
Configuration management for MacDL
"""

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


@dataclass
class Config:
    """MacDL configuration settings"""
    
    # Download settings
    download_dir: str = field(default_factory=lambda: str(Path.home() / "Downloads"))
    max_concurrent_downloads: int = 3
    threads_per_download: int = 8
    chunk_size: int = 1024 * 1024  # 1 MB
    
    # Network settings
    timeout: int = 30
    max_retries: int = 3
    user_agent: str = "MacDL/0.1.0"
    
    # UI settings
    show_progress: bool = True
    theme: str = "dark"
    
    # Plugin settings
    enabled_plugins: list[str] = field(default_factory=lambda: ["http", "gofile", "bunkr"])
    
    _config_path: Optional[Path] = field(default=None, repr=False)
    
    @classmethod
    def get_default_config_path(cls) -> Path:
        """Get the default config file path"""
        config_dir = Path.home() / ".config" / "macdl"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "config.json"
    
    @classmethod
    def load(cls, path: Optional[Path] = None) -> "Config":
        """Load configuration from file"""
        config_path = path or cls.get_default_config_path()
        
        if config_path.exists():
            with open(config_path) as f:
                data = json.load(f)
                config = cls(**data)
                config._config_path = config_path
                return config
        
        # Return default config if file doesn't exist
        config = cls()
        config._config_path = config_path
        return config
    
    def save(self, path: Optional[Path] = None) -> None:
        """Save configuration to file"""
        config_path = path or self._config_path or self.get_default_config_path()
        
        # Convert to dict, excluding private fields
        data = {k: v for k, v in asdict(self).items() if not k.startswith("_")}
        
        with open(config_path, "w") as f:
            json.dump(data, f, indent=2)
    
    def get_download_path(self, filename: str) -> Path:
        """Get full path for a download file"""
        return Path(self.download_dir) / filename
