# SimpleTweakEditor v1.0.0 Release Notes

## 🎉 First Official Release

We are excited to announce the first official release of SimpleTweakEditor - a professional iOS .deb package editor with a modern GUI interface.

## ✨ Features

### Core Functionality
- **Unpack .deb files** - Extract contents with proper structure preservation
- **Repack folders** - Create .deb packages from modified folders
- **Control file editor** - Built-in editor with syntax validation
- **Drag & Drop support** - Simply drag files/folders to the application

### User Experience
- **Multi-language support** - English and Chinese interfaces
- **Dark mode** - Automatic system theme adaptation
- **Command line interface** - Execute custom dpkg commands
- **Batch operations** - Command-line mode for automation

### Security
- **Path validation** - Protection against path traversal attacks
- **File size limits** - 500MB maximum to prevent resource exhaustion
- **Secure file operations** - Atomic operations with proper permissions
- **Safe configuration** - Secure permission management (0600)

## 📋 System Requirements

### macOS
- macOS 10.13 or later
- Python 3.8+
- Homebrew (for installing dpkg)

### Linux
- Ubuntu 18.04+ or equivalent
- Python 3.8+
- dpkg package installed

### Dependencies
- PyQt6 (GUI framework)
- Pillow (Image processing)
- dpkg-deb (Required for .deb operations)

## 📦 Installation

### macOS

#### Option 1: DMG Installer (Recommended)
1. Download `SimpleTweakEditor-1.0.0-macOS.dmg`
2. Open the DMG file
3. Drag SimpleTweakEditor.app to Applications
4. First launch: Right-click and select "Open"
5. Install dependencies:
   ```bash
   # Install Python dependencies
   pip3 install PyQt6 Pillow
   
   # Install dpkg
   brew install dpkg
   ```

#### Option 2: Standalone Executable
1. Download `SimpleTweakEditor-1.0.0-Darwin.tar.gz`
2. Extract the archive
3. Make executable: `chmod +x SimpleTweakEditor`
4. Run: `./SimpleTweakEditor`

### Linux

#### Option 1: AppImage (Recommended)
1. Download `SimpleTweakEditor-1.0.0-x86_64.AppImage`
2. Make executable: `chmod +x SimpleTweakEditor-*.AppImage`
3. Run: `./SimpleTweakEditor-*.AppImage`
4. Install dependencies if needed:
   ```bash
   sudo apt-get install python3 python3-pip dpkg
   pip3 install PyQt6 Pillow
   ```

#### Option 2: Tarball
1. Download `SimpleTweakEditor-1.0.0-Linux.tar.gz`
2. Extract: `tar -xzf SimpleTweakEditor-*.tar.gz`
3. Make executable: `chmod +x SimpleTweakEditor`
4. Run: `./SimpleTweakEditor`

## 🚀 Quick Start

1. **Launch the application**
   - Double-click the app icon or run from terminal

2. **Unpack a .deb file**
   - Drag and drop a .deb file onto the application
   - Or use File → Unpack .deb Package

3. **Edit the package**
   - Navigate to the unpacked folder
   - Edit files as needed
   - The control file editor will validate your changes

4. **Repack the folder**
   - Drag the modified folder back to the application
   - Or use File → Repack Folder
   - Choose output location and filename

## 🐛 Known Issues

- On macOS, first launch may require security approval
- Windows is not supported due to dpkg-deb requirements
- Large .deb files (>500MB) are rejected for security

## 🔒 Security Notes

This tool implements several security measures:
- Path traversal protection
- File size limitations
- Secure file permissions
- No network access required

## 📝 License

SimpleTweakEditor is released under the Apache License 2.0

## 🙏 Acknowledgments

- PyQt6 development team
- dpkg maintainers
- All beta testers and contributors

## 📞 Support

- GitHub Issues: https://github.com/Evil0ctal/SimpleTweakEditor/issues
- Documentation: https://github.com/Evil0ctal/SimpleTweakEditor/wiki

## 👨‍💻 Author

Evil0ctal
- GitHub: https://github.com/Evil0ctal
- Project: https://github.com/Evil0ctal/SimpleTweakEditor

---

Thank you for using SimpleTweakEditor! We hope it makes your iOS development workflow more efficient.