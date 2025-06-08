# SimpleTweakEditor Release Notes

<div align="center">

English | [中文](RELEASE_NOTES.md)

</div>

## 🚀 v1.0.4 (2025-01-07)

### iOS Device Support & SSH Terminal

This version introduces major new features including complete iOS device support and a professional SSH terminal, making SimpleTweakEditor a more comprehensive iOS development tool.

#### 🆕 Major New Features

##### 📱 iOS Device File Management
- **AFC Protocol Support** - Direct iOS filesystem access via Apple File Conduit protocol
  - Real-time device detection and connection management
  - Complete filesystem browsing and navigation
  - File upload, download, delete and rename operations
  - Support for non-jailbroken, rootless and rootful jailbreak modes
  - Intelligent path mapping and permission handling

##### 🔌 Professional SSH Terminal
- **Device Auto-Discovery** - Automatically scan USB and Wi-Fi connected iOS devices
  - USB devices via automatic iproxy port forwarding
  - Wi-Fi devices via network scanning
  - Support for manually adding custom devices
  
- **Secure Credential Management** - Securely store SSH credentials using system keychain
  - Automatic save and load of login information
  - Support for password and key authentication
  - Credential manager UI for easy management
  
- **Multi-Session Support** - Manage multiple SSH connections simultaneously
  - Tabbed interface for easy session switching
  - Independent terminal instance for each session
  - Support for session cloning and quick reconnect
  
- **Quick Command Library** - Preset common iOS management commands
  - System information viewing
  - Process management
  - File operations
  - Security checks
  - User-defined scripts

#### 🎨 Interface Enhancements
- **New Device Panel** - Dedicated iOS device management interface
  - Real-time device information display
  - File manager integration
  - Quick action buttons
  
- **SSH Terminal Panel** - Theme-aware professional terminal interface
  - Seamlessly integrated with app theme system
  - Adaptive light/dark themes
  - Optimized fonts and color schemes

#### 🔧 Technical Improvements
- **Modular Architecture** - New independent SSH and device management modules
  - `src/modules/ssh_terminal/` - SSH terminal implementation
  - `src/core/ios_filesystem.py` - iOS filesystem abstraction layer
  - `src/core/device_manager.py` - Device detection and management
  
- **Dependency Optimization** - Graceful degradation with optional dependencies
  - paramiko for SSH connections
  - pymobiledevice3 for iOS device access
  - Friendly prompts when dependencies are missing

- **Security Enhancements** - Multi-layer security protection
  - SSH connection encryption
  - Secure credential storage
  - Path validation and permission checks

#### 🐛 Fixes and Optimizations
- Improved main window tab management
- Optimized large file transfer performance
- Enhanced error handling and logging
- Fixed encoding issues in certain scenarios

### Upgrade Notes
- New features require additional Python packages:
  ```bash
  pip install paramiko pymobiledevice3
  ```
- iOS device features require iTunes/Apple Mobile Device Support (Windows)
- SSH features require jailbroken device with OpenSSH installed

---

## 📝 v1.0.3 (2025-06-01)

### Plist Editor & Project Optimization

This release brings a brand new Plist editor, project structure cleanup, and documentation support for future AI-assisted development.

#### 🆕 Major New Features
- **Full-Featured Plist Editor** - Supports both tree view and text editing modes
  - Complete support for all plist data types (dictionary, array, string, number, boolean, data, date)
  - Syntax highlighting (XML and text formats)
  - Undo/redo functionality (Ctrl+Z/Ctrl+Y)
  - Drag-and-drop support - Drop .plist files directly into editor
  - Right-click context menu - Quick add/delete/modify items
  - Key-value editor - More intuitive property editing
  - Data validation - Real-time input validity checking

#### 🧹 Project Cleanup & Optimization
- **Test File Cleanup** - Removed all legacy test files
  - Removed debug_array.plist, test_*.plist and other test files
  - Deleted test_data/ directory
  - Cleaned up __pycache__ and .DS_Store files
  
- **Documentation Reorganization** - All docs moved to docs/ directory
  - Moved SECURITY_*.md files to docs/
  - Unified documentation management structure
  - Updated .gitignore to prevent test file commits

#### 🌍 Localization Improvements
- **Eliminated Hardcoded Chinese** - Fixed all hardcoded Chinese strings
  - RepoRefreshWorker now properly uses language manager
  - All package manager UI text is localized
  - Download progress and status messages support multiple languages

#### 🔐 Security Enhancements
- **Enhanced Path Traversal Protection** - Improved path validation logic
- **File Size Validation** - Plist editor limits file size (max 100MB)
- **Secure File Operations** - All file operations go through security validation

#### 🔧 Technical Improvements
- **Code Quality** - Unified file header format and comment standards
- **Error Handling** - Improved exception handling with user-friendly error messages
- **Performance Optimization** - Plist editor uses efficient tree rendering
- **UI Consistency** - All new components follow existing design language

### Developer Notes
- Added CLAUDE.md providing comprehensive development guidance
- Improved project structure documentation
- Clearer code organization and module separation

---

## 🪟 v1.0.2 (2025-05-30)

### Windows Platform Support & Interactive Terminal Enhancement

This release's major highlight is the addition of full Windows platform support, solving the dpkg dependency issue on Windows through a pure Python implementation, and fixing critical issues with the interactive terminal across platforms.

#### 🆕 Major New Features
- **Full Windows Support** - Provides complete functionality on Windows platform, identical to macOS/Linux
- **Pure Python dpkg Implementation** - Complete rewrite of .deb file handling logic, no system dpkg dependency required
- **Cross-Platform Permission Handling** - Smart Unix file permission mapping in Windows environment
- **Multi-Compression Support** - Support for gz, xz, lzma and other compression formats in .deb files

#### 🐛 Interactive Terminal Fixes
- **Interactive Terminal dpkg Support** - Fixed "dpkg not found" errors on Linux/macOS
- **Windows Terminal Integration** - Interactive terminal now uses built-in Python dpkg implementation on Windows
- **Chinese Encoding Fix** - Resolved Chinese character display issues in Windows terminal
- **Platform-Specific Commands** - Provided adapted quick commands for Windows

#### 🔧 Technical Improvements
- **AR Archive Format Handling** - Complete AR archive read/write functionality implementation
- **Secure Path Validation** - Enhanced protection against path traversal attacks
- **Smart Permission Mapping** - Automatic executable permission setting for DEBIAN scripts and bin directory files on Windows
- **File Integrity Verification** - Enhanced .deb package validation and testing capabilities
- **Smart dpkg Command Interception** - Automatically detects and handles dpkg-deb commands
- **Cross-Platform Command Support** - Platform-specific quick commands for better UX
- **Multi-Encoding Support** - Windows terminal supports UTF-8, GBK, GB2312 encodings
- **Environment Optimization** - Proper environment variable setup for Windows terminal

#### 📦 Build System & Compatibility
- **Universal Build System** - New `build.py` one-click build script, auto-detects platform and builds appropriate format
- **Legacy Scripts Removal** - Removed `build_scripts` directory and all legacy build scripts
- **Backward Compatibility** - Maintains full compatibility with existing code
- **Multi-Platform Build** - Updated build scripts to support cross-platform releases
- **Documentation Updates** - Updated README and release notes to reflect Windows support

### Technical Implementation Details
- Implemented complete `dpkg_deb.py` module providing same API as dpkg-deb
- Supports extract, build, info, contents listing, and verify operations
- Automatic detection and setting of appropriate Unix permissions on Windows (755 for executables, 644 for regular files)
- Support for lzma compression format, compatible with older iOS package formats
- Added `terminal_dpkg_wrapper.py` module for cross-platform dpkg command support
- Improved command handling logic in interactive terminal
- Enhanced terminal output encoding handling
- Optimized command list for platform adaptation

---

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