# MacDL 🚀

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![macOS](https://img.shields.io/badge/platform-macOS-lightgrey.svg)](https://www.apple.com/macos/)

A lightweight, open-source download manager for macOS with multi-threaded downloads and file hosting site support.

## ✨ Features

- **Multi-threaded Downloads**: Split files into chunks and download in parallel for maximum speed
- **File Hosting Support**: Built-in plugins for popular sites (Bunkr, GoFile, and more)
- **Resume Support**: Automatically resume interrupted downloads
- **CLI & GUI**: Use from terminal or with a sleek desktop interface
- **Plugin Architecture**: Easily extend support for new sites
- **Low Profile**: Minimal resource usage, runs quietly in the background

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/drsanjula/macdl.git
cd macdl

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e ".[all]"
```

## 🚀 Quick Start

### CLI Usage

```bash
# Download a file
macdl download "https://example.com/file.zip"

# Download with multiple threads
macdl download "https://example.com/large-file.zip" --threads 8

# Download from file hosting sites
macdl download "https://gofile.io/d/abc123"

# Batch download from file
macdl download -f urls.txt -o ~/Downloads/
```

### GUI Usage

```bash
# Launch the graphical interface
macdl gui
```

## 🔌 Supported Sites

| Site | Status |
|------|--------|
| HTTP/HTTPS (direct links) | ✅ |
| GoFile.io | ✅ |
| Bunkr.su | 🚧 |
| More coming... | 📋 |

## 🏗️ Architecture

```
macdl/
├── core/           # Download engine
├── plugins/        # Site extractors
├── cli/            # Command-line interface
├── gui/            # Desktop application
└── storage/        # Database & config
```

## 🛠️ Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run linter
ruff check .
```

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

Made with ❤️ for the macOS community
