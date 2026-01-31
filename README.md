# MacDL 🚀

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![macOS](https://img.shields.io/badge/platform-macOS-lightgrey.svg)](https://www.apple.com/macos/)

A lightweight, open-source download manager for macOS with multi-threaded downloads and file hosting site support.

## ✨ Features

- **🚀 Multi-threaded Downloads**: Split files into chunks and download in parallel for maximum speed
- **🔌 File Hosting Support**: Built-in plugins for GoFile, Bunkr, and direct HTTP/HTTPS links
- **🔄 Resume Support**: Automatically resume interrupted downloads via Range headers
- **🖥️ CLI & GUI**: Use from terminal with rich output or with a sleek PySide6 desktop interface
- **📊 Progress Tracking**: Real-time speed, ETA, and progress visualization
- **💾 Download History**: SQLite-backed history with statistics
- **🔧 Plugin Architecture**: Easily extend support for new sites

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/drsanjula/macdl.git
cd macdl

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install with all features (CLI + GUI)
pip install -e ".[all]"

# Or install CLI only
pip install -e .

# Or install with GUI support
pip install -e ".[gui]"
```

## 🚀 Quick Start

### CLI Usage

```bash
# Download a file
macdl download "https://example.com/file.zip"

# Download with custom threads
macdl download "https://example.com/large.zip" -t 16

# Download from file hosting sites (auto-detected)
macdl download "https://gofile.io/d/abc123"
macdl download "https://bunkr.su/a/xyz789"

# Specify output directory
macdl download "https://example.com/file.zip" -o ~/Downloads/

# Batch download multiple URLs
macdl batch url1 url2 url3

# Batch download from file
macdl batch -f urls.txt -o ~/Downloads/

# View download history
macdl history

# View statistics
macdl history --stats

# Clear history
macdl history --clear

# Show configuration
macdl config

# List available plugins
macdl plugins
```

### GUI Usage

```bash
# Launch the graphical interface
macdl gui
```

Features a modern dark theme with:
- URL input with auto-detection of file hosting sites
- Download list with real-time progress bars
- Speed and ETA display
- Settings and history management

## 🔌 Supported Sites

| Site | Status | Description |
|------|--------|-------------|
| HTTP/HTTPS | ✅ | Direct download links |
| GoFile.io | ✅ | File hosting with API support |
| Bunkr.su/si/is | ✅ | Album and single file downloads |

### Adding New Plugins

Create a new plugin by extending `BasePlugin`:

```python
from macdl.plugins.base import BasePlugin
from macdl.core.models import DownloadInfo

class MyPlugin(BasePlugin):
    name = "mysite"
    description = "MySite.com downloads"
    domains = ["mysite.com"]
    
    async def extract(self, url: str) -> list[DownloadInfo]:
        # Extract actual download URLs
        return [DownloadInfo(url=direct_url, filename="file.zip")]
```

## 🏗️ Architecture

```
macdl/
├── core/           # Async download engine (aiohttp)
│   ├── downloader.py   # Segmented download logic
│   ├── models.py       # DownloadJob, Segment, etc.
│   └── progress.py     # Speed/ETA tracking
├── plugins/        # Site extractors
│   ├── base.py         # BasePlugin class
│   ├── registry.py     # Plugin discovery
│   ├── http_plugin.py  # Direct URLs (fallback)
│   ├── gofile.py       # GoFile.io
│   └── bunkr.py        # Bunkr.su
├── cli/            # Click-based CLI
│   └── main.py         # Commands
├── gui/            # PySide6 desktop app
│   ├── app.py          # Entry point
│   └── main_window.py  # UI components
├── storage/        # SQLite persistence
│   └── database.py     # History/state
└── config.py       # Configuration management
```

## 🛠️ Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run linter
ruff check .

# Format code
ruff format .
```

## 📝 Configuration

Configuration is stored in `~/.config/macdl/config.json`:

```json
{
  "download_dir": "~/Downloads",
  "max_concurrent_downloads": 3,
  "threads_per_download": 8,
  "chunk_size": 1048576,
  "timeout": 30,
  "max_retries": 3
}
```

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing`)
5. Open a Pull Request

---

Made with ❤️ for the macOS community
