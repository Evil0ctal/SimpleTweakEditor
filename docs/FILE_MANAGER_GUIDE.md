# File Manager Guide

## Overview

The iOS File Manager is a visual file browsing tool integrated into SimpleTweakEditor that supports three device scenarios:
- **Non-jailbroken devices**: Limited access to media files and app sandboxes
- **Rootless jailbreak**: Access to `/var/jb/` and allowed directories
- **Rootful jailbreak**: Full filesystem access

## Accessing File Manager

1. Connect an iOS device
2. Go to the "iOS Device" tab
3. Click the "File Manager" button

## Features

### Core Features
- **Browse**: Navigate through device filesystem
- **Upload/Download**: Transfer files between device and PC
- **Drag & Drop**: Drag files from PC to upload
- **Preview**: View text and configuration files
- **Context Menu**: Right-click for file operations

### File Operations
- **Download**: Right-click → Download
- **Upload**: Click Upload button or drag files
- **Delete**: Right-click → Delete
- **Rename**: Right-click → Rename
- **New Folder**: Click "New Folder" button
- **Properties**: Right-click → Properties

### Access Levels

#### Non-Jailbroken (Orange indicator)
- Access: `/DCIM/`, `/Downloads/`, `/Documents/`
- Limited to media files and app data
- Cannot access system files

#### Rootless Jailbreak (Blue indicator)
- Access: `/var/jb/`, `/var/mobile/`, `/var/containers/`
- Can access jailbreak files and user data
- System partition remains read-only

#### Rootful Jailbreak (Green indicator)
- Full filesystem access
- Can read/write system files
- Use caution with system directories (shown in red)

## Safety Features

- **Path Protection**: Dangerous system paths are marked in red
- **Confirmation Dialogs**: Delete operations require confirmation
- **Access Control**: Operations restricted based on jailbreak type
- **Error Handling**: Clear error messages for failed operations

## Tips

1. **Quick Navigation**: 
   - Use "↑" button for parent directory
   - Use "🏠" button for home directory
   - Type path directly in the path bar

2. **File Installation**:
   - Double-click `.deb` files to prompt for installation
   - Upload `.deb` files to `/var/mobile/Downloads/` for manual installation

3. **Performance**:
   - Large directories may take time to load
   - File preview limited to 1MB for performance

## Troubleshooting

### "AFC client not available"
- Install iTunes or Apple Devices for drivers
- Ensure device is unlocked and trusted
- Try disconnecting and reconnecting the device

### Limited functionality warning
- Install `pymobiledevice3` for full features:
  ```bash
  pip install pymobiledevice3
  ```

### Cannot access certain directories
- Check your device's jailbreak status
- Non-jailbroken devices have very limited access
- Some directories require specific jailbreak types