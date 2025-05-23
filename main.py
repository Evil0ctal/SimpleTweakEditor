#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iOS .deb Tweak Editor - Main Entry Point
A secure tool for iOS .deb package manipulation

Author: Evil0ctal
License: Apache 2.0
"""

import argparse
import os
import platform
import sys

# Check Python version
if sys.version_info < (3, 8):
    sys.exit("Error: Python 3.8 or higher is required")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, QLoggingCategory
from PyQt6.QtGui import QIcon

from src.core.app import TweakEditorApp
from src.utils.file_operations import batch_unpack_deb, batch_repack_folder


def print_usage():
    """打印命令行使用说明"""
    print("iOS .deb Tweak Editor - Command Line Usage")
    print("\nBasic Usage:")
    print("  python main.py [options] [file.deb|folder]")
    print("\nOptions:")
    print("  --help, -h           Show this help message")
    print("  --unpack, -u <deb>   Unpack specified .deb file")
    print("  --repack, -r <dir>   Repack specified folder")
    print("  --output, -o <dir>   Specify output directory (use with unpack/repack)")
    print("  --batch, -b          Batch mode, no GUI")
    print("  --lang <code>        Set language (en/zh)")
    print("\nExamples:")
    print("  python main.py                              # Start GUI mode")
    print("  python main.py file.deb                    # Open .deb file in GUI")
    print("  python main.py --unpack file.deb           # Unpack file.deb")
    print("  python main.py -u file.deb -o ~/output     # Unpack to specified directory")
    print("  python main.py -r ~/tweakfolder            # Repack specified folder")
    print("  python main.py -b -u *.deb                 # Batch unpack all deb files")


def setup_qt_environment():
    """设置Qt环境"""
    # 忽略macOS上的NSOpenPanel警告
    os.environ['QT_MAC_WANTS_LAYER'] = '1'

    if platform.system() == "Darwin":
        # 禁用Qt调试输出
        QLoggingCategory.setFilterRules("*.debug=false")


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--help', '-h', action='store_true', help='Show help message')
    parser.add_argument('--unpack', '-u', metavar='DEB_FILE', help='Unpack specified .deb file')
    parser.add_argument('--repack', '-r', metavar='FOLDER', help='Repack specified folder')
    parser.add_argument('--output', '-o', metavar='DIR', help='Specify output directory')
    parser.add_argument('--batch', '-b', action='store_true', help='Batch mode, no GUI')
    parser.add_argument('--lang', choices=['en', 'zh'], help='Set language (en/zh)')
    parser.add_argument('file_or_folder', nargs='?', help='File or folder to process')

    return parser.parse_known_args()


def handle_batch_mode(args):
    """处理批处理模式"""
    if args.unpack:
        success = batch_unpack_deb(args.unpack, args.output)
        sys.exit(0 if success else 1)
    elif args.repack:
        success = batch_repack_folder(args.repack, args.output)
        sys.exit(0 if success else 1)
    else:
        print("\nError: Batch mode requires --unpack or --repack option")
        sys.exit(1)


def main():
    """主函数"""
    # 解析命令行参数
    args, unknown = parse_arguments()

    # 显示帮助
    if args.help:
        print_usage()
        sys.exit(0)

    # 批处理模式
    if args.batch:
        handle_batch_mode(args)

    # 设置Qt环境
    setup_qt_environment()

    # 创建Qt应用程序
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # 设置应用程序图标
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icons', 'app_icon.png')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # 创建主应用程序
    main_app = TweakEditorApp()

    # 设置语言
    if args.lang:
        main_app.switch_language(args.lang)

    # 处理命令行指定的文件或文件夹
    input_path = args.file_or_folder or args.unpack or args.repack
    if input_path and os.path.exists(input_path):
        # 延迟处理输入文件，确保UI已完全加载
        QTimer.singleShot(500, lambda: main_app.process_input_path(input_path))

    # 显示主窗口
    main_app.show()

    # 启动应用程序事件循环
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
