# SimpleTweakEditor Release Notes

<div align="center">

English | [中文](RELEASE_NOTES.md)

</div>

## 🔧 v1.0.1 (2025-05-28)

### Bug Fixes & Improvements

This release focuses on stability improvements, UI layout fixes, and enhanced user experience based on feedback from v1.0.0.

#### 🐛 Critical Bug Fixes
- **Language Switching Stability** - Fixed crashes when switching between languages due to missing UI component checks
- **UI Layout Issues** - Resolved component overlap problems in the main window and interactive terminal
- **Font Compatibility** - Fixed macOS font warnings by implementing proper font fallback mechanisms
- **Terminal Display** - Corrected height restrictions and splitter orientation issues in the terminal interface

#### ✨ Enhancements
- **Dynamic Layout System** - Improved window size adaptation and automatic component adjustment
- **Window Management** - Enhanced automatic window centering and state persistence
- **Interactive Terminal** - True PTY-based terminal with improved multi-tab support
- **Package Management** - Enhanced built-in package browser and repository management
- **Documentation** - Reorganized project structure with dedicated docs folder

#### 🔧 Technical Improvements
- Fixed AttributeError when updating command presets
- Improved cross-platform font handling
- Enhanced error handling for UI component interactions
- Optimized layout calculations for different screen sizes

### What's New Since v1.0.0
- More stable language switching without crashes
- Better terminal experience with proper PTY support
- Improved UI responsiveness and layout management
- Enhanced package management functionality
- Cleaner project documentation structure

---

## 🎉 v1.0.0 (2025-05-24)

### First Official Release

We are excited to announce the first official release of SimpleTweakEditor - a professional iOS .deb package editor with a modern GUI interface.

#### 🆕 New Features
- **Complete GUI Interface** - Modern PyQt6-based interface with intuitive design
- **Multi-language Support** - English and Chinese interfaces with automatic system language detection
- **Package Management** - Built-in software package browser and repository management
- **Interactive Terminal** - Real terminal experience with command execution
- **Smart Tool Detection** - Automatically finds dpkg-deb in various system paths
- **Standalone macOS App** - Self-contained build including all Python dependencies (~31MB)

#### 🔐 Security Features
- **Path Validation** - Protection against path traversal attacks
- **File Size Limits** - 500MB maximum to prevent resource exhaustion
- **Secure File Operations** - Atomic operations with proper permissions
- **Safe Configuration** - Secure permission management (0600)

#### 🎨 User Experience
- **Multiple Themes** - Dark mode, light mode, and colorful themes
- **Drag & Drop Support** - Simply drag files/folders to the application
- **Command Line Interface** - Execute custom dpkg commands
- **Batch Operations** - Command-line mode for automation
- **State Persistence** - Remembers window size and settings

---

## 📋 System Requirements

### macOS
- macOS 10.13 or later
- Python 3.8+ (for source builds)
- Homebrew (for installing dpkg)

### Linux
- Ubuntu 18.04+ or equivalent
- Python 3.8+ (for source builds)
- dpkg package installed

### Dependencies
- PyQt6 (GUI framework)
- Pillow (Image processing)
- dpkg-deb (Required for .deb operations)

---

## 📦 Installation

### macOS

#### Option 1: Standalone App (Recommended)
1. Download `SimpleTweakEditor.app` from releases
2. Drag SimpleTweakEditor.app to Applications
3. First launch: Right-click and select "Open"
4. Install dpkg: `brew install dpkg`

#### Option 2: Source Package
```bash
git clone https://github.com/Evil0ctal/SimpleTweakEditor.git
cd SimpleTweakEditor
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

### Linux

#### Option 1: AppImage
1. Download `SimpleTweakEditor-x86_64.AppImage`
2. Make executable: `chmod +x SimpleTweakEditor-*.AppImage`
3. Run: `./SimpleTweakEditor-*.AppImage`

#### Option 2: Source Build
```bash
git clone https://github.com/Evil0ctal/SimpleTweakEditor.git
cd SimpleTweakEditor
pip3 install -r requirements.txt
python3 main.py
```

---

## 🚀 Quick Start

1. **Launch the application**
   - Double-click the app icon or run from terminal

2. **Unpack a .deb file**
   - Drag and drop a .deb file onto the application
   - Or use File → Unpack .deb Package

3. **Edit the package**
   - Navigate to the unpacked folder
   - Edit files as needed
   - Use the built-in control file editor

4. **Repack the folder**
   - Drag the modified folder back to the application
   - Or use File → Repack Folder
   - Choose output location and filename

---

## 🐛 Known Issues

### v1.0.1
- Terminal functionality requires proper PTY support on host system
- Large .deb files (>500MB) are rejected for security

### v1.0.0 (Fixed in v1.0.1)
- ~~Language switching could cause application crashes~~
- ~~UI components might overlap in certain window sizes~~
- ~~Font compatibility issues on macOS~~

---

## 📁 Documentation

For detailed information about features and usage:
- [Quick Start Guide](docs/QUICK_START.md)
- [Project Structure](docs/PROJECT_STRUCTURE.md)
- [Feature Roadmap](docs/FEATURE_ROADMAP.md)
- [Repository Manager Guide](docs/REPO_MANAGER_GUIDE.md)
- [Theme Documentation](docs/THEMES.md)

---

## 🔒 Security Notes

This tool implements several security measures:
- Path traversal protection
- File size limitations (500MB max)
- Secure file permissions (0600 for config files)
- No network access required
- Safe temporary file operations

---

## 📝 License

SimpleTweakEditor is released under the Apache License 2.0

---

## 🙏 Acknowledgments

- PyQt6 development team
- dpkg maintainers
- All beta testers and contributors

---

## 📞 Support

- **GitHub Issues**: https://github.com/Evil0ctal/SimpleTweakEditor/issues
- **Documentation**: https://github.com/Evil0ctal/SimpleTweakEditor/wiki

---

## 👨‍💻 Author

**Evil0ctal**
- GitHub: https://github.com/Evil0ctal
- Project: https://github.com/Evil0ctal/SimpleTweakEditor

---

<div align="center">

**Thank you for using SimpleTweakEditor!**

⭐ If you find this project helpful, please give it a star on GitHub!

Made with ❤️ by [Evil0ctal](https://github.com/Evil0ctal)

</div>