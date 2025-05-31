# SimpleTweakEditor

<div align="center">

![SimpleTweakEditor Logo](https://img.shields.io/badge/SimpleTweakEditor-v1.0.2-blue?style=for-the-badge&logo=apple&logoColor=white)

[![License](https://img.shields.io/github/license/Evil0ctal/SimpleTweakEditor?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.0%2B-green?style=flat-square&logo=qt&logoColor=white)](https://pypi.org/project/PyQt6/)
[![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey?style=flat-square)](https://github.com/Evil0ctal/SimpleTweakEditor)
[![GitHub Stars](https://img.shields.io/github/stars/Evil0ctal/SimpleTweakEditor?style=flat-square)](https://github.com/Evil0ctal/SimpleTweakEditor/stargazers)
[![Downloads](https://img.shields.io/github/downloads/Evil0ctal/SimpleTweakEditor/total?style=flat-square)](https://github.com/Evil0ctal/SimpleTweakEditor/releases)
[![Release](https://img.shields.io/github/v/release/Evil0ctal/SimpleTweakEditor?style=flat-square)](https://github.com/Evil0ctal/SimpleTweakEditor/releases/latest)

**Professional iOS .deb Package Editor - Cross-Platform, No Dependencies**

🚀 **One-Click Unpack/Repack** | 🎯 **Smart Control Editor** | 🌍 **Cross-Platform** | 📦 **Package Manager**

[中文文档](README.md) | [Quick Start](docs/QUICK_START.md) | [Download](https://github.com/Evil0ctal/SimpleTweakEditor/releases)

</div>

## 📸 Screenshots

<div align="center">
<table>
  <tr>
    <td align="center">
      <img src="screenshots/en/main_window_dark.png" width="400" alt="Main Interface - Dark Theme">
      <br>
      <sub><b>Main Interface</b></sub>
    </td>
    <td align="center">
      <img src="screenshots/en/package_manager.png" width="400" alt="Package Manager">
      <br>
      <sub><b>Package Manager</b></sub>
    </td>
    <td align="center">
      <img src="screenshots/en/interactive_terminal.png" width="400" alt="Interactive Terminal">
      <br>
      <sub><b>Interactive Terminal</b></sub>
    </td>
  </tr>
  <tr>
    <td align="center">
      <img src="screenshots/en/control_editor.png" width="400" alt="Control File Editor">
      <br>
      <sub><b>Control File Editor</b></sub>
    </td>
    <td align="center">
      <img src="screenshots/en/package_history.png" width="400" alt="Package Version Selection">
      <br>
      <sub><b>Package Version Selection</b></sub>
    </td>
    <td align="center">
      <img src="screenshots/en/repo_manager.png" width="400" alt="Repository Manager">
      <br>
      <sub><b>Repository Manager</b></sub>
    </td>
  </tr>
</table>
</div>

## 🎯 Core Features

### 📦 .deb Package Handling
- **One-Click Unpack** - Drag & drop to extract, preserving directory structure and permissions
- **Smart Repack** - Automatic validation ensures Debian-compliant packages
- **Cross-Platform** - Runs on Windows/macOS/Linux, no dpkg required on Windows
- **Batch Operations** - Command-line batch mode for efficient multi-package processing

### 📝 Control File Editor
- **Syntax Highlighting** - Optimized highlighting for Control file syntax
- **Real-time Validation** - Live format and dependency checking
- **Auto-completion** - Smart suggestions for package names and versions
- **Template Support** - Built-in templates for common Control files

### 📱 Package Manager
- **Multi-Source Support** - Integrated BigBoss, Chariz, Packix and major iOS repos
- **Package Browser** - Browse and search thousands of iOS tweaks by category
- **Version History** - View all package versions, download specific releases
- **Offline Cache** - Smart caching for faster loading

### 💻 Interactive Terminal
- **Real PTY** - Full pseudo-terminal with color and special character support
- **Multi-tabs** - Run multiple terminal sessions simultaneously
- **Command Presets** - Quick buttons for common dpkg/apt commands
- **History** - Command history with quick re-execution

### 🎨 Interface & Experience
- **Modern UI** - Native PyQt6 interface, smooth and beautiful
- **Dark/Light Themes** - Automatic theme switching based on system
- **Multi-language** - English/Chinese interface with auto-detection
- **Drag & Drop** - Intuitive file operations
- **State Persistence** - Remembers window position, size and preferences

### 🔐 Security Features
- **Path Protection** - Prevents path traversal and symlink attacks
- **Size Limits** - File size restrictions prevent memory exhaustion
- **Permission Handling** - Correct Unix permissions even on Windows
- **Integrity Checks** - Package structure validation prevents corruption

## 🚀 Installation

### System Requirements
- **macOS**: 10.13 or later
- **Linux**: Ubuntu 18.04+ or equivalent
- **Windows**: Windows 10 or later
- **Dependencies**: dpkg-deb (Linux/macOS), built-in pure Python implementation on Windows

### Download Pre-built Releases (Recommended)

Download the version for your system from [Releases](https://github.com/Evil0ctal/SimpleTweakEditor/releases):

| Platform | Filename | Description |
|----------|----------|-------------|
| **Windows** | `SimpleTweakEditor-v1.0.2-Windows-x64.zip` | Extract and run, no installation |
| **macOS Intel** | `SimpleTweakEditor-v1.0.2-macOS-x64.zip` | For Intel-based Macs |
| **macOS Apple Silicon** | `SimpleTweakEditor-v1.0.2-macOS-Apple-Silicon.zip` | For M1/M2/M3 Macs |
| **Linux** | `SimpleTweakEditor-v1.0.2-Linux-x64.zip` | Works on most Linux distributions |

#### Run from Source
```bash
# Clone repository
git clone https://github.com/Evil0ctal/SimpleTweakEditor.git
cd SimpleTweakEditor

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install dependencies
pip install -r requirements.txt

# macOS users install dpkg
brew install dpkg

# Linux users install dpkg
sudo apt-get install dpkg

# Windows users need no additional setup
# Application automatically uses built-in pure Python dpkg implementation

# Run application
python main.py
```

## 📖 Usage

### GUI Mode
1. Double-click to launch the application
2. Drag & drop a .deb file to the main window to unpack
3. Edit files as needed
4. Click "Repack" button to create new .deb

### Command Line Mode
```bash
# Unpack a .deb file
python main.py --unpack package.deb --output ./unpacked/

# Repack a folder
python main.py --repack ./package_folder/ --output package_new.deb

# Batch unpack multiple files
python main.py --batch --unpack "*.deb"

# Set interface language
python main.py --lang en  # English
python main.py --lang zh  # Chinese
```

## 🛠️ How It Works

### Windows .deb Handling
This tool uses a pure Python dpkg implementation on Windows, no WSL or Linux tools required:
- Complete AR archive format parsing
- Supports all compression formats (gz/xz/lzma)
- Smart Unix permission mapping
- Automatic executable detection and permission setting

### Smart Permission Handling
.deb packages created on Windows automatically get correct Unix permissions:
- DEBIAN scripts (preinst/postinst/etc): 755
- Binary executables: 755
- Regular files: 644
- Directories: 755

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

### 🆕 v1.0.2 (2025-05-30) - Full Windows Support
**Major Update: Complete Windows Support!**
- 🪟 **Native Windows Support**
  - Pure Python dpkg implementation, no WSL or Cygwin needed
  - Full Windows 10/11 compatibility
  - Automatic path separator and permission handling
- 🔧 **Cross-Platform .deb Engine**
  - Complete AR archive format implementation
  - All compression formats supported (gz/xz/lzma)
  - Smart Unix permission preservation
- 📦 **Universal Build System**
  - New `build.py` one-click build script
  - Auto-detects platform and builds appropriate format
  - Creates versioned zip archives for easy distribution
- 🛡️ **Security Enhancements**
  - Improved path traversal protection
  - Enhanced package integrity verification
  - File size limits to prevent DoS

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

## 📁 Project Structure

```
SimpleTweakEditor/
├── main.py                    # Main entry point
├── requirements.txt           # Python dependencies
├── README.md                 # Chinese documentation
├── README_EN.md             # This file
├── RELEASE_NOTES.md         # Release notes (Chinese)
├── RELEASE_NOTES_EN.md      # Release notes (English)
├── LICENSE                   # Apache 2.0 License
├── docs/                     # Documentation directory
│   ├── PROJECT_STRUCTURE.md  # Detailed architecture docs
│   ├── QUICK_START.md        # Quick start guide
│   ├── FEATURE_ROADMAP.md    # Feature roadmap
│   ├── REPO_MANAGER_GUIDE.md # Repository manager guide
│   └── THEMES.md             # Theme documentation
│
├── src/                      # Source code
│   ├── core/                 # Core modules
│   │   ├── app.py           # Main application logic
│   │   ├── config.py        # Configuration management
│   │   ├── events.py        # Event definitions
│   │   └── repo_manager.py  # Repository management
│   │
│   ├── ui/                   # User interface
│   │   ├── main_window.py   # Main window
│   │   ├── control_editor.py # Control file editor
│   │   ├── about_dialog_improved.py # About dialog
│   │   ├── interactive_terminal.py # Interactive terminal
│   │   ├── package_browser_dialog.py # Package browser
│   │   ├── package_manager_widget.py # Package manager
│   │   ├── repo_manager_dialog.py # Repository manager dialog
│   │   └── styles.py        # Style management
│   │
│   ├── workers/              # Background tasks
│   │   ├── command_thread.py # Command execution
│   │   └── download_thread.py # Download tasks
│   │
│   ├── utils/                # Utilities
│   │   ├── file_operations.py # File operations
│   │   ├── dpkg_deb.py      # Cross-platform dpkg implementation
│   │   └── system_utils.py  # System utilities
│   │
│   ├── localization/        # Localization
│   │   ├── language_manager.py # Language manager
│   │   └── translations.py  # Translation data
│   │
│   └── resources/           # Resources
│       └── default_repositories.json # Default repositories
│
├── build.py                 # Universal build script
│
└── releases/                # Release files
    └── vX.X.X/             # Version release directory
        ├── Windows/        # Windows builds
        ├── Darwin/         # macOS builds
        └── Linux/          # Linux builds
```

## 💻 Development Guide

### 🔨 Building Releases

```bash
# One-click build for current platform
python build.py
```

Automatically generates platform-specific executables in `releases/` directory

### Code Quality
- Follows PEP 8 standards
- Type hints (coming soon)
- Comprehensive error handling
- Security-first design philosophy

### Adding New Features
1. File operations go in `utils/file_operations.py`
2. UI components go in the `ui/` directory
3. Background tasks inherit from `CommandThread` class
4. Translations go in `translations.py`

### Contributing Guidelines
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Create a Pull Request

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- PyQt6 development team
- dpkg maintainers
- All contributors

## 📞 Contact

- **Author**: Evil0ctal
- **GitHub**: https://github.com/Evil0ctal
- **Project**: https://github.com/Evil0ctal/SimpleTweakEditor

---

<div align="center">

**Note**: This tool is for legitimate iOS development and debugging purposes only. Please comply with relevant laws and regulations.

---

Made with ❤️ by [Evil0ctal](https://github.com/Evil0ctal)

⭐ Star this project if you find it helpful!

</div>