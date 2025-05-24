#!/bin/bash
# Complete cleanup script for SimpleTweakEditor project

echo "🧹 Deep cleaning SimpleTweakEditor project..."

# 获取项目根目录
PROJECT_ROOT="$(dirname "$(dirname "$(readlink -f "$0")")")"
cd "$PROJECT_ROOT"

# 清理Python缓存
echo "🗑️  Removing Python cache..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
find . -type f -name "*.pyd" -delete 2>/dev/null || true

# 清理构建文件
echo "🗑️  Removing build artifacts..."
rm -rf build/
rm -rf dist/
rm -f *.spec
rm -rf *.egg-info/

# 清理系统文件
echo "🗑️  Removing system files..."
find . -name ".DS_Store" -delete 2>/dev/null || true
find . -name "Thumbs.db" -delete 2>/dev/null || true
find . -name "._*" -delete 2>/dev/null || true

# 清理临时文件
echo "🗑️  Removing temporary files..."
find . -name "*.tmp" -delete 2>/dev/null || true
find . -name "*.temp" -delete 2>/dev/null || true
find . -name "*.bak" -delete 2>/dev/null || true
find . -name "*~" -delete 2>/dev/null || true
find . -name ".*.swp" -delete 2>/dev/null || true
find . -name ".*.swo" -delete 2>/dev/null || true

# 清理日志文件
echo "🗑️  Removing log files..."
find . -name "*.log" -delete 2>/dev/null || true
rm -rf logs/

# 清理测试覆盖率文件
echo "🗑️  Removing test coverage files..."
rm -rf .coverage
rm -rf htmlcov/
rm -rf .pytest_cache/
rm -rf .tox/
rm -rf .nox/

# 清理项目特定的文件
echo "🗑️  Removing project-specific files..."
rm -f config.json
rm -rf unpacked/
rm -rf output/
rm -rf extracted_*/
rm -rf repacked_*/

# 清理旧的发布文件（可选）
read -p "❓ Remove release files? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🗑️  Removing release files..."
    rm -rf releases/
fi

echo ""
echo "✅ Cleanup completed!"
echo ""
echo "📁 Clean project structure:"
ls -la | grep -E "^d|^-.*\.(py|md|txt|sh)$"