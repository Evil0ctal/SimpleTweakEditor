#!/bin/bash
# SimpleTweakEditor Linux AppImage Builder
# Creates a portable AppImage for Linux

set -e

APP_NAME="SimpleTweakEditor"
# 从Python脚本获取版本号
VERSION=$(python3 "$(dirname "$0")/get_version.py")
ARCH="x86_64"

echo "🐧 Building $APP_NAME AppImage for Linux..."
echo "==========================================="

# 检查系统
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo "⚠️  This script is intended for Linux systems"
    echo "   Current OS: $OSTYPE"
fi

# 创建AppDir结构
APPDIR="dist/$APP_NAME.AppDir"
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"
mkdir -p "$APPDIR/usr/lib/python3/dist-packages"
mkdir -p "$APPDIR/usr/share/applications"
mkdir -p "$APPDIR/usr/share/icons/hicolor/256x256/apps"
mkdir -p "$APPDIR/usr/share/metainfo"

# 创建启动脚本
cat > "$APPDIR/usr/bin/$APP_NAME" << 'EOF'
#!/bin/bash
# SimpleTweakEditor Launcher

# 获取AppImage路径
if [ -z "$APPDIR" ]; then
    APPDIR="$(dirname "$(dirname "$(readlink -f "$0")")")"
fi

# 设置环境
export PYTHONPATH="$APPDIR/usr/lib/python3/dist-packages:$PYTHONPATH"
export PATH="$APPDIR/usr/bin:$PATH"

# 检查Python3
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required to run SimpleTweakEditor"
    echo "Please install Python 3.8 or later"
    exit 1
fi

# 检查dpkg-deb
if ! command -v dpkg-deb &> /dev/null; then
    echo "Warning: dpkg-deb is not installed"
    echo "Install it using: sudo apt-get install dpkg"
fi

# 运行主程序
cd "$APPDIR/usr/lib/python3/dist-packages"
exec python3 main.py "$@"
EOF

chmod +x "$APPDIR/usr/bin/$APP_NAME"

# 复制项目文件
echo "📁 Copying project files..."
cp -r main.py "$APPDIR/usr/lib/python3/dist-packages/"
cp -r src "$APPDIR/usr/lib/python3/dist-packages/"
cp -r icons "$APPDIR/usr/lib/python3/dist-packages/"
cp requirements.txt "$APPDIR/usr/lib/python3/dist-packages/"

# 创建AppRun
cat > "$APPDIR/AppRun" << 'EOF'
#!/bin/bash
HERE="$(dirname "$(readlink -f "${0}")")"
exec "$HERE/usr/bin/SimpleTweakEditor" "$@"
EOF
chmod +x "$APPDIR/AppRun"

# 创建.desktop文件
cat > "$APPDIR/$APP_NAME.desktop" << EOF
[Desktop Entry]
Name=SimpleTweakEditor
GenericName=iOS .deb Editor
Comment=Professional iOS .deb Package Editor
Exec=$APP_NAME %f
Icon=$APP_NAME
Terminal=false
Type=Application
Categories=Development;Utility;
MimeType=application/x-deb;application/x-debian-package;
Keywords=iOS;deb;tweak;editor;package;
StartupNotify=true
EOF

# 复制到applications目录
cp "$APPDIR/$APP_NAME.desktop" "$APPDIR/usr/share/applications/"

# 复制图标
if [ -f "icons/icon_256x256.png" ]; then
    cp "icons/icon_256x256.png" "$APPDIR/usr/share/icons/hicolor/256x256/apps/$APP_NAME.png"
    cp "icons/icon_256x256.png" "$APPDIR/$APP_NAME.png"
elif [ -f "icons/app_icon.png" ]; then
    cp "icons/app_icon.png" "$APPDIR/usr/share/icons/hicolor/256x256/apps/$APP_NAME.png"
    cp "icons/app_icon.png" "$APPDIR/$APP_NAME.png"
fi

# 创建AppStream元数据
cat > "$APPDIR/usr/share/metainfo/$APP_NAME.appdata.xml" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<component type="desktop-application">
  <id>com.evil0ctal.$APP_NAME</id>
  <metadata_license>CC0-1.0</metadata_license>
  <project_license>Apache-2.0</project_license>
  <name>SimpleTweakEditor</name>
  <summary>Professional iOS .deb Package Editor</summary>
  <description>
    <p>SimpleTweakEditor is a secure tool for iOS .deb package manipulation with the following features:</p>
    <ul>
      <li>Unpack .deb files</li>
      <li>Edit control files</li>
      <li>Repack to .deb format</li>
      <li>Drag and drop support</li>
      <li>Multi-language interface</li>
    </ul>
  </description>
  <launchable type="desktop-id">$APP_NAME.desktop</launchable>
  <url type="homepage">https://github.com/Evil0ctal/SimpleTweakEditor</url>
  <provides>
    <binary>$APP_NAME</binary>
  </provides>
  <releases>
    <release version="$VERSION" date="$(date +%Y-%m-%d)"/>
  </releases>
</component>
EOF

# 创建依赖安装脚本
cat > "$APPDIR/install_dependencies.sh" << 'EOF'
#!/bin/bash
echo "Installing dependencies for SimpleTweakEditor..."

# 安装系统依赖
echo "Installing system packages..."
sudo apt-get update
sudo apt-get install -y python3 python3-pip dpkg

# 安装Python依赖
echo "Installing Python packages..."
pip3 install PyQt6 Pillow

echo "Dependencies installed successfully!"
EOF
chmod +x "$APPDIR/install_dependencies.sh"

# 创建README
cat > "$APPDIR/README.md" << EOF
# SimpleTweakEditor v$VERSION

## Running the AppImage
1. Make it executable: chmod +x SimpleTweakEditor-$VERSION-$ARCH.AppImage
2. Run: ./SimpleTweakEditor-$VERSION-$ARCH.AppImage

## Dependencies
- Python 3.8+
- PyQt6 (will prompt to install if missing)
- dpkg-deb (required for .deb operations)

## Installing Dependencies
Run the included script:
./SimpleTweakEditor-$VERSION-$ARCH.AppImage --appimage-extract
./squashfs-root/install_dependencies.sh

Or manually:
sudo apt-get install python3 python3-pip dpkg
pip3 install PyQt6 Pillow

## Usage
- Double-click to launch
- Drag and drop .deb files
- Use File menu for operations

## Author
Evil0ctal
https://github.com/Evil0ctal/SimpleTweakEditor
EOF

echo "✅ AppDir structure created successfully!"
echo ""
echo "📦 To create AppImage, you need appimagetool:"
echo "   1. Download: https://github.com/AppImage/AppImageKit/releases"
echo "   2. Make executable: chmod +x appimagetool-*.AppImage"
echo "   3. Run: ./appimagetool-*.AppImage $APPDIR SimpleTweakEditor-$VERSION-$ARCH.AppImage"
echo ""
echo "Or use the following commands:"
echo "   wget https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
echo "   chmod +x appimagetool-x86_64.AppImage"
echo "   ./appimagetool-x86_64.AppImage $APPDIR SimpleTweakEditor-$VERSION-$ARCH.AppImage"