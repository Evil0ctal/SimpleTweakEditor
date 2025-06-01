# -*- coding: utf-8 -*-
"""
创建时间: 2025-05-24
作者: Evil0ctal

中文介绍:
文件操作工具模块，提供 SimpleTweakEditor 的核心功能。
包含 .deb 文件的解包和打包功能，支持跨平台操作，自动选择最佳处理器。
提供批量处理、control 文件验证、目录结构生成等实用功能。

英文介绍:
File operations utility module providing core functionality for SimpleTweakEditor.
Includes unpacking and packing functions for .deb files with cross-platform support
and automatic selection of the best handler.
Provides batch processing, control file validation, directory structure generation
and other practical features.
"""

import os
import shutil
import subprocess
from datetime import datetime
import platform

from .system_utils import set_debian_permissions, get_package_info_from_control, suggest_output_filename
from .dpkg_deb import dpkg_deb
from .security import validate_path, secure_path_join, sanitize_filename, validate_file_size, PathTraversalError


def find_dpkg_deb():
    """
    查找dpkg-deb命令的路径
    
    Returns:
        str: dpkg-deb的完整路径，如果找不到则返回None
    """
    # 可能的dpkg-deb路径
    possible_paths = [
        "dpkg-deb",  # 系统PATH中
        "/usr/bin/dpkg-deb",
        "/usr/local/bin/dpkg-deb",
        "/opt/homebrew/bin/dpkg-deb",  # Homebrew on Apple Silicon
        "/usr/local/opt/dpkg/bin/dpkg-deb",  # Homebrew on Intel
    ]
    
    # 在Windows上可能的路径
    if platform.system() == "Windows":
        possible_paths.extend([
            r"C:\Program Files\dpkg\bin\dpkg-deb.exe",
            r"C:\dpkg\bin\dpkg-deb.exe",
        ])
    
    # 检查每个可能的路径
    for path in possible_paths:
        try:
            # 尝试运行dpkg-deb --version
            result = subprocess.run([path, "--version"], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=5)
            if result.returncode == 0:
                return path
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            continue
    
    # 最后尝试使用which/where命令
    try:
        if platform.system() == "Windows":
            result = subprocess.run(["where", "dpkg-deb"], 
                                  capture_output=True, 
                                  text=True)
        else:
            result = subprocess.run(["which", "dpkg-deb"], 
                                  capture_output=True, 
                                  text=True)
        
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split('\n')[0]
    except:
        pass
    
    return None


def find_wsl_dpkg_deb():
    """
    在Windows上通过WSL查找dpkg-deb
    
    Returns:
        tuple: (wsl_path, dpkg_deb_path) 如果找到，否则 (None, None)
    """
    if platform.system() != "Windows":
        return None, None
    
    try:
        # 检查WSL是否可用
        result = subprocess.run(["wsl", "--status"], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        if result.returncode != 0:
            return None, None
        
        # 尝试在WSL中查找dpkg-deb
        result = subprocess.run(["wsl", "which", "dpkg-deb"], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        
        if result.returncode == 0 and result.stdout.strip():
            return "wsl", result.stdout.strip()
    except:
        pass
    
    return None, None


def get_deb_handler_priority():
    """
    根据平台返回处理器优先级列表
    
    Returns:
        list: 处理器类型列表，按优先级排序
    """
    system = platform.system()
    
    if system == "Darwin":  # macOS
        # macOS: 优先使用原生dpkg-deb，然后Python实现
        return ["dpkg-native", "python"]
    elif system == "Linux":
        # Linux: 优先使用原生dpkg-deb，然后Python实现
        return ["dpkg-native", "python"]
    elif system == "Windows":
        # Windows: 优先使用Python实现，然后WSL，最后原生dpkg
        return ["python", "dpkg-wsl", "dpkg-native"]
    else:
        # 其他平台: 尝试所有方法
        return ["python", "dpkg-native"]


def unpack_deb_file(deb_path, output_dir):
    """
    解包.deb文件

    Args:
        deb_path: .deb文件路径
        output_dir: 输出目录

    Returns:
        tuple: (成功标志, 消息, 目标目录)
    """
    try:
        # 安全路径验证 - 防止路径遍历攻击
        try:
            deb_path = validate_path(os.path.expanduser(deb_path))
            output_dir = validate_path(os.path.expanduser(output_dir))
        except PathTraversalError as e:
            return False, f"不安全的路径: {str(e)}", None
        
        # 验证文件
        if not os.path.exists(deb_path):
            return False, f"文件不存在: {deb_path}", None
        if not deb_path.endswith('.deb'):
            return False, "不是有效的.deb文件", None
        
        # 验证文件大小
        try:
            validate_file_size(deb_path, max_size=500 * 1024 * 1024)
        except ValueError as e:
            return False, str(e), None
        
        # 准备目标目录（以.deb文件命名的文件夹）
        deb_name = sanitize_filename(os.path.splitext(os.path.basename(deb_path))[0])
        target_dir = secure_path_join(output_dir, deb_name)

        # 如果目标目录已存在，删除它
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)

        # 创建目标目录
        os.makedirs(target_dir, exist_ok=True)

        # 获取处理器优先级
        handlers = get_deb_handler_priority()
        last_error = None
        
        for handler in handlers:
            if handler == "python":
                # 尝试使用纯Python处理器
                try:
                    success = dpkg_deb.unpack(deb_path, target_dir)
                    if success:
                        # 设置DEBIAN目录权限
                        debian_dir = os.path.join(target_dir, "DEBIAN")
                        permissions_set, permission_errors = set_debian_permissions(debian_dir)
                        
                        output_msg = "Successfully unpacked using native Python handler\n"
                        # 添加权限设置信息
                        for perm_msg in permissions_set:
                            output_msg += perm_msg + "\n"
                        if permission_errors:
                            for error in permission_errors:
                                output_msg += f"Warning: {error}\n"
                        
                        return True, output_msg, target_dir
                except Exception as e:
                    last_error = f"Python handler failed: {str(e)}"
                    continue
                    
            elif handler == "dpkg-native":
                # 尝试使用原生dpkg-deb
                dpkg_deb_path = find_dpkg_deb()
                if dpkg_deb_path:
                    try:
                        # 提取文件系统内容
                        result1 = subprocess.run(
                            [dpkg_deb_path, "-x", deb_path, target_dir],
                            capture_output=True, text=True
                        )

                        # 提取control文件到DEBIAN/
                        debian_dir = os.path.join(target_dir, "DEBIAN")
                        os.makedirs(debian_dir, exist_ok=True)
                        result2 = subprocess.run(
                            [dpkg_deb_path, "-e", deb_path, debian_dir],
                            capture_output=True, text=True
                        )

                        # 检查解包结果
                        if result1.returncode == 0 and result2.returncode == 0:
                            # 设置DEBIAN目录权限
                            permissions_set, permission_errors = set_debian_permissions(debian_dir)

                            # 收集输出消息
                            output_msg = f"Successfully unpacked using native dpkg-deb ({dpkg_deb_path})\n"
                            if result1.stdout:
                                output_msg += result1.stdout.strip() + "\n"
                            if result2.stdout:
                                output_msg += result2.stdout.strip() + "\n"

                            # 添加权限设置信息
                            for perm_msg in permissions_set:
                                output_msg += perm_msg + "\n"

                            if permission_errors:
                                for error in permission_errors:
                                    output_msg += f"Warning: {error}\n"

                            return True, output_msg, target_dir
                        else:
                            error_msg = ""
                            if result1.stderr:
                                error_msg += result1.stderr.strip() + "\n"
                            if result2.stderr:
                                error_msg += result2.stderr.strip() + "\n"
                            last_error = f"dpkg-deb failed: {error_msg}"
                    except Exception as e:
                        last_error = f"dpkg-deb error: {str(e)}"
                else:
                    last_error = "dpkg-deb not found"
                    
            elif handler == "dpkg-wsl":
                # 尝试使用WSL中的dpkg-deb
                wsl_path, dpkg_path = find_wsl_dpkg_deb()
                if wsl_path and dpkg_path:
                    try:
                        # 转换Windows路径为WSL路径
                        wsl_deb_path = subprocess.run(
                            ["wsl", "wslpath", "-u", deb_path],
                            capture_output=True, text=True
                        ).stdout.strip()
                        
                        wsl_target_dir = subprocess.run(
                            ["wsl", "wslpath", "-u", target_dir],
                            capture_output=True, text=True
                        ).stdout.strip()
                        
                        # 提取文件系统内容
                        result1 = subprocess.run(
                            ["wsl", dpkg_path, "-x", wsl_deb_path, wsl_target_dir],
                            capture_output=True, text=True
                        )

                        # 提取control文件到DEBIAN/
                        debian_dir = os.path.join(target_dir, "DEBIAN")
                        os.makedirs(debian_dir, exist_ok=True)
                        wsl_debian_dir = subprocess.run(
                            ["wsl", "wslpath", "-u", debian_dir],
                            capture_output=True, text=True
                        ).stdout.strip()
                        
                        result2 = subprocess.run(
                            ["wsl", dpkg_path, "-e", wsl_deb_path, wsl_debian_dir],
                            capture_output=True, text=True
                        )

                        if result1.returncode == 0 and result2.returncode == 0:
                            # 设置DEBIAN目录权限
                            permissions_set, permission_errors = set_debian_permissions(debian_dir)

                            output_msg = "Successfully unpacked using WSL dpkg-deb\n"
                            return True, output_msg, target_dir
                        else:
                            error_msg = ""
                            if result1.stderr:
                                error_msg += result1.stderr.strip() + "\n"
                            if result2.stderr:
                                error_msg += result2.stderr.strip() + "\n"
                            last_error = f"WSL dpkg-deb failed: {error_msg}"
                    except Exception as e:
                        last_error = f"WSL error: {str(e)}"
                else:
                    last_error = "WSL or dpkg-deb not available in WSL"
        
        # 如果所有方法都失败了
        error_msg = "Failed to unpack .deb file. Tried methods:\n"
        error_msg += f"- {last_error or 'All handlers failed'}\n"
        error_msg += "\nSuggestions:\n"
        if platform.system() == "Windows":
            error_msg += "- Install Windows Subsystem for Linux (WSL) with dpkg\n"
            error_msg += "- Or wait for future updates with improved Windows support"
        else:
            error_msg += "- Install dpkg: brew install dpkg (macOS) or apt-get install dpkg (Linux)"
        
        return False, error_msg, None

    except Exception as e:
        return False, f"Exception during unpacking: {str(e)}", None


def pack_folder_to_deb(folder_path, output_path):
    """
    将文件夹打包为.deb文件

    Args:
        folder_path: 要打包的文件夹路径
        output_path: 输出.deb文件路径

    Returns:
        tuple: (成功标志, 消息)
    """
    # 初始化变量
    temp_structure_file = None
    structure_file = os.path.join(folder_path, "DIRECTORY_STRUCTURE.md")
    
    try:
        # 检查文件夹结构
        debian_dir = os.path.join(folder_path, "DEBIAN")
        control_file = os.path.join(debian_dir, "control")

        if not os.path.isdir(debian_dir):
            return False, f"Missing DEBIAN directory in {folder_path}"

        if not os.path.isfile(control_file):
            return False, f"Missing control file in {debian_dir}"

        # 临时移动DIRECTORY_STRUCTURE.md文件（如果存在）
        if os.path.exists(structure_file):
            temp_structure_file = structure_file + ".tmp"
            shutil.move(structure_file, temp_structure_file)

        # 获取处理器优先级
        handlers = get_deb_handler_priority()
        last_error = None
        
        # 预先设置权限
        permissions_set, permission_errors = set_debian_permissions(debian_dir)
        
        for handler in handlers:
            if handler == "python":
                # 尝试使用纯Python处理器
                try:
                    success = dpkg_deb.pack(folder_path, output_path)
                    if success:
                        output_msg = "Successfully packed using native Python handler\n"
                        # 添加权限设置信息
                        for perm_msg in permissions_set:
                            output_msg += perm_msg + "\n"
                        if permission_errors:
                            for error in permission_errors:
                                output_msg += f"Warning: {error}\n"
                        
                        # 恢复DIRECTORY_STRUCTURE.md文件
                        if temp_structure_file and os.path.exists(temp_structure_file):
                            shutil.move(temp_structure_file, structure_file)
                            
                        return True, output_msg
                except Exception as e:
                    last_error = f"Python handler failed: {str(e)}"
                    continue
                    
            elif handler == "dpkg-native":
                # 尝试使用原生dpkg-deb
                dpkg_deb_path = find_dpkg_deb()
                if dpkg_deb_path:
                    try:
                        # 构建dpkg-deb命令
                        build_cmd = [dpkg_deb_path, "--root-owner-group", "-b", folder_path, output_path]

                        # 执行打包命令
                        result = subprocess.run(build_cmd, capture_output=True, text=True)

                        if result.returncode == 0:
                            # 收集输出消息
                            output_msg = f"Successfully packed using native dpkg-deb ({dpkg_deb_path})\n"
                            if result.stdout:
                                output_msg += result.stdout.strip() + "\n"
                            if result.stderr:
                                output_msg += result.stderr.strip() + "\n"

                            # 添加权限设置信息
                            for perm_msg in permissions_set:
                                output_msg += perm_msg + "\n"

                            if permission_errors:
                                for error in permission_errors:
                                    output_msg += f"Warning: {error}\n"

                            # 恢复DIRECTORY_STRUCTURE.md文件
                            if temp_structure_file and os.path.exists(temp_structure_file):
                                shutil.move(temp_structure_file, structure_file)

                            return True, output_msg
                        else:
                            error_msg = ""
                            if result.stdout:
                                error_msg += result.stdout.strip() + "\n"
                            if result.stderr:
                                error_msg += result.stderr.strip() + "\n"
                            last_error = f"dpkg-deb failed: {error_msg}"
                    except Exception as e:
                        last_error = f"dpkg-deb error: {str(e)}"
                else:
                    last_error = "dpkg-deb not found"
                    
            elif handler == "dpkg-wsl":
                # 尝试使用WSL中的dpkg-deb
                wsl_path, dpkg_path = find_wsl_dpkg_deb()
                if wsl_path and dpkg_path:
                    try:
                        # 转换Windows路径为WSL路径
                        wsl_folder_path = subprocess.run(
                            ["wsl", "wslpath", "-u", folder_path],
                            capture_output=True, text=True
                        ).stdout.strip()
                        
                        wsl_output_path = subprocess.run(
                            ["wsl", "wslpath", "-u", output_path],
                            capture_output=True, text=True
                        ).stdout.strip()
                        
                        # 构建dpkg-deb命令
                        result = subprocess.run(
                            ["wsl", dpkg_path, "--root-owner-group", "-b", wsl_folder_path, wsl_output_path],
                            capture_output=True, text=True
                        )

                        if result.returncode == 0:
                            output_msg = "Successfully packed using WSL dpkg-deb\n"
                            
                            # 恢复DIRECTORY_STRUCTURE.md文件
                            if temp_structure_file and os.path.exists(temp_structure_file):
                                shutil.move(temp_structure_file, structure_file)
                                
                            return True, output_msg
                        else:
                            error_msg = ""
                            if result.stdout:
                                error_msg += result.stdout.strip() + "\n"
                            if result.stderr:
                                error_msg += result.stderr.strip() + "\n"
                            last_error = f"WSL dpkg-deb failed: {error_msg}"
                    except Exception as e:
                        last_error = f"WSL error: {str(e)}"
                else:
                    last_error = "WSL or dpkg-deb not available in WSL"
        
        # 恢复文件（如果所有方法都失败）
        if temp_structure_file and os.path.exists(temp_structure_file):
            shutil.move(temp_structure_file, structure_file)
            
        # 如果所有方法都失败了
        error_msg = "Failed to pack .deb file. Tried methods:\n"
        error_msg += f"- {last_error or 'All handlers failed'}\n"
        error_msg += "\nSuggestions:\n"
        if platform.system() == "Windows":
            error_msg += "- Install Windows Subsystem for Linux (WSL) with dpkg\n"
            error_msg += "- Or wait for future updates with improved Windows support"
        else:
            error_msg += "- Install dpkg: brew install dpkg (macOS) or apt-get install dpkg (Linux)"
        
        return False, error_msg

    except Exception as e:
        # 恢复文件（如果打包失败）
        if temp_structure_file and os.path.exists(temp_structure_file):
            shutil.move(temp_structure_file, structure_file)
        return False, f"Exception during packaging: {str(e)}"


def batch_unpack_deb(deb_path, output_dir=None):
    """
    命令行模式下解包deb文件

    Args:
        deb_path: .deb文件路径
        output_dir: 输出目录（可选）

    Returns:
        bool: 成功标志
    """
    if not os.path.exists(deb_path):
        print(f"\nError: File '{deb_path}' does not exist")
        return False

    if not deb_path.lower().endswith('.deb'):
        print(f"\nError: '{deb_path}' is not a .deb file")
        return False

    # 准备输出目录
    if output_dir is None:
        # 默认在当前目录下创建以deb文件名的文件夹
        output_dir = os.path.dirname(os.path.abspath(deb_path))

    print(f"\nUnpacking '{deb_path}' to '{output_dir}'...")

    success, message, target_dir = unpack_deb_file(deb_path, output_dir)

    if success:
        print(f"\nSuccessfully unpacked to: {target_dir}")
        if message:
            print("Details:")
            print(message)
        return True
    else:
        print(f"\nUnpack failed:")
        if message:
            print(message)
        return False


def batch_repack_folder(folder_path, output_path=None):
    """
    命令行模式下打包文件夹

    Args:
        folder_path: 文件夹路径
        output_path: 输出文件路径（可选）

    Returns:
        bool: 成功标志
    """
    if not os.path.isdir(folder_path):
        print(f"\nError: '{folder_path}' is not a valid directory")
        return False

    # 检查目录结构
    debian_dir = os.path.join(folder_path, "DEBIAN")
    control_file = os.path.join(debian_dir, "control")

    if not os.path.isdir(debian_dir):
        print(f"\nError: '{folder_path}' does not contain DEBIAN directory")
        return False

    if not os.path.isfile(control_file):
        print(f"\nError: '{debian_dir}' does not contain control file")
        return False

    # 准备输出路径
    if output_path is None:
        # 从控制文件中提取信息生成文件名
        package_info = get_package_info_from_control(control_file)
        output_name = suggest_output_filename(package_info)
        output_path = os.path.join(os.path.dirname(folder_path), output_name)

    print(f"\nPacking '{folder_path}' to '{output_path}'...")

    success, message = pack_folder_to_deb(folder_path, output_path)

    if success:
        print(f"\nSuccessfully packed to: {output_path}")
        if message:
            print("Details:")
            print(message)
        return True
    else:
        print(f"\nPack failed:")
        if message:
            print(message)
        return False


def validate_control_file(control_content):
    """
    验证control文件格式

    Args:
        control_content: control文件内容

    Returns:
        tuple: (是否有效, 错误消息列表)
    """
    errors = []

    # 检查必填字段
    required_fields = ["Package", "Version", "Architecture", "Description"]
    missing_fields = []

    for field in required_fields:
        if not any(line.startswith(f"{field}:") for line in control_content.splitlines()):
            missing_fields.append(field)

    if missing_fields:
        errors.append(f"Missing required fields: {', '.join(missing_fields)}")

    # 检查字段格式
    for line_num, line in enumerate(control_content.splitlines(), 1):
        if line and not line.startswith(" ") and ":" not in line:
            errors.append(f"Line {line_num}: Invalid field format: '{line}'")

    return len(errors) == 0, errors


def read_control_file(control_path):
    """
    读取control文件内容

    Args:
        control_path: control文件路径

    Returns:
        tuple: (成功标志, 内容或错误消息)
    """
    try:
        with open(control_path, "r", encoding='utf-8') as f:
            return True, f.read()
    except Exception as e:
        return False, str(e)


def write_control_file(control_path, content):
    """
    写入control文件内容

    Args:
        control_path: control文件路径
        content: 文件内容

    Returns:
        tuple: (成功标志, 错误消息)
    """
    try:
        # 确保内容以换行符结束
        if not content.endswith("\n"):
            content += "\n"

        with open(control_path, "w", encoding='utf-8') as f:
            f.write(content)
        return True, None
    except Exception as e:
        return False, str(e)


def generate_directory_structure(directory_path, output_file=None):
    """
    生成目录结构的Markdown文件
    
    Args:
        directory_path: 要分析的目录路径
        output_file: 输出文件路径，如果为None则自动生成
    
    Returns:
        tuple: (成功标志, 输出文件路径或错误消息)
    """
    try:
        directory_path = os.path.abspath(directory_path)
        if not os.path.exists(directory_path):
            return False, f"Directory does not exist: {directory_path}"
        
        if output_file is None:
            output_file = os.path.join(directory_path, "DIRECTORY_STRUCTURE.md")
        
        # 生成目录结构
        structure_lines = []
        dir_name = os.path.basename(directory_path)
        
        # 添加标题和基本信息
        structure_lines.append(f"# Directory Structure: {dir_name}")
        structure_lines.append("")
        structure_lines.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        structure_lines.append(f"Total path: `{directory_path}`")
        structure_lines.append("")
        
        # 生成树状结构
        structure_lines.append("## File Tree")
        structure_lines.append("")
        structure_lines.append("```")
        structure_lines.append(f"{dir_name}/")
        
        def scan_directory(path, prefix=""):
            """递归扫描目录"""
            try:
                entries = sorted(os.listdir(path))
                dir_files = []
                dir_subdirs = []
                
                for entry in entries:
                    entry_path = os.path.join(path, entry)
                    if os.path.isdir(entry_path):
                        dir_subdirs.append(entry)
                    else:
                        dir_files.append(entry)
                
                # 先处理目录
                for i, dirname in enumerate(dir_subdirs):
                    is_last_dir = (i == len(dir_subdirs) - 1) and len(dir_files) == 0
                    connector = "└── " if is_last_dir else "├── "
                    structure_lines.append(f"{prefix}{connector}{dirname}/")
                    
                    # 递归处理子目录
                    new_prefix = prefix + ("    " if is_last_dir else "│   ")
                    scan_directory(os.path.join(path, dirname), new_prefix)
                
                # 再处理文件
                for i, filename in enumerate(dir_files):
                    is_last_file = (i == len(dir_files) - 1)
                    connector = "└── " if is_last_file else "├── "
                    
                    # 获取文件大小
                    current_file_path = os.path.join(path, filename)
                    try:
                        size = os.path.getsize(current_file_path)
                        if size < 1024:
                            size_str = f"{size}B"
                        elif size < 1024*1024:
                            size_str = f"{size/1024:.1f}KB"
                        else:
                            size_str = f"{size/(1024*1024):.1f}MB"
                        structure_lines.append(f"{prefix}{connector}{filename} ({size_str})")
                    except Exception:
                        structure_lines.append(f"{prefix}{connector}{filename}")
                        
            except PermissionError:
                structure_lines.append(f"{prefix}├── [Permission Denied]")
            except Exception as scan_error:
                structure_lines.append(f"{prefix}├── [Error: {str(scan_error)}]")
        
        scan_directory(directory_path)
        structure_lines.append("```")
        structure_lines.append("")
        
        # 添加统计信息
        structure_lines.append("## Statistics")
        structure_lines.append("")
        
        total_files = 0
        total_dirs = 0
        total_size = 0
        
        for root, dirs, files in os.walk(directory_path):
            total_dirs += len(dirs)
            total_files += len(files)
            for file in files:
                try:
                    current_file = os.path.join(root, file)
                    total_size += os.path.getsize(current_file)
                except Exception:
                    pass
        
        size_mb = total_size / (1024 * 1024)
        structure_lines.append(f"- **Total Directories**: {total_dirs}")
        structure_lines.append(f"- **Total Files**: {total_files}")
        structure_lines.append(f"- **Total Size**: {size_mb:.2f} MB")
        structure_lines.append("")
        
        # 如果是.deb解包目录，添加包信息
        control_file = os.path.join(directory_path, "DEBIAN", "control")
        if os.path.exists(control_file):
            structure_lines.append("## Package Information")
            structure_lines.append("")
            try:
                with open(control_file, 'r', encoding='utf-8') as f:
                    control_content = f.read()
                structure_lines.append("```")
                structure_lines.append(control_content.strip())
                structure_lines.append("```")
                structure_lines.append("")
            except Exception:
                structure_lines.append("*Could not read control file*")
                structure_lines.append("")
        
        # 重要文件列表
        important_files = []
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                if file in ['control', 'postinst', 'prerm', 'postrm', 'preinst', 'conffiles']:
                    rel_path = os.path.relpath(os.path.join(root, file), directory_path)
                    important_files.append(rel_path)
        
        if important_files:
            structure_lines.append("## Important Files")
            structure_lines.append("")
            for file in sorted(important_files):
                structure_lines.append(f"- `{file}`")
            structure_lines.append("")
        
        # 写入文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(structure_lines))
        
        return True, output_file
        
    except Exception as e:
        return False, f"Error generating directory structure: {str(e)}"
