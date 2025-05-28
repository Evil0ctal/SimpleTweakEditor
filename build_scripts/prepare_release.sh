#!/bin/bash
# SimpleTweakEditor Release Preparation Script
# 准备所有平台的发布文件，并按平台分类整理

set -e

# 从Python脚本获取版本号
VERSION=$(python3 "$(dirname "$0")/get_version.py")
PROJECT_ROOT="$(dirname "$(dirname "$(readlink -f "$0" || realpath "$0")")")"
RELEASE_DIR="$PROJECT_ROOT/releases/v$VERSION"

echo "🚀 SimpleTweakEditor v$VERSION Release Builder"
echo "============================================="

# 创建发布目录结构
echo "📁 Creating release directory structure..."
rm -rf "$RELEASE_DIR"
mkdir -p "$RELEASE_DIR/macOS"
mkdir -p "$RELEASE_DIR/Linux"
mkdir -p "$RELEASE_DIR/Source"
mkdir -p "$RELEASE_DIR/Docs"

# 切换到项目根目录
cd "$PROJECT_ROOT"

# 清理旧的构建
echo "🧹 Cleaning old builds..."
rm -rf dist/ build/ __pycache__/
rm -f SimpleTweakEditor.spec
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# 检查依赖
echo "📦 Checking dependencies..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required"
    exit 1
fi

# 安装构建依赖
echo "📥 Installing build dependencies..."
pip3 install -q pyinstaller pillow 2>/dev/null || echo "Dependencies may already be installed"

# 构建不同平台的版本
OS_TYPE=$(uname -s)

if [ "$OS_TYPE" = "Darwin" ]; then
    echo ""
    echo "🍎 Building for macOS..."
    
    # 使用新的standalone app构建脚本
    echo "📱 Creating standalone macOS .app bundle..."
    python3 "$PROJECT_ROOT/build_scripts/build_macos_app_standalone.py"
    
    # 复制.app到发布目录
    if [ -d "$PROJECT_ROOT/dist/SimpleTweakEditor.app" ]; then
        echo "📦 Packaging SimpleTweakEditor.app..."
        cp -r "$PROJECT_ROOT/dist/SimpleTweakEditor.app" "$RELEASE_DIR/macOS/"
        
        # 创建zip文件方便上传到GitHub
        cd "$PROJECT_ROOT/dist"
        zip -r -q "SimpleTweakEditor-macOS.zip" SimpleTweakEditor.app
        mv SimpleTweakEditor-macOS.zip "$RELEASE_DIR/macOS/"
        cd "$PROJECT_ROOT"
        
        echo "✅ Standalone .app created (includes all dependencies)"
    fi
    
    # 清理PyInstaller临时文件
    rm -rf "$PROJECT_ROOT/build"
    rm -f "$PROJECT_ROOT/SimpleTweakEditor.spec"
    
elif [ "$OS_TYPE" = "Linux" ]; then
    echo ""
    echo "🐧 Building for Linux..."
    
    # 1. 创建AppImage目录结构
    echo "📦 Creating AppImage structure..."
    "$PROJECT_ROOT/build_scripts/build_linux_appimage.sh"
    
    # 2. 使用PyInstaller创建单文件版本
    echo "🔨 Building standalone executable..."
    pyinstaller --name SimpleTweakEditor \
                --onefile \
                --windowed \
                --clean \
                --noconfirm \
                --add-data "icons:icons" \
                --add-data "src:src" \
                --hidden-import PyQt6.QtCore \
                --hidden-import PyQt6.QtGui \
                --hidden-import PyQt6.QtWidgets \
                --hidden-import PIL \
                --hidden-import PIL.Image \
                main.py
    
    # 复制Linux可执行文件
    if [ -f "dist/SimpleTweakEditor" ]; then
        cp "dist/SimpleTweakEditor" "$RELEASE_DIR/Linux/"
        chmod +x "$RELEASE_DIR/Linux/SimpleTweakEditor"
        
        # 创建tar.gz包
        cd "$RELEASE_DIR/Linux"
        tar -czf "SimpleTweakEditor-Linux-x86_64.tar.gz" SimpleTweakEditor
        cd "$PROJECT_ROOT"
    fi
    
    # 复制AppImage结构（如果存在）
    if [ -d "dist/SimpleTweakEditor.AppDir" ]; then
        cp -r "dist/SimpleTweakEditor.AppDir" "$RELEASE_DIR/Linux/"
    fi
fi

# 复制文档
echo ""
echo "📋 Copying documentation..."
cp README.md LICENSE RELEASE_NOTES.md "$RELEASE_DIR/Docs/" 2>/dev/null || true
[ -f QUICK_START.md ] && cp QUICK_START.md "$RELEASE_DIR/Docs/"
[ -f PROJECT_STRUCTURE.md ] && cp PROJECT_STRUCTURE.md "$RELEASE_DIR/Docs/"

# 创建源代码包
echo ""
echo "📦 Creating source code archive..."
SOURCE_ARCHIVE="$RELEASE_DIR/Source/SimpleTweakEditor-$VERSION-source.tar.gz"
tar -czf "$SOURCE_ARCHIVE" \
    --exclude="__pycache__" \
    --exclude="*.pyc" \
    --exclude="build" \
    --exclude="dist" \
    --exclude="releases" \
    --exclude=".git" \
    --exclude=".idea" \
    --exclude=".venv" \
    --exclude="venv" \
    --exclude="config.json" \
    --exclude="*.deb" \
    --exclude=".DS_Store" \
    --exclude="SimpleTweakEditor.spec" \
    main.py src icons requirements.txt README.md LICENSE \
    RELEASE_NOTES.md QUICK_START.md PROJECT_STRUCTURE.md \
    build_scripts 2>/dev/null || true

# 创建README说明文件
cat > "$RELEASE_DIR/README.txt" << EOF
SimpleTweakEditor v$VERSION Release Files
========================================

📁 macOS/
   - SimpleTweakEditor.app         : Standalone macOS app (no dependencies required)
   - SimpleTweakEditor-macOS.zip   : Compressed .app for easy download (~31MB)

📁 Linux/
   - (Empty on macOS builds)       : Run this script on Linux to build
   - SimpleTweakEditor             : Linux executable (when built on Linux)
   - SimpleTweakEditor-*.tar.gz    : Compressed Linux executable
   - SimpleTweakEditor.AppDir      : AppImage directory structure

📁 Source/
   - SimpleTweakEditor-*-source.tar.gz : Complete source code

📁 Docs/
   - README.md                     : Project documentation
   - RELEASE_NOTES.md             : Release notes
   - QUICK_START.md               : Quick start guide
   - LICENSE                      : License file

Requirements for running the app:
- macOS 10.13 or later
- dpkg-deb (for .deb operations): brew install dpkg

The standalone .app includes:
- Python runtime
- PyQt6 and all Python dependencies
- Complete application code

Note: First launch may require right-clicking and selecting "Open"
due to macOS security settings.

For detailed instructions, see QUICK_START.md
EOF

# 生成校验和
echo ""
echo "🔐 Generating checksums..."
for platform in macOS Linux Source; do
    if [ -d "$RELEASE_DIR/$platform" ] && [ "$(ls -A "$RELEASE_DIR/$platform" 2>/dev/null)" ]; then
        cd "$RELEASE_DIR/$platform"
        if command -v sha256sum &> /dev/null; then
            sha256sum * > SHA256SUMS 2>/dev/null || true
        elif command -v shasum &> /dev/null; then
            shasum -a 256 * > SHA256SUMS 2>/dev/null || true
        fi
        cd "$PROJECT_ROOT"
    fi
done

# 清理临时文件
echo ""
echo "🧹 Cleaning up..."
rm -rf "$PROJECT_ROOT/build"
rm -rf "$PROJECT_ROOT/dist"
rm -f "$PROJECT_ROOT/SimpleTweakEditor.spec"

# 打印摘要
echo ""
echo "✅ Release preparation completed!"
echo ""
echo "📦 Release structure:"
echo ""

# 显示目录结构
if command -v tree &> /dev/null; then
    tree "$RELEASE_DIR" -L 2
else
    find "$RELEASE_DIR" -type f | sort | head -20
fi

# 计算文件大小
echo ""
echo "📊 File sizes:"
if [ "$OS_TYPE" = "Darwin" ]; then
    find "$RELEASE_DIR" -type f -name "*.zip" -o -name "*.tar.gz" -o -name "SimpleTweakEditor*" | while read f; do
        if [ -f "$f" ]; then
            size=$(ls -lh "$f" | awk '{print $5}')
            echo "  - $(basename "$f"): $size"
        fi
    done
fi

echo ""
echo "📝 GitHub Release Upload Guide:"
echo "1. Create a new release on GitHub"
echo "2. Upload these files:"
if [ "$OS_TYPE" = "Darwin" ]; then
    echo "   - macOS: SimpleTweakEditor-macOS.zip"
elif [ "$OS_TYPE" = "Linux" ]; then
    echo "   - Linux: SimpleTweakEditor-Linux-x86_64.tar.gz"
fi
echo "   - Source: SimpleTweakEditor-$VERSION-source.tar.gz"
echo ""
echo "🎉 Release v$VERSION is ready!"