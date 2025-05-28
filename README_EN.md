# SimpleTweakEditor

<div align="center">

![SimpleTweakEditor Logo](https://img.shields.io/badge/SimpleTweakEditor-v1.0.1-blue?style=for-the-badge&logo=apple&logoColor=white)

[![License](https://img.shields.io/github/license/Evil0ctal/SimpleTweakEditor?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.0%2B-green?style=flat-square&logo=qt&logoColor=white)](https://pypi.org/project/PyQt6/)
[![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Linux-lightgrey?style=flat-square)](https://github.com/Evil0ctal/SimpleTweakEditor)
[![GitHub Stars](https://img.shields.io/github/stars/Evil0ctal/SimpleTweakEditor?style=flat-square)](https://github.com/Evil0ctal/SimpleTweakEditor/stargazers)
[![Downloads](https://img.shields.io/github/downloads/Evil0ctal/SimpleTweakEditor/total?style=flat-square)](https://github.com/Evil0ctal/SimpleTweakEditor/releases)

**Professional iOS .deb Package Editor with Modern GUI**

[中文文档](README.md) | [Quick Start](docs/QUICK_START.md) | [Download](https://github.com/Evil0ctal/SimpleTweakEditor/releases)

</div>

## ✨ Features

### 🔐 Security First
- **Path Validation** - Protection against path traversal attacks
- **File Size Limits** - Prevents resource exhaustion (500MB max)
- **Secure Operations** - Atomic file operations with proper permissions
- **Safe Configuration** - Secure permission management (0600)

### 🎯 Core Functionality
- **Unpack .deb Files** - Extract .deb packages while preserving structure
- **Repack Folders** - Build .deb packages from modified folders
- **Drag & Drop** - Simple drag and drop interface for quick operations
- **Control File Editor** - Built-in editor with syntax validation
- **Batch Processing** - Command-line support for automation
- **Package Management** - Built-in package browser and repository management
- **Interactive Terminal** - Real PTY-based terminal with multi-tab support

### 🌍 User Experience
- **Multi-language** - English/Chinese with automatic system detection
- **Multiple Themes** - Dark mode, light mode, and colorful themes
- **Dynamic Layout** - Smart layout adaptation based on screen size
- **Window Management** - Automatic window centering and state persistence
- **Smart Detection** - Automatically finds dpkg-deb in multiple paths
- **Cross-platform Fonts** - Improved font compatibility across different systems
- **Intuitive UI** - Clean, modern interface with helpful tooltips

## 🚀 Installation

### System Requirements
- **macOS**: 10.13 or later
- **Linux**: Ubuntu 18.04+ or equivalent
- **Dependencies**: dpkg-deb (for .deb operations)

### Quick Install

#### Option 1: Download Standalone App (Recommended)
1. Download `SimpleTweakEditor-macOS-standalone.zip` from [Releases](https://github.com/Evil0ctal/SimpleTweakEditor/releases)
2. Extract and move SimpleTweakEditor.app to Applications
3. Install dpkg: `brew install dpkg`
4. Right-click and select "Open" on first launch

#### Option 2: Run from Source
```bash
# Clone repository
git clone https://github.com/Evil0ctal/SimpleTweakEditor.git
cd SimpleTweakEditor

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run application
python main.py
```

## 📖 Usage

### GUI Mode
Simply launch the application and:
1. **Drag & drop** a .deb file to unpack it
2. **Edit** the contents as needed
3. **Repack** the folder back to .deb

### Command Line Mode
```bash
# Show help
python main.py --help

# Unpack a .deb file
python main.py --unpack package.deb --output ./unpacked/

# Repack a folder
python main.py --repack ./package_folder/ --output package_new.deb

# Batch unpack
python main.py --batch --unpack "*.deb"

# Set language
python main.py --lang en  # or 'zh' for Chinese
```

## 🛠️ Building

### Build Standalone macOS App
```bash
cd build_scripts
python3 build_macos_app_standalone.py
```

### Build for Distribution
```bash
./build_scripts/prepare_release.sh
```

## 📚 Documentation

- [Quick Start Guide](docs/QUICK_START.md) - Get started in minutes
- [Release Notes](RELEASE_NOTES.md) - What's new in each version (Chinese)
- [Release Notes (EN)](RELEASE_NOTES_EN.md) - English release notes
- [Feature Roadmap](docs/FEATURE_ROADMAP.md) - Planned features and improvements
- [Project Structure](docs/PROJECT_STRUCTURE.md) - Understanding the codebase
- [Repository Manager Guide](docs/REPO_MANAGER_GUIDE.md) - Managing software repositories
- [Theme Documentation](docs/THEMES.md) - Theme system and customization

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📋 Troubleshooting

### Common Issues

**Q: "dpkg-deb not found" error**  
A: Install dpkg using your package manager:
- macOS: `brew install dpkg`
- Ubuntu/Debian: `sudo apt-get install dpkg`

**Q: App won't open on macOS**  
A: Right-click the app and select "Open" to bypass Gatekeeper on first launch.

**Q: Missing PyQt6 error**  
A: Install Python dependencies: `pip3 install PyQt6 Pillow`

## 📝 Changelog

### v1.0.1 (2025-05-28)
- 🔧 **UI Layout Optimization** - Fixed interactive terminal component overlap and display issues
- 🌍 **Language Switching Stability** - Resolved crashes when switching languages
- 🎨 **Font Compatibility** - Improved cross-platform font handling, fixed macOS font warnings
- 📐 **Dynamic Layout** - Enhanced window size adaptation and component auto-adjustment
- 🖥️ **Terminal Improvements** - True PTY terminal support with multi-tab functionality
- 📦 **Package Management** - Built-in package browser and repository management
- 🎯 **Window Centering** - Automatic window positioning and state saving
- 🗂️ **Documentation Cleanup** - Reorganized project documentation structure

### v1.0.0 (2025-05-24)
- ✨ First official release
- 🔐 Enhanced security and path validation
- 🌍 Multi-language support with automatic system language detection
- 🎨 Multiple theme support (dark, light, colorful)
- 📦 Modular refactoring for improved code quality
- 🚀 Standalone .app build with all dependencies included
- 🔍 Smart dpkg-deb tool path detection

For detailed release notes, see [RELEASE_NOTES_EN.md](RELEASE_NOTES_EN.md)

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Thanks to all contributors and testers
- PyQt6 for the excellent GUI framework
- The iOS jailbreak community for inspiration

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/Evil0ctal/SimpleTweakEditor/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Evil0ctal/SimpleTweakEditor/discussions)
- **Email**: evil0ctal@gmail.com

---

<div align="center">

**Note**: This tool is for legitimate iOS development and debugging purposes only. Please comply with relevant laws and regulations.

Made with ❤️ by [Evil0ctal](https://github.com/Evil0ctal)

⭐ Star this project if you find it helpful!

</div>